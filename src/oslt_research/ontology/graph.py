from __future__ import annotations

from collections import defaultdict
from datetime import date
from enum import StrEnum
from typing import Iterable, Sequence

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field

from oslt_research.domain.enums import ClaimTier

from .entities import InstitutionalEntity, InstitutionalRelation, SystemDomain


class ResolutionTier(StrEnum):
    """How much a merge can be trusted.

    Ordered weakest to strongest by MERGE_TIER_ORDER. A coupling verdict that only holds
    at NAME_ONLY is a verdict about a naming coincidence until someone checks identifiers.
    """

    NAME_ONLY = "NAME_ONLY"
    CORROBORATED_NAME = "CORROBORATED_NAME"
    STRONG_IDENTIFIER = "STRONG_IDENTIFIER"


MERGE_TIER_ORDER: dict[ResolutionTier, int] = {
    ResolutionTier.NAME_ONLY: 0,
    ResolutionTier.CORROBORATED_NAME: 1,
    ResolutionTier.STRONG_IDENTIFIER: 2,
}


class CouplingVerdict(StrEnum):
    """Outcome of an MD15-versus-MX09 contest over the admitted subgraph."""

    MD15_COUPLING_SUPPORTED = "MD15_COUPLING_SUPPORTED"
    MX09_ISOLATED_PROCESSES_BETTER = "MX09_ISOLATED_PROCESSES_BETTER"
    CENTRAL_COORDINATION_NOT_COUPLING = "CENTRAL_COORDINATION_NOT_COUPLING"
    INSUFFICIENT_INDEPENDENT_SOURCES = "INSUFFICIENT_INDEPENDENT_SOURCES"
    INSUFFICIENT_ADMITTED_RELATIONS = "INSUFFICIENT_ADMITTED_RELATIONS"


class CouplingAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: CouplingVerdict
    outcome_date: date
    admitted_relations: int
    excluded_relations: int
    temporally_prior_relations: int
    systems_spanned: list[SystemDomain]
    independent_dependency_families: list[str]
    central_entity_id: str | None = None
    merges_applied: dict[str, int] = Field(default_factory=dict)
    minimum_resolution_tier: ResolutionTier | None = None
    claim_tier_ceiling: ClaimTier
    rationale: str
    limitations: list[str] = Field(default_factory=list)


