from __future__ import annotations

from datetime import date

import pytest

from oslt_research.domain.enums import AccessClass, ClaimTier, SourceStatus
from oslt_research.domain.models import ProvenanceRecord
from oslt_research.ontology.admission import (
    admit_entity,
    admit_relation,
    assess_relation_admission,
)
from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    InstitutionalRelation,
    RelationType,
    SystemDomain,
    normalise_name,
)
from oslt_research.ontology.graph import CouplingVerdict, InstitutionalOntologyGraph


OUTCOME = date(2020, 1, 1)


def provenance(source_id: str = "SRC-1", **overrides) -> ProvenanceRecord:
    payload = {
        "source_id": source_id,
        "source_uri": f"https://example.org/{source_id}",
        "checksum_sha256": "a" * 64,
        "access_class": AccessClass.OPEN,
    }
    payload.update(overrides)
    return ProvenanceRecord(**payload)


def entity(
    entity_id: str,
    domain: SystemDomain,
    *,
    role: EntityRole = EntityRole.ADVOCACY_ORGANISATION,
    name: str | None = None,
    jurisdiction: str = "UK",
    identifiers: dict[str, str] | None = None,
) -> InstitutionalEntity:
    return admit_entity(
        InstitutionalEntity(
            entity_id=entity_id,
            canonical_name=name or f"Body {entity_id}",
            roles=[role],
            system_domain=domain,
            jurisdiction=jurisdiction,
            identifiers=identifiers or {},
            provenance=provenance(entity_id),
            source_status=SourceStatus.VERIFIED,
            dependency_family=f"family-{entity_id}",
        )
    )


def relation(
    relation_id: str,
    source: str,
    target: str,
    *,
    family: str,
    valid_from: date | None = date(2015, 1, 1),
    status: SourceStatus = SourceStatus.VERIFIED,
    kind: RelationType = RelationType.FUNDS,
) -> InstitutionalRelation:
    return admit_relation(
        InstitutionalRelation(
            relation_id=relation_id,
            source_entity_id=source,
            target_entity_id=target,
            relation_type=kind,
            valid_from=valid_from,
            provenance=provenance(relation_id),
            source_status=status,
            dependency_family=family,
        )
    )


# --------------------------------------------------------------------- entities


def test_normalise_name_folds_legal_suffixes_and_stopwords():
    assert normalise_name("The Example Foundation Ltd") == "example"
    assert normalise_name("EXAMPLE  charity  UK") == "example"


def test_relation_rejects_self_loop_and_inverted_interval():
    with pytest.raises(ValueError, match="self-loop"):
        InstitutionalRelation(
            relation_id="R",
            source_entity_id="A",
            target_entity_id="A",
            relation_type=RelationType.FUNDS,
            provenance=provenance(),
            dependency_family="f",
        )
    with pytest.raises(ValueError, match="valid_to cannot precede valid_from"):
        InstitutionalRelation(
            relation_id="R",
            source_entity_id="A",
            target_entity_id="B",
            relation_type=RelationType.FUNDS,
            valid_from=date(2020, 1, 1),
            valid_to=date(2019, 1, 1),
            provenance=provenance(),
            dependency_family="f",
        )


def test_undated_relation_is_refused_admission():
    decision = assess_relation_admission(
        InstitutionalRelation(
            relation_id="R",
            source_entity_id="A",
            target_entity_id="B",
            relation_type=RelationType.FUNDS,
            provenance=provenance(),
            source_status=SourceStatus.VERIFIED,
            dependency_family="f",
        )
    )
    assert not decision.admitted
    assert "RELATION_UNDATED" in decision.failures


def test_unverified_source_is_refused_admission():
    decision = assess_relation_admission(
        InstitutionalRelation(
            relation_id="R",
            source_entity_id="A",
            target_entity_id="B",
            relation_type=RelationType.FUNDS,
            valid_from=date(2015, 1, 1),
            provenance=provenance(),
            source_status=SourceStatus.UNVERIFIED,
            dependency_family="f",
        )
    )
    assert not decision.admitted
    assert "SOURCE_STATUS_UNVERIFIED" in decision.failures


def test_precedes_requires_a_start_date():
    dated = relation("R1", "A", "B", family="f", valid_from=date(2015, 1, 1))
    assert dated.precedes(OUTCOME) is True
    assert dated.precedes(date(2010, 1, 1)) is False
    undated = InstitutionalRelation(
        relation_id="R2",
        source_entity_id="A",
        target_entity_id="B",
        relation_type=RelationType.FUNDS,
        provenance=provenance(),
        dependency_family="f",
    )
    assert undated.precedes(OUTCOME) is False


