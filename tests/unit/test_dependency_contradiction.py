from datetime import datetime, timezone

from oslt_research.domain.enums import (
    AccessClass,
    ContradictionClass,
    EpistemicStatus,
    EvidenceLane,
    FindingDirection,
    SourceStatus,
)
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord, ScopeContext
from oslt_research.evidence.contradiction import assess_pair, find_substantive_contradictions
from oslt_research.evidence.dependency import EvidenceDependencyGraph
from oslt_research.evidence.provenance import sha256_text


def evidence(evidence_id: str, family: str, bias: str | None = None):
    content = evidence_id
    return EvidenceObject(
        evidence_id=evidence_id,
        lane=EvidenceLane.SUPPORT,
        source_status=SourceStatus.VERIFIED,
        epistemic_status=EpistemicStatus.OBSERVATION,
        title=evidence_id,
        content=content,
        provenance=ProvenanceRecord(
            source_id="DS",
            source_uri=f"https://example.test/{evidence_id}",
            retrieved_at=datetime.now(timezone.utc),
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        dependency_family=family,
        metadata={"content_sha256": sha256_text(content), "bias_signature": bias},
        admitted=True,
    )


def test_dependency_summary_collapses_families_and_flags_shared_bias():
    items = [evidence("E1", "F1", "B1"), evidence("E2", "F1", "B1"), evidence("E3", "F2")]
    summary = EvidenceDependencyGraph.summarise(items)
    assert summary.raw_count == 3
    assert summary.effective_independent_families == 2
    assert summary.family_members["F1"] == ["E1", "E2"]
    assert summary.shared_bias_signatures["B1"] == ["E1", "E2"]


def test_dependency_graph_records_evidence_and_result(result_factory):
    graph = EvidenceDependencyGraph()
    graph.add_evidence(evidence("E1", "F1"))
    result = result_factory(result_id="R1", dependency_families=["F1"])
    graph.add_result(result)
    assert graph.graph.has_edge("E1", "family:F1")
    assert graph.graph.has_edge("R1", "EV-R1")
    assert EvidenceDependencyGraph.effective_result_weight(result) > 0


def test_aligned_opposing_results_are_substantive_contradiction(result_factory):
    left = result_factory(result_id="L", finding_direction=FindingDirection.SUPPORTS)
    right = result_factory(result_id="R", finding_direction=FindingDirection.FALSIFIES)
    assessment = assess_pair(left, right)
    assert assessment.classification == ContradictionClass.SUBSTANTIVE_CONTRADICTION.value
    assert len(find_substantive_contradictions([left, right])) == 1


def test_scope_mismatch_is_not_substantive_contradiction(result_factory):
    left = result_factory(result_id="L")
    right_scope = ScopeContext(
        construct="different construct",
        population="population",
        period="2020-2025",
        jurisdiction="UK",
        estimand="risk difference",
    )
    right = result_factory(
        result_id="R",
        finding_direction=FindingDirection.FALSIFIES,
        scope=right_scope,
    )
    assessment = assess_pair(left, right)
    assert assessment.classification == ContradictionClass.CONSTRUCT_MISMATCH.value


def test_different_propositions_are_not_comparable(result_factory):
    left = result_factory(result_id="L", proposition_id="P1")
    right = result_factory(result_id="R", proposition_id="P2")
    assert assess_pair(left, right).classification == ContradictionClass.NOT_COMPARABLE.value