class InstitutionalOntologyGraph:
    """Entity/link layer for institutional mechanism analysis.

    Holds role-typed organisational nodes and typed, dated, independently-sourced edges.
    It answers what the evidence layer cannot: which institutional ties existed, between
    which kinds of body, in what order. It does not itself release claims.
    """

    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()
        self.entities: dict[str, InstitutionalEntity] = {}
        self.relations: dict[str, InstitutionalRelation] = {}

    # ------------------------------------------------------------------ ingest

    def add_entity(self, entity: InstitutionalEntity) -> None:
        self.entities[entity.entity_id] = entity
        self.graph.add_node(
            entity.entity_id,
            canonical_name=entity.canonical_name,
            roles=[role.value for role in entity.roles],
            system_domain=entity.system_domain.value,
            jurisdiction=entity.jurisdiction,
            admitted=entity.admitted,
            dependency_family=entity.dependency_family,
        )

    def add_relation(self, relation: InstitutionalRelation) -> None:
        for endpoint in (relation.source_entity_id, relation.target_entity_id):
            if endpoint not in self.entities:
                raise KeyError(f"unknown entity referenced by relation: {endpoint}")
        self.relations[relation.relation_id] = relation
        self.graph.add_edge(
            relation.source_entity_id,
            relation.target_entity_id,
            key=relation.relation_id,
            relation_type=relation.relation_type.value,
            valid_from=relation.valid_from,
            valid_to=relation.valid_to,
            admitted=relation.admitted,
            dependency_family=relation.dependency_family,
        )

    # -------------------------------------------------------- entity resolution

    def resolve_duplicates(
        self, *, minimum_tier: ResolutionTier = ResolutionTier.NAME_ONLY
    ) -> dict[str, list[str]]:
        """Group entity ids that refer to the same organisation, by evidence strength.

        Three tiers, and the caller decides how much weight a merge must carry:

        STRONG_IDENTIFIER  a shared Companies House number, charity number, ROR or LEI.
        CORROBORATED_NAME  same normalised name and jurisdiction, plus a second signal
                           (a shared weak identifier, or an overlapping counterparty),
                           so the match does not rest on the name alone.
        NAME_ONLY          same normalised name and jurisdiction and nothing else. Two
                           distinct bodies can share a name; this is a lead, not a join.

        Requiring STRONG_IDENTIFIER lets a coupling verdict be recomputed using only
        merges that would survive an identifier-level audit.
        """

        threshold = MERGE_TIER_ORDER[minimum_tier]
        parent: dict[str, str] = {item: item for item in self.entities}

        def find(item: str) -> str:
            while parent[item] != item:
                parent[item] = parent[parent[item]]
                item = parent[item]
            return item

        def union(left: str, right: str) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[max(left_root, right_root)] = min(left_root, right_root)

        by_identifier: dict[tuple[str, str], list[str]] = defaultdict(list)
        by_name: dict[tuple[str, str], list[str]] = defaultdict(list)
        for entity_id, entity in self.entities.items():
            for identifier in entity.strong_identifiers():
                by_identifier[identifier].append(entity_id)
            by_name[(entity.normalised_name(), entity.jurisdiction.casefold())].append(entity_id)

        for group in by_identifier.values():
            for other in group[1:]:
                union(group[0], other)

        if threshold < MERGE_TIER_ORDER[ResolutionTier.STRONG_IDENTIFIER]:
            allow_bare_name = threshold == MERGE_TIER_ORDER[ResolutionTier.NAME_ONLY]
            for group in by_name.values():
                for index, left in enumerate(group):
                    for right in group[index + 1 :]:
                        if allow_bare_name or self._name_match_is_corroborated(left, right):
                            union(left, right)

        clusters: dict[str, list[str]] = defaultdict(list)
        for entity_id in self.entities:
            clusters[find(entity_id)].append(entity_id)
        return {root: sorted(members) for root, members in clusters.items() if len(members) > 1}

    def _counterparties(self) -> dict[str, set[str]]:
        neighbours: dict[str, set[str]] = defaultdict(set)
        for relation in self.relations.values():
            neighbours[relation.source_entity_id].add(relation.target_entity_id)
            neighbours[relation.target_entity_id].add(relation.source_entity_id)
        return neighbours

    def _weak_identifiers(self, entity_id: str) -> set[tuple[str, str]]:
        entity = self.entities[entity_id]
        everything = {
            (namespace, value.strip().casefold())
            for namespace, value in entity.identifiers.items()
            if value.strip()
        }
        return everything - entity.strong_identifiers()

    def _name_match_is_corroborated(self, left: str, right: str) -> bool:
        """A second signal beyond the name: a shared weak id, or a shared counterparty.

        Two records of the same name that also transact with the same third party are far
        more likely to be one body than a coincidence of naming.
        """

        if self._weak_identifiers(left) & self._weak_identifiers(right):
            return True
        neighbours = self._counterparties()
        return bool(neighbours[left] & neighbours[right])

    def merge_tier(self, members: Sequence[str]) -> ResolutionTier:
        """Strongest evidence supporting a merge of these entity ids."""

        identifier_sets = [self.entities[m].strong_identifiers() for m in members]
        if identifier_sets and set.intersection(*identifier_sets):
            return ResolutionTier.STRONG_IDENTIFIER
        for index, left in enumerate(members):
            for right in members[index + 1 :]:
                if self._name_match_is_corroborated(left, right):
                    return ResolutionTier.CORROBORATED_NAME
        return ResolutionTier.NAME_ONLY

    # ------------------------------------------------------------- mechanism

    def admitted_relations(self) -> list[InstitutionalRelation]:
        return [item for item in self.relations.values() if item.admitted]

    def _canonical_map(
        self, minimum_tier: ResolutionTier
    ) -> tuple[dict[str, str], dict[str, int]]:
        """Map every entity id to its resolved-cluster representative.

        Also returns how many clusters were merged and how many of those rested on a
        normalised name alone. A name-only merge is the weakest join in this system, and
        when a coupling verdict depends on one it has to be visible in the result.
        """

        mapping = {entity_id: entity_id for entity_id in self.entities}
        tally: dict[str, int] = defaultdict(int)
        for members in self.resolve_duplicates(minimum_tier=minimum_tier).values():
            representative = members[0]
            for member in members:
                mapping[member] = representative
            tally[self.merge_tier(members).value] += 1
        return mapping, dict(tally)

    def assess_coupling(
        self,
        outcome_date: date,
        relations: Iterable[InstitutionalRelation] | None = None,
        *,
        resolve_entities: bool = False,
        minimum_resolution_tier: ResolutionTier = ResolutionTier.NAME_ONLY,
    ) -> CouplingAssessment:
        """Contest MD15 (structural coupling) against MX09 (isolated processes).

        The test is deliberately hard to pass. An edge counts only if it was admitted,
        and only if it is dated strictly before the outcome it is invoked to explain.
        Coupling additionally requires at least two independent dependency families and
        at least two distinct system domains, so a single document asserting a web of
        ties can never on its own establish a coupled mechanism.
        """

        candidates = list(relations) if relations is not None else list(self.relations.values())
        admitted = [item for item in candidates if item.admitted]

        # Without resolution the same body appearing in two registers stays two nodes, so
        # a tie that genuinely bridges them can never form a connected path. Resolution is
        # opt-in because merging on a weak match would invent the bridge instead.
        canonical: dict[str, str] = {}
        merges: dict[str, int] = {}
        if resolve_entities:
            canonical, merges = self._canonical_map(minimum_resolution_tier)

        def node_of(entity_id: str) -> str:
            return canonical.get(entity_id, entity_id)
        excluded = len(candidates) - len(admitted)
        prior = [item for item in admitted if item.precedes(outcome_date)]

        limitations: list[str] = []
        if resolve_entities and merges:
            total = sum(merges.values())
            breakdown = ", ".join(f"{count} {tier}" for tier, count in sorted(merges.items()))
            limitations.append(f"entity resolution merged {total} cluster(s): {breakdown}")
            weak = merges.get(ResolutionTier.NAME_ONLY.value, 0)
            if weak:
                limitations.append(
                    f"{weak} merged on normalised name alone with no corroborating identifier "
                    "or shared counterparty; any bridge depending on them is a weak join and "
                    "the verdict should not outlive an identifier-level check"
                )
        if excluded:
            limitations.append(f"{excluded} relation(s) failed admission and were excluded")
        if len(admitted) != len(prior):
            limitations.append(
                f"{len(admitted) - len(prior)} admitted relation(s) were not temporally "
                "prior to the outcome and were excluded"
            )
        # If almost everything predates the outcome, the temporal test is not testing.
        # MD15 is a claim about ties that PRECEDE a change; an outcome date later than the
        # whole corpus admits everything and turns ordering into a formality. Observed
        # directly: the same graph returns MD15 against an arbitrary future date and MX09
        # against a real documented one.
        if admitted and len(prior) / len(admitted) > 0.9:
            limitations.append(
                f"TEMPORAL_TEST_NOT_DISCRIMINATING: {len(prior)} of {len(admitted)} admitted "
                f"relations precede {outcome_date.isoformat()}, so the outcome date excludes "
                "almost nothing. A verdict from this is a statement about the corpus, not "
                "about ties preceding a change; use a dated real-world outcome"
            )

        families = sorted({item.dependency_family for item in prior})
        domains: set[SystemDomain] = set()
        for item in prior:
            for endpoint in (item.source_entity_id, item.target_entity_id):
                entity = self.entities.get(node_of(endpoint)) or self.entities.get(endpoint)
                # UNKNOWN is excluded deliberately. An entity whose domain could not be
                # determined must not be able to widen apparent cross-system spread.
                if entity is not None and entity.system_domain is not SystemDomain.UNKNOWN:
                    domains.add(entity.system_domain)
        spanned = sorted(domains, key=lambda value: value.value)

        def build(
            verdict: CouplingVerdict,
            ceiling: ClaimTier,
            rationale: str,
            central: str | None = None,
        ) -> CouplingAssessment:
            return CouplingAssessment(
                verdict=verdict,
                outcome_date=outcome_date,
                admitted_relations=len(admitted),
                excluded_relations=excluded,
                temporally_prior_relations=len(prior),
                systems_spanned=spanned,
                independent_dependency_families=families,
                central_entity_id=central,
                merges_applied=merges,
                minimum_resolution_tier=(
                    minimum_resolution_tier if resolve_entities else None
                ),
                claim_tier_ceiling=ceiling,
                rationale=rationale,
                limitations=limitations,
            )

        if len(prior) < 2:
            return build(
                CouplingVerdict.INSUFFICIENT_ADMITTED_RELATIONS,
                ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
                "Fewer than two admitted, temporally prior relations; no mechanism claim "
                "of any kind is available.",
            )

        if len(families) < 2:
            return build(
                CouplingVerdict.INSUFFICIENT_INDEPENDENT_SOURCES,
                ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
                "All temporally prior relations share one dependency family, so they "
                "cannot corroborate each other. The network may be real, but this "
                "evidence cannot establish it.",
            )

        incident: dict[str, int] = defaultdict(int)
        for item in prior:
            incident[node_of(item.source_entity_id)] += 1
            incident[node_of(item.target_entity_id)] += 1
        central = next(
            (entity_id for entity_id, count in incident.items() if count == len(prior)), None
        )
        if central is not None:
            return build(
                CouplingVerdict.CENTRAL_COORDINATION_NOT_COUPLING,
                ClaimTier.ASSOCIATION_ONLY,
                "Every temporally prior relation is incident to a single entity. MD15 "
                "specifies reinforcement between independent nodes without central "
                "coordination; a hub pattern is a different mechanism and must not be "
                "reported as coupling.",
                central,
            )

        if len(spanned) < 2:
            return build(
                CouplingVerdict.MX09_ISOLATED_PROCESSES_BETTER,
                ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE,
                "Temporally prior relations sit within a single system domain. The MX09 "
                "rival, that change reflects isolated non-coupled processes, explains the "
                "observed pattern at least as well.",
            )

        # MD15 predicts diffusion and feedback, which requires the relations to actually
        # connect. A pile of disconnected dyads spans domains trivially -- every
        # CONTRACTS_WITH edge runs POLICY -> COMMERCIAL by construction -- while being
        # the textbook shape of the MX09 rival: isolated, non-coupled processes. So the
        # test is connectivity, not a domain head-count.
        connected = nx.Graph()
        for item in prior:
            connected.add_edge(node_of(item.source_entity_id), node_of(item.target_entity_id),
                               relation=item)
        components = list(nx.connected_components(connected))

        def qualifies(component: set[str]) -> bool:
            domains = {
                self.entities[node].system_domain
                for node in component
                if node in self.entities
                and self.entities[node].system_domain is not SystemDomain.UNKNOWN
            }
            kinds = {
                connected.edges[edge]["relation"].relation_type
                for edge in connected.subgraph(component).edges
            }
            # More than one kind of tie is the discriminating requirement. A component
            # built from a single relation type is one mechanism repeated: every
            # CONTRACTS_WITH edge runs POLICY -> COMMERCIAL, so domain spread follows
            # from the edge type rather than from anything diffusing between systems.
            return len(component) > 2 and len(domains) > 1 and len(kinds) > 1

        diffusing = [component for component in components if qualifies(component)]
        if not diffusing:
            largest = max(components, key=len, default=set())
            largest_kinds = sorted(
                {
                    connected.edges[edge]["relation"].relation_type.value
                    for edge in connected.subgraph(largest).edges
                }
            )
            corpus_kinds = sorted({item.relation_type.value for item in prior})
            unreached = [kind for kind in corpus_kinds if kind not in largest_kinds]
            return build(
                CouplingVerdict.MX09_ISOLATED_PROCESSES_BETTER,
                ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE,
                "No connected component carries influence between systems. The corpus "
                f"holds {len(corpus_kinds)} tie type(s) ({', '.join(corpus_kinds)}) across "
                f"{len(components)} components, but the largest component has "
                f"{len(largest)} entities joined by only {', '.join(largest_kinds)}"
                + (
                    f"; {', '.join(unreached)} appear only in components that do not "
                    "connect to it, so no path runs from one kind of tie to another. "
                    if unreached
                    else ". "
                )
                + "A component built from one tie type is one mechanism repeated, and its "
                "domain spread follows from that tie type rather than from diffusion. The "
                "MX09 rival, isolated non-coupled processes, explains the pattern better.",
            )

        return build(
            CouplingVerdict.MD15_COUPLING_SUPPORTED,
            ClaimTier.LIMITED_CAUSAL_EVIDENCE,
            f"{len(prior)} admitted relations, dated before the outcome, drawn from "
            f"{len(families)} independent dependency families and spanning {len(spanned)} "
            "system domains, with no single central node. This is consistent with MD15 "
            "cross-system coupling. It remains observational: the registry caps MD15 at "
            "LIMITED_CAUSAL_EVIDENCE and MX09 is not excluded.",
        )