# ------------------------------------------------------------------------ graph


def test_add_relation_rejects_unknown_endpoint():
    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("A", SystemDomain.PHILANTHROPIC))
    with pytest.raises(KeyError, match="unknown entity"):
        graph.add_relation(relation("R1", "A", "MISSING", family="f1"))


def test_entity_resolution_merges_on_strong_identifier_not_across_jurisdictions():
    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("A", SystemDomain.ADVOCACY, name="Alpha Trust",
                            identifiers={"charity_number": "12345"}))
    graph.add_entity(entity("B", SystemDomain.ADVOCACY, name="Alpha",
                            identifiers={"charity_number": "12345"}))
    graph.add_entity(entity("C", SystemDomain.ADVOCACY, name="Alpha Trust",
                            jurisdiction="US"))
    clusters = graph.resolve_duplicates()
    assert list(clusters.values()) == [["A", "B"]]


def test_coupling_supported_needs_a_connected_cross_domain_chain():
    """MD15 predicts diffusion, so influence must trace along a connected path."""

    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("F", SystemDomain.PHILANTHROPIC))
    graph.add_entity(entity("A", SystemDomain.ADVOCACY))
    graph.add_entity(entity("G", SystemDomain.CLINICAL))
    graph.add_entity(entity("P", SystemDomain.POLICY))
    graph.add_relation(relation("R1", "F", "A", family="grant-register",
                                kind=RelationType.FUNDS))
    graph.add_relation(relation("R2", "A", "G", family="guideline-archive",
                                kind=RelationType.ADVISES))
    graph.add_relation(relation("R3", "G", "P", family="grant-register",
                                kind=RelationType.ISSUES_GUIDANCE_TO))

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.MD15_COUPLING_SUPPORTED
    assert assessment.claim_tier_ceiling is ClaimTier.LIMITED_CAUSAL_EVIDENCE
    assert len(assessment.independent_dependency_families) == 2
    assert len(assessment.systems_spanned) == 4


def test_disconnected_dyads_spanning_domains_are_the_mx09_rival():
    """Every CONTRACTS_WITH edge spans POLICY->COMMERCIAL by construction.

    Counting domains without requiring connectivity would let any pile of unrelated
    procurement awards read as cross-system coupling. Disconnected dyads are precisely
    what 'isolated, non-coupled processes' means.
    """

    graph = InstitutionalOntologyGraph()
    for name, domain in (
        ("B1", SystemDomain.POLICY), ("S1", SystemDomain.COMMERCIAL),
        ("B2", SystemDomain.POLICY), ("S2", SystemDomain.COMMERCIAL),
    ):
        graph.add_entity(entity(name, domain))
    graph.add_relation(relation("R1", "B1", "S1", family="contracts-finder"))
    graph.add_relation(relation("R2", "B2", "S2", family="find-a-tender"))

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.MX09_ISOLATED_PROCESSES_BETTER
    assert len(assessment.independent_dependency_families) == 2
    assert "No connected component carries influence" in assessment.rationale


def test_single_dependency_family_cannot_establish_coupling():
    """One campaign map asserting a whole network must not triangulate with itself."""

    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("F", SystemDomain.PHILANTHROPIC))
    graph.add_entity(entity("A", SystemDomain.ADVOCACY))
    graph.add_entity(entity("G", SystemDomain.CLINICAL))
    graph.add_entity(entity("P", SystemDomain.POLICY))
    graph.add_relation(relation("R1", "F", "A", family="one-campaign-map"))
    graph.add_relation(relation("R2", "G", "P", family="one-campaign-map"))

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.INSUFFICIENT_INDEPENDENT_SOURCES
    assert assessment.claim_tier_ceiling is ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY


def test_single_system_domain_returns_the_mx09_rival():
    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("A", SystemDomain.ADVOCACY))
    graph.add_entity(entity("B", SystemDomain.ADVOCACY))
    graph.add_entity(entity("C", SystemDomain.ADVOCACY))
    graph.add_entity(entity("D", SystemDomain.ADVOCACY))
    graph.add_relation(relation("R1", "A", "B", family="companies-house"))
    graph.add_relation(relation("R2", "C", "D", family="charity-commission"))

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.MX09_ISOLATED_PROCESSES_BETTER
    assert assessment.systems_spanned == [SystemDomain.ADVOCACY]


