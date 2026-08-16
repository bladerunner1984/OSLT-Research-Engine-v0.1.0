from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Sequence

import httpx

from oslt_research.connectors.base import HarvestQuery, SourceConnector
from oslt_research.domain.enums import EvidenceLane
from oslt_research.domain.models import EvidenceObject
from oslt_research.evidence.lane_coding import LaneClassifier, apply_lane_assignment
from oslt_research.evidence.provenance import sha256_text

from .harvest import execute_harvest


#: Query expansions aimed at each mandatory counterevidence lane.
#:
#: The constitution requires counterevidence and null evidence to be retrieved, not merely
#: accepted if it happens to arrive. A single topic query returns whatever the literature
#: surfaces most readily, which is exactly the selection the MD11 hypothesis is about. Each
#: lane therefore gets its own search rather than being filtered out of one shared result set.
#: SUPPORT is present so the CONTRADICT search can be judged for symmetry rather than
#: taken on trust. Its three terms are the exact mirror of CONTRADICT's three: same
#: grammatical form, same length, same position in the query. If the supporting phrasing
#: were richer or more numerous than the contradicting one, the asymmetry alone would
#: manufacture a shortfall of counterevidence. Note that the classifier never assigns
#: SUPPORT or CONTRADICT (both are proposition-relative), so these lanes can only ever
#: report retrieval counts, never confirmed lane membership.
LANE_QUERY_TERMS: dict[EvidenceLane, tuple[str, ...]] = {
    EvidenceLane.SUPPORT: (
        "consistent findings",
        "confirming evidence",
        "consistent with previous",
    ),
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


#: Lane search outcomes. The whole point of this vocabulary is that a zero which was
#: looked for is a scientific result and a zero which was never looked for is a
#: governance failure, and the two must never collapse into the same value.
STATUS_NOT_ATTEMPTED = "NOT_ATTEMPTED"          # no query was even issued for this lane
STATUS_UNSEARCHED_ERROR = "UNSEARCHED_ERROR"    # every query failed: HTTP/timeout/429
STATUS_SEARCHED_PARTIAL = "SEARCHED_PARTIAL"    # some queries completed, some failed
STATUS_SEARCHED_COMPLETE = "SEARCHED_COMPLETE"  # every query completed against every source

#: Statuses that count as "this lane was searched" for MANDATORY_LANES.
SEARCHED_STATUSES = (STATUS_SEARCHED_COMPLETE, STATUS_SEARCHED_PARTIAL)


@dataclass(frozen=True)
class LaneSearchRecord:
    """Proof that a lane was actually searched, and with what."""

    lane: EvidenceLane
    queries_run: list[str] = field(default_factory=list)
    records_returned: int = 0
    records_lane_confirmed: int = 0
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    #: Queries that completed against at least one source without raising. `None` means
    #: the caller did not track completion, in which case `status` falls back to the
    #: original conservative inference. Every record produced by `harvest` sets it.
    queries_completed: list[str] | None = None
    searched_at: str = ""

    @property
    def status(self) -> str:
        if not self.queries_run:
            return STATUS_NOT_ATTEMPTED
        completed = self.queries_completed
        if completed is None:
            # Legacy inference: results prove at least one query completed; errors with
            # no results prove none did.
            if self.errors and not self.records_returned:
                return STATUS_UNSEARCHED_ERROR
            return STATUS_SEARCHED_PARTIAL if self.errors else STATUS_SEARCHED_COMPLETE
        if not completed:
            return STATUS_UNSEARCHED_ERROR
        if self.errors or len(completed) < len(self.queries_run):
            return STATUS_SEARCHED_PARTIAL
        return STATUS_SEARCHED_COMPLETE

    @property
    def searched(self) -> bool:
        """A lane counts as searched only if a query actually completed.

        Returning nothing is a legitimate result and still counts. Failing to run is not.
        """

        return self.status in SEARCHED_STATUSES

    @property
    def genuine_zero(self) -> bool:
        """A recorded, reportable "we looked everywhere and there is nothing" zero.

        Deliberately requires SEARCHED_COMPLETE: a partial sweep that returned nothing
        cannot be cited as an absence, because the part that failed is where the missing
        records would have been.
        """

        return self.status == STATUS_SEARCHED_COMPLETE and self.records_returned == 0

    def as_row(self) -> dict[str, object]:
        return {
            "lane": self.lane.value,
            "status": self.status,
            "searched": self.searched,
            "genuine_zero": self.genuine_zero,
            "mandatory": self.lane in MANDATORY_LANES,
            "queries_run": list(self.queries_run),
            "queries_completed": (
                None if self.queries_completed is None else list(self.queries_completed)
            ),
            "records_returned": self.records_returned,
            "records_lane_confirmed": self.records_lane_confirmed,
            "sources": list(self.sources),
            "errors": list(self.errors),
            "searched_at": self.searched_at,
        }


class MandatoryLaneGapError(RuntimeError):
    """Raised when a harvest is treated as complete without searching every mandatory lane.

    Exists so an incomplete counterevidence sweep is loud. The failure this class guards
    against is not "we found no contradicting evidence" - that is a result - but "we
    concluded there was none without looking", which is unfalsifiable and would entitle a
    reviewer to discard the corpus as confirmation-biased.
    """


@dataclass(frozen=True)
class CounterevidenceReport:
    base_concept: str
    lane_searches: dict[EvidenceLane, LaneSearchRecord] = field(default_factory=dict)
    evidence: list[EvidenceObject] = field(default_factory=list)
    proposition_ids: list[str] = field(default_factory=list)

    def lanes_searched(self) -> set[EvidenceLane]:
        return {lane for lane, record in self.lane_searches.items() if record.searched}

    def mandatory_lanes_satisfied(self) -> bool:
        return all(lane in self.lanes_searched() for lane in MANDATORY_LANES)

    def missing_mandatory_lanes(self) -> list[EvidenceLane]:
        searched = self.lanes_searched()
        return [lane for lane in MANDATORY_LANES if lane not in searched]

    def mandatory_lane_status(self) -> dict[str, str]:
        """The status of every mandatory lane, including ones never attempted."""

        return {
            lane.value: (
                self.lane_searches[lane].status
                if lane in self.lane_searches
                else STATUS_NOT_ATTEMPTED
            )
            for lane in MANDATORY_LANES
        }

    def genuine_zero_lanes(self) -> list[EvidenceLane]:
        """Lanes fully searched that returned nothing - a reportable scientific zero."""

        return [lane for lane, record in self.lane_searches.items() if record.genuine_zero]

    def enforce_mandatory_lanes(self) -> None:
        """Refuse to let an incomplete sweep pass as a complete one."""

        missing = self.missing_mandatory_lanes()
        if missing:
            raise MandatoryLaneGapError(
                "mandatory counterevidence lanes not searched for "
                f"{self.base_concept!r}: "
                + ", ".join(
                    f"{lane.value}={self.mandatory_lane_status()[lane.value]}"
                    for lane in missing
                )
            )

    def summary(self) -> dict[str, object]:
        return {
            "base_concept": self.base_concept,
            "proposition_ids": list(self.proposition_ids),
            "total_records": len(self.evidence),
            "mandatory_lanes_satisfied": self.mandatory_lanes_satisfied(),
            "missing_mandatory_lanes": [lane.value for lane in self.missing_mandatory_lanes()],
            "mandatory_lane_status": self.mandatory_lane_status(),
            "genuine_zero_lanes": [lane.value for lane in self.genuine_zero_lanes()],
            "per_lane": {
                lane.value: {
                    "queries": record.queries_run,
                    "returned": record.records_returned,
                    "lane_confirmed": record.records_lane_confirmed,
                    "searched": record.searched,
                    "status": record.status,
                    "genuine_zero": record.genuine_zero,
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
        request_delay_seconds: float = 0.0,
        max_retries: int = 3,
        backoff_seconds: float = 5.0,
    ):
        if max_records_per_query < 1:
            raise ValueError("max_records_per_query must be at least 1")
        if request_delay_seconds < 0:
            raise ValueError("request_delay_seconds must not be negative")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self.classifier = classifier or LaneClassifier()
        self.lanes = tuple(lanes) if lanes else tuple(LANE_QUERY_TERMS)
        self.max_records_per_query = max_records_per_query
        #: Politeness pacing applied before every request, from the first one. Defaults to
        #: zero so unit tests with stub connectors stay instant; live runners set it.
        self.request_delay_seconds = request_delay_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    @staticmethod
    def _is_rate_limited(exc: Exception) -> bool:
        return (
            isinstance(exc, httpx.HTTPStatusError)
            and exc.response is not None
            and exc.response.status_code in (429, 503)
        )

    async def _execute(self, connector, query, store):
        """Run one search, pacing every request and backing off on rate limits.

        A rate limit that is retried and still fails is an ERROR, never a zero: the lane
        must come out UNSEARCHED_ERROR rather than "searched, nothing found".
        """

        attempt = 0
        while True:
            if self.request_delay_seconds:
                await asyncio.sleep(self.request_delay_seconds)
            try:
                return await execute_harvest(connector, query, store=store)
            except Exception as exc:  # noqa: BLE001 - classified immediately below
                if attempt >= self.max_retries or not self._is_rate_limited(exc):
                    raise
                await asyncio.sleep(self.backoff_seconds * (2**attempt))
                attempt += 1

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

            completed: list[str] = []
            for index, term in enumerate(LANE_QUERY_TERMS.get(lane, ())):
                concept = f"{base_concept} {term}"
                query = HarvestQuery(
                    query_id=f"{query_id_prefix}-{lane.value}-{index}",
                    concept=concept,
                    proposition_ids=list(proposition_ids),
                    max_records=self.max_records_per_query,
                )
                any_source_completed = False
                for connector in connector_list:
                    try:
                        result = await self._execute(connector, query, store)
                    except Exception as exc:  # noqa: BLE001 - one source must not sink the lane
                        errors.append(f"{connector.source_name}:{type(exc).__name__}")
                        continue
                    any_source_completed = True
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
                if any_source_completed:
                    completed.append(concept)

            searches[lane] = LaneSearchRecord(
                lane=lane,
                queries_run=queries_run,
                records_returned=returned,
                records_lane_confirmed=confirmed,
                sources=sorted(set(sources)),
                errors=errors,
                queries_completed=completed,
                searched_at=datetime.now(timezone.utc).isoformat(),
            )

        return CounterevidenceReport(
            base_concept=base_concept,
            lane_searches=searches,
            evidence=list(collected.values()),
            proposition_ids=list(proposition_ids),
        )


# --------------------------------------------------------------------- persistence

#: A separate table, because the subject of the record is the SEARCH, not any record it
#: returned. A lane that returned nothing has no evidence row to hang provenance from,
#: and that is precisely the case that has to be persisted.
LANE_SEARCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS lane_search_records (
    search_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    base_concept TEXT NOT NULL,
    proposition_ids TEXT NOT NULL,
    lane TEXT NOT NULL,
    status TEXT NOT NULL,
    searched INTEGER NOT NULL,
    genuine_zero INTEGER NOT NULL,
    mandatory INTEGER NOT NULL,
    queries_attempted INTEGER NOT NULL,
    queries_completed INTEGER NOT NULL,
    records_returned INTEGER NOT NULL,
    records_lane_confirmed INTEGER NOT NULL,
    searched_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
"""


def search_id_for(run_id: str, base_concept: str, lane: EvidenceLane) -> str:
    return f"LS-{run_id}-{sha256_text(base_concept)[:12].upper()}-{lane.value}"


def save_lane_searches(store, *, run_id: str, report: CounterevidenceReport) -> list[str]:
    """Persist one row per lane, including lanes that were attempted and failed.

    Rows are written for every lane in the report, searched or not. Writing only the
    successful lanes would recreate the exact ambiguity this table exists to remove.
    """

    store.initialise()
    rows = []
    for lane, record in report.lane_searches.items():
        payload = record.as_row()
        payload["run_id"] = run_id
        payload["base_concept"] = report.base_concept
        payload["proposition_ids"] = list(report.proposition_ids)
        rows.append(
            (
                search_id_for(run_id, report.base_concept, lane),
                run_id,
                report.base_concept,
                json.dumps(list(report.proposition_ids)),
                lane.value,
                record.status,
                int(record.searched),
                int(record.genuine_zero),
                int(lane in MANDATORY_LANES),
                len(record.queries_run),
                len(record.queries_completed or []),
                record.records_returned,
                record.records_lane_confirmed,
                record.searched_at,
                json.dumps(payload, default=str),
            )
        )
    with store.transaction() as connection:
        connection.executescript(LANE_SEARCH_SCHEMA)
        connection.executemany(
            """
            INSERT INTO lane_search_records (
                search_id, run_id, base_concept, proposition_ids, lane, status,
                searched, genuine_zero, mandatory, queries_attempted, queries_completed,
                records_returned, records_lane_confirmed, searched_at, payload_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(search_id) DO UPDATE SET
                status=excluded.status, searched=excluded.searched,
                genuine_zero=excluded.genuine_zero,
                queries_attempted=excluded.queries_attempted,
                queries_completed=excluded.queries_completed,
                records_returned=excluded.records_returned,
                records_lane_confirmed=excluded.records_lane_confirmed,
                searched_at=excluded.searched_at, payload_json=excluded.payload_json
            """,
            rows,
        )
    return [row[0] for row in rows]


def load_lane_searches(store, *, run_id: str | None = None) -> list[dict[str, object]]:
    """Read persisted lane searches back, so the corpus can answer "did anyone look?"."""

    store.initialise()
    with store.transaction() as connection:
        connection.executescript(LANE_SEARCH_SCHEMA)
        sql = "SELECT payload_json FROM lane_search_records"
        params: tuple[object, ...] = ()
        if run_id:
            sql += " WHERE run_id = ?"
            params = (run_id,)
        sql += " ORDER BY search_id"
        rows = connection.execute(sql, params).fetchall()
    return [json.loads(row[0]) for row in rows]
