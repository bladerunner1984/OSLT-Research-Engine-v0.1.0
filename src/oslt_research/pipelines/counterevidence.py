from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

from oslt_research.connectors.base import HarvestQuery, SourceConnector
from oslt_research.domain.enums import EvidenceLane
from oslt_research.domain.models import EvidenceObject
from oslt_research.evidence.lane_coding import LaneClassifier, apply_lane_assignment

from .harvest import execute_harvest


#: Query expansions aimed at each mandatory counterevidence lane.
#:
#: The constitution requires counterevidence and null evidence to be retrieved, not merely
#: accepted if it happens to arrive. A single topic query returns whatever the literature
#: surfaces most readily, which is exactly the selection the MD11 hypothesis is about. Each
#: lane therefore gets its own search rather than being filtered out of one shared result set.
LANE_QUERY_TERMS: dict[EvidenceLane, tuple[str, ...]] = {
    EvidenceLane.NULL: (
        "no significant association",
        "null findings",
        "no difference between groups",
    ),
    EvidenceLane.CONTRADICT: (
        "contradictory findings",
        "conflicting evidence",
        "inconsistent with previous",
    ),
    EvidenceLane.RIVAL: (
        "alternative explanation",
        "competing hypothesis",
        "ascertainment artefact",
        "reverse causation",
    ),
    EvidenceLane.REPLICATION: (
        "replication study",
        "failure to replicate",
        "independent replication",
    ),
    EvidenceLane.BIAS_CRITIQUE: (
        "risk of bias",
        "methodological critique",
        "systematic review limitations",
    ),
    EvidenceLane.CORRECTION_RETRACTION: (
        "retracted",
        "expression of concern",
        "correction to",
    ),
}

#: Lanes the claim release gate requires to have been searched before any release.
MANDATORY_LANES: tuple[EvidenceLane, ...] = (
    EvidenceLane.CONTRADICT,
    EvidenceLane.RIVAL,
    EvidenceLane.NULL,
)


@dataclass(frozen=True)
class LaneSearchRecord:
    """Proof that a lane was actually searched, and with what."""

    lane: EvidenceLane
    queries_run: list[str] = field(default_factory=list)
    records_returned: int = 0
    records_lane_confirmed: int = 0
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def searched(self) -> bool:
        """A lane counts as searched only if a query actually completed.

        Returning nothing is a legitimate result and still counts. Failing to run is not.
        """

        return bool(self.queries_run) and not (self.errors and not self.records_returned)


@dataclass(frozen=True)
class CounterevidenceReport:
    base_concept: str
    lane_searches: dict[EvidenceLane, LaneSearchRecord] = field(default_factory=dict)
    evidence: list[EvidenceObject] = field(default_factory=list)

    def lanes_searched(self) -> set[EvidenceLane]:
        return {lane for lane, record in self.lane_searches.items() if record.searched}

    def mandatory_lanes_satisfied(self) -> bool:
        return all(lane in self.lanes_searched() for lane in MANDATORY_LANES)

    def missing_mandatory_lanes(self) -> list[EvidenceLane]:
        searched = self.lanes_searched()
        return [lane for lane in MANDATORY_LANES if lane not in searched]

    def summary(self) -> dict[str, object]:
        return {
            "base_concept": self.base_concept,
            "total_records": len(self.evidence),
            "mandatory_lanes_satisfied": self.mandatory_lanes_satisfied(),
            "missing_mandatory_lanes": [lane.value for lane in self.missing_mandatory_lanes()],
            "per_lane": {
                lane.value: {
                    "queries": record.queries_run,
                    "returned": record.records_returned,
                    "lane_confirmed": record.records_lane_confirmed,
                    "searched": record.searched,
                    "errors": record.errors,
                }
                for lane, record in self.lane_searches.items()
            },
        }


class CounterevidenceHarvester:
    """Runs lane-targeted searches so counterevidence is sought, not merely awaited.

    Records what was searched even when a lane returns nothing. An empty NULL lane after a
    genuine search is a finding about the literature; an empty NULL lane because nobody
    looked is a governance failure, and the two must never be confusable downstream.
    """

    def __init__(
        self,
        *,
        classifier: LaneClassifier | None = None,
        lanes: Sequence[EvidenceLane] | None = None,
        max_records_per_query: int = 25,
    ):
        if max_records_per_query < 1:
            raise ValueError("max_records_per_query must be at least 1")
        self.classifier = classifier or LaneClassifier()
        self.lanes = tuple(lanes) if lanes else tuple(LANE_QUERY_TERMS)
        self.max_records_per_query = max_records_per_query

    async def harvest(
        self,
        *,
        base_concept: str,
        connectors: Iterable[SourceConnector],
        store=None,
        proposition_ids: Sequence[str] = (),
        query_id_prefix: str = "CE",
    ) -> CounterevidenceReport:
        connector_list = list(connectors)
        searches: dict[EvidenceLane, LaneSearchRecord] = {}
        collected: dict[str, EvidenceObject] = {}

        for lane in self.lanes:
            queries_run: list[str] = []
            errors: list[str] = []
            sources: list[str] = []
            returned = 0
            confirmed = 0

            for index, term in enumerate(LANE_QUERY_TERMS.get(lane, ())):
                concept = f"{base_concept} {term}"
                query = HarvestQuery(
                    query_id=f"{query_id_prefix}-{lane.value}-{index}",
                    concept=concept,
                    proposition_ids=list(proposition_ids),
                    max_records=self.max_records_per_query,
                )
                for connector in connector_list:
                    try:
                        result = await execute_harvest(connector, query, store=store)
                    except Exception as exc:  # noqa: BLE001 - one source must not sink the lane
                        errors.append(f"{connector.source_name}:{type(exc).__name__}")
                        continue
                    sources.append(connector.source_name)
                    returned += len(result.evidence)
                    for item in result.evidence:
                        # execute_harvest now lane-codes on construction, so trust the
                        # persisted lane; only re-classify a record that arrived uncoded,
                        # otherwise the report could disagree with the stored corpus.
                        if item.lane_coding is None:
                            item = apply_lane_assignment(item, self.classifier.classify(item))
                        collected.setdefault(item.evidence_id, item)
                        if item.lane is lane:
                            confirmed += 1
                queries_run.append(concept)

            searches[lane] = LaneSearchRecord(
                lane=lane,
                queries_run=queries_run,
                records_returned=returned,
                records_lane_confirmed=confirmed,
                sources=sorted(set(sources)),
                errors=errors,
            )

        return CounterevidenceReport(
            base_concept=base_concept,
            lane_searches=searches,
            evidence=list(collected.values()),
        )