def test_hub_pattern_is_reported_as_central_coordination_not_coupling():
    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("HUB", SystemDomain.POLICY))
    graph.add_entity(entity("A", SystemDomain.ADVOCACY))
    graph.add_entity(entity("B", SystemDomain.CLINICAL))
    graph.add_relation(relation("R1", "HUB", "A", family="grant-register"))
    graph.add_relation(relation("R2", "HUB", "B", family="contracts-finder"))

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.CENTRAL_COORDINATION_NOT_COUPLING
    assert assessment.central_entity_id == "HUB"


def test_relations_after_the_outcome_are_excluded_and_disclosed():
    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("F", SystemDomain.PHILANTHROPIC))
    graph.add_entity(entity("A", SystemDomain.ADVOCACY))
    graph.add_entity(entity("G", SystemDomain.CLINICAL))
    graph.add_entity(entity("P", SystemDomain.POLICY))
    graph.add_relation(relation("R1", "F", "A", family="grant-register"))
    graph.add_relation(
        relation("R2", "G", "P", family="guideline-archive", valid_from=date(2024, 1, 1))
    )

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.INSUFFICIENT_ADMITTED_RELATIONS
    assert assessment.temporally_prior_relations == 1
    assert any("temporally prior" in item for item in assessment.limitations)


def test_unadmitted_relations_are_excluded_and_disclosed():
    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("F", SystemDomain.PHILANTHROPIC))
    graph.add_entity(entity("A", SystemDomain.ADVOCACY))
    graph.add_entity(entity("G", SystemDomain.CLINICAL))
    graph.add_entity(entity("P", SystemDomain.POLICY))
    graph.add_relation(relation("R1", "F", "A", family="grant-register"))
    graph.add_relation(
        relation("R2", "G", "P", family="asserted-map", status=SourceStatus.UNVERIFIED)
    )

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.excluded_relations == 1
    assert assessment.verdict is CouplingVerdict.INSUFFICIENT_ADMITTED_RELATIONS
    assert any("failed admission" in item for item in assessment.limitations)
    assert len(graph.admitted_relations()) == 1


def test_single_tie_type_component_is_not_coupling():
    """One mechanism repeated is not systems reinforcing one another."""

    graph = InstitutionalOntologyGraph()
    graph.add_entity(entity("B", SystemDomain.POLICY))
    graph.add_entity(entity("S1", SystemDomain.COMMERCIAL))
    graph.add_entity(entity("S2", SystemDomain.COMMERCIAL))
    graph.add_entity(entity("B2", SystemDomain.POLICY))
    graph.add_relation(relation("R1", "B", "S1", family="contracts-finder",
                                kind=RelationType.CONTRACTS_WITH))
    graph.add_relation(relation("R2", "S1", "B2", family="find-a-tender",
                                kind=RelationType.CONTRACTS_WITH))
    graph.add_relation(relation("R3", "B2", "S2", family="contracts-finder",
                                kind=RelationType.CONTRACTS_WITH))

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.MX09_ISOLATED_PROCESSES_BETTER
    assert "one mechanism repeated" in assessment.rationale


def test_unreached_tie_types_are_named_in_the_rationale():
    """Two tie types in separate components is not a diffusion path, and says so."""

    graph = InstitutionalOntologyGraph()
    for name, domain in (
        ("B", SystemDomain.POLICY), ("S", SystemDomain.COMMERCIAL),
        ("S2", SystemDomain.COMMERCIAL),
        ("F", SystemDomain.POLICY), ("U", SystemDomain.ACADEMIC),
    ):
        graph.add_entity(entity(name, domain))
    graph.add_relation(relation("R1", "B", "S", family="contracts-finder",
                                kind=RelationType.CONTRACTS_WITH))
    graph.add_relation(relation("R2", "S", "S2", family="find-a-tender",
                                kind=RelationType.CONTRACTS_WITH))
    graph.add_relation(relation("R3", "F", "U", family="gtr", kind=RelationType.FUNDS))

    assessment = graph.assess_coupling(OUTCOME)
    assert assessment.verdict is CouplingVerdict.MX09_ISOLATED_PROCESSES_BETTER
    assert "FUNDS" in assessment.rationale
    assert "do not connect to it" in assessment.rationale
