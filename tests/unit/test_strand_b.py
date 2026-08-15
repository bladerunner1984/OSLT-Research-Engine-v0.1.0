from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import ProvenanceRecord
from oslt_research.ontology.admission import admit_entity, admit_relation
from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    InstitutionalRelation,
    RelationType,
    SystemDomain,
)
from oslt_research.ontology.graph import CouplingVerdict, ResolutionTier
from oslt_research.pipelines.strand_b import run_strand_b


def provenance() -> ProvenanceRecord:
    return ProvenanceRecord(source_id="S", source_uri="https://x",
                            checksum_sha256="a" * 64, access_class=AccessClass.OPEN)


def entity(eid: str, domain=SystemDomain.POLICY, ids=None) -> InstitutionalEntity:
    return admit_entity(InstitutionalEntity(
        entity_id=eid, canonical_name=f"Body {eid}", roles=[EntityRole.OTHER],
        system_domain=domain, jurisdiction="UK", identifiers=ids or {},
        provenance=provenance(), source_status=SourceStatus.VERIFIED,
        dependency_family=f"fam-{eid}"))


def relation(rid, src, tgt, family, kind=RelationType.FUNDS, when=date(2015, 1, 1)):
    return admit_relation(InstitutionalRelation(
        relation_id=rid, source_entity_id=src, target_entity_id=tgt, relation_type=kind,
        valid_from=when, provenance=provenance(), source_status=SourceStatus.VERIFIED,
        dependency_family=family))


@dataclass
class Fragment:
    entities: list
    relations: list


class Resolver:
    def __init__(self, tag: str, add: dict | None = None, fail: bool = False):
        self.tag, self.add, self.fail = tag, add or {}, fail

    def resolve(self, entities):
        if self.fail:
            raise RuntimeError("resolver down")

        class Report:
            pass

        report = Report()
        report.entities = [
            e.model_copy(update={"identifiers": {**e.identifiers, **self.add}})
            if not e.strong_identifiers() else e
            for e in entities
        ]
        report.summary = lambda: {"tag": self.tag, "count": len(entities)}
        return report


def test_fragments_are_merged_into_one_graph():
    run = run_strand_b(fragments={
        "a": Fragment([entity("A"), entity("B", SystemDomain.COMMERCIAL)],
                      [relation("R1", "A", "B", "fam-a")]),
        "b": Fragment([entity("C", SystemDomain.ADVOCACY)], []),
    })
    assert len(run.entities) == 3
    assert run.per_source == {"a": 1, "b": 0}


def test_a_relation_whose_endpoint_is_absent_is_not_placed():
    run = run_strand_b(fragments={
        "a": Fragment([entity("A")], [relation("R1", "A", "MISSING", "fam-a")]),
    })
    assert run.relations == []


def test_resolvers_run_in_sequence_and_are_summarised():
    run = run_strand_b(
        fragments={"a": Fragment([entity("A")], [])},
        resolvers={"first": Resolver("first", {"companies_house": "01234567"})},
    )
    assert run.strong_identifier_count == 1
    assert run.resolver_summaries["first"]["tag"] == "first"


def test_a_later_resolver_does_not_overwrite_an_earlier_identifier():
    """Each resolver skips entities that already carry a strong identifier."""

    run = run_strand_b(
        fragments={"a": Fragment([entity("A")], [])},
        resolvers={
            "first": Resolver("first", {"companies_house": "01234567"}),
            "second": Resolver("second", {"companies_house": "09999999"}),
        },
    )
    assert run.entities[0].identifiers["companies_house"] == "01234567"


def test_a_failing_resolver_is_recorded_not_fatal():
    """Resolution is an improvement, not a gate."""

    run = run_strand_b(
        fragments={"a": Fragment([entity("A")], [])},
        resolvers={"broken": Resolver("broken", fail=True)},
    )
    assert "resolver:broken" in run.source_failures
    assert len(run.entities) == 1


def test_assessment_runs_for_every_outcome_date():
    run = run_strand_b(
        fragments={"a": Fragment(
            [entity("A"), entity("B", SystemDomain.COMMERCIAL)],
            [relation("R1", "A", "B", "fam-a")],
        )},
        outcome_dates=[date(2010, 1, 1), date(2020, 1, 1)],
    )
    assert set(run.assessments) == {"2010-01-01", "2020-01-01"}


def test_verdict_differs_by_outcome_date():
    """A single date is a free parameter the verdict turns on."""

    run = run_strand_b(
        fragments={"a": Fragment(
            [entity("A"), entity("B", SystemDomain.COMMERCIAL)],
            [relation("R1", "A", "B", "fam-a", when=date(2015, 1, 1))],
        )},
        outcome_dates=[date(2010, 1, 1), date(2020, 1, 1)],
    )
    early = run.assessments["2010-01-01"]
    late = run.assessments["2020-01-01"]
    assert early.temporally_prior_relations == 0
    assert late.temporally_prior_relations == 1


def test_strong_identifier_is_the_default_tier():
    """Every positive MD15 result so far evaporated at this tier; permissive is opt-in."""

    run = run_strand_b(
        fragments={"a": Fragment(
            [entity("A"), entity("B", SystemDomain.COMMERCIAL)],
            [relation("R1", "A", "B", "fam-a")],
        )},
        outcome_dates=[date(2020, 1, 1)],
    )
    assert run.assessments["2020-01-01"].minimum_resolution_tier is ResolutionTier.STRONG_IDENTIFIER


def test_summary_reports_families_and_tie_types():
    run = run_strand_b(fragments={"a": Fragment(
        [entity("A"), entity("B", SystemDomain.COMMERCIAL), entity("C")],
        [relation("R1", "A", "B", "fam-a"),
         relation("R2", "B", "C", "fam-b", kind=RelationType.ADVISES)],
    )})
    summary = run.summary()
    assert summary["dependency_families"] == 2
    assert summary["relation_types"] == ["ADVISES", "FUNDS"]


def test_empty_input_is_safe():
    run = run_strand_b(fragments={})
    assert run.entities == [] and run.relations == []
