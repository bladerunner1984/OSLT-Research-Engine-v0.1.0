from datetime import datetime, timezone

from oslt_research.domain.enums import (
    AccessClass,
    EpistemicStatus,
    EvidenceLane,
    FindingDirection,
    SourceStatus,
)
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.provenance import sha256_text
from oslt_research.kernels.academic_knowledge import AcademicKnowledgeProductionKernel


def evidence(
    index: int,
    *,
    kind: str = "publication",
    orientation: str = "NOT_ASSESSABLE",
    published: bool | None = None,
    family: str | None = None,
):
    content = f"record {index}"
    metadata = {
        "content_sha256": sha256_text(content),
        "record_kind": kind,
        "orientation": orientation,
    }
    if published is not None:
        metadata["published"] = published
    return EvidenceObject(
        evidence_id=f"EV-{index}",
        lane=EvidenceLane.UNCLASSIFIED,
        source_status=SourceStatus.VERIFIED,
        epistemic_status=EpistemicStatus.OBSERVATION,
        title=content,
        content=content,
        provenance=ProvenanceRecord(
            source_id="DS033",
            source_uri=f"https://example.test/{index}",
            retrieved_at=datetime.now(timezone.utc),
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        dependency_family=family or f"family-{index}",
        metadata=metadata,
        admitted=True,
    )


def test_no_denominator_produces_descriptive_inconclusive_results():
    items = [evidence(i) for i in range(10)]
    results = AcademicKnowledgeProductionKernel().analyse(
        run_id="RUN", evidence=items, period="2020-2025"
    )
    assert len(results) == 2
    assert all(result.finding_direction == FindingDirection.INCONCLUSIVE for result in results)
    assert all(result.claim_tier.value == "DESCRIPTIVE_EVIDENCE_ONLY" for result in results)
    assert "not identified" in results[0].narrative


def test_orientation_rate_spread_supports_selection_hypothesis():
    items = []
    for i in range(10):
        items.append(
            evidence(
                i,
                kind="registration",
                orientation="FRAMEWORK_A",
                published=i < 9,
            )
        )
    for i in range(10, 20):
        items.append(
            evidence(
                i,
                kind="registration",
                orientation="FRAMEWORK_B",
                published=i < 12,
            )
        )
    results = AcademicKnowledgeProductionKernel().analyse(
        run_id="RUN", evidence=items, period="2020-2025"
    )
    md11, mx14 = results
    assert md11.finding_direction == FindingDirection.SUPPORTS
    assert mx14.finding_direction == FindingDirection.WEAKENS
    assert md11.claim_tier.value == "ASSOCIATION_ONLY"


def test_small_rate_spread_weakens_selection_hypothesis():
    items = []
    for group, start in [("A", 0), ("B", 10)]:
        for i in range(start, start + 10):
            items.append(
                evidence(
                    i,
                    kind="registration",
                    orientation=group,
                    published=(i - start) < 5,
                )
            )
    results = AcademicKnowledgeProductionKernel().analyse(
        run_id="RUN", evidence=items, period="2020-2025"
    )
    assert results[0].finding_direction == FindingDirection.WEAKENS
    assert results[1].finding_direction == FindingDirection.SUPPORTS
