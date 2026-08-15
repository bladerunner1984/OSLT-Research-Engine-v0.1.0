from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from oslt_research.ontology.entities import InstitutionalEntity, InstitutionalRelation
from oslt_research.ontology.graph import (
    CouplingAssessment,
    InstitutionalOntologyGraph,
    ResolutionTier,
)


class RegisterFragment(Protocol):
    """What every register connector returns."""

    entities: list[InstitutionalEntity]
    relations: list[InstitutionalRelation]


class IdentifierResolver(Protocol):
    def resolve(self, entities: Any) -> Any: ...


@dataclass(frozen=True)
class StrandBRun:
    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    per_source: dict[str, int] = field(default_factory=dict)
    source_failures: dict[str, str] = field(default_factory=dict)
    resolver_summaries: dict[str, dict] = field(default_factory=dict)
    assessments: dict[str, CouplingAssessment] = field(default_factory=dict)

    @property
    def strong_identifier_count(self) -> int:
        return sum(1 for item in self.entities if item.strong_identifiers())

    def summary(self) -> dict[str, object]:
        return {
            "entities": len(self.entities),
            "relations": len(self.relations),
            "entities_with_strong_identifier": self.strong_identifier_count,
            "dependency_families": len({item.dependency_family for item in self.relations}),
            "relation_types": sorted({item.relation_type.value for item in self.relations}),
            "per_source": self.per_source,
            "source_failures": self.source_failures,
            "verdicts": {
                key: value.verdict.value for key, value in sorted(self.assessments.items())
            },
        }


def run_strand_b(
    *,
    fragments: dict[str, RegisterFragment],
    resolvers: dict[str, IdentifierResolver] | None = None,
    outcome_dates: list[date] | None = None,
    minimum_tier: ResolutionTier = ResolutionTier.STRONG_IDENTIFIER,
    store=None,
) -> StrandBRun:
    """Assemble the institutional graph from every register and assess it.

    Two design choices carry the weight here.

    Resolvers run in sequence and each skips entities that already carry a strong
    identifier, so Companies House claims what it can, then the Charity Commission, then
    ROR. Order therefore matters and is the caller's to decide.

    Coupling is assessed at STRONG_IDENTIFIER by default. Every positive MD15 result this
    project has produced evaporated when merges on naming coincidence were barred, so the
    permissive tier is opt-in rather than the default a careless caller would inherit.

    Assessing against several real outcome dates rather than one is deliberate. A single
    date is a free parameter the verdict turns on, and the same graph has returned MD15
    against a date chosen by hand and MX09 against dates fixed by Parliament.
    """

    graph = InstitutionalOntologyGraph()
    entities: list[InstitutionalEntity] = []
    relations: list[InstitutionalRelation] = []
    per_source: dict[str, int] = {}
    failures: dict[str, str] = {}

    for name, fragment in fragments.items():
        try:
            entities.extend(fragment.entities)
            relations.extend(fragment.relations)
            per_source[name] = len(fragment.relations)
        except Exception as exc:  # noqa: BLE001 - one register must not sink the run
            failures[name] = f"{type(exc).__name__}: {exc}"

    resolver_summaries: dict[str, dict] = {}
    for name, resolver in (resolvers or {}).items():
        try:
            report = resolver.resolve(entities)
            entities = list(report.entities)
            resolver_summaries[name] = report.summary()
        except Exception as exc:  # noqa: BLE001 - resolution is an improvement, not a gate
            failures[f"resolver:{name}"] = f"{type(exc).__name__}: {exc}"

    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        # A relation whose endpoints did not survive resolution cannot be placed.
        if (
            relation.source_entity_id in graph.entities
            and relation.target_entity_id in graph.entities
        ):
            graph.add_relation(relation)

    assessments: dict[str, CouplingAssessment] = {}
    for outcome in outcome_dates or []:
        assessments[outcome.isoformat()] = graph.assess_coupling(
            outcome, resolve_entities=True, minimum_resolution_tier=minimum_tier
        )

    if store is not None:
        store.save_entities(graph.entities.values())
        store.save_relations(graph.relations.values())

    return StrandBRun(
        entities=list(graph.entities.values()),
        relations=list(graph.relations.values()),
        per_source=per_source,
        source_failures=failures,
        resolver_summaries=resolver_summaries,
        assessments=assessments,
    )
