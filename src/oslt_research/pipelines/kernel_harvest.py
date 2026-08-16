from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from oslt_research.connectors.base import HarvestQuery, SourceConnector
from oslt_research.domain.enums import EvidenceLane
from oslt_research.domain.models import EvidenceObject

from .counterevidence import (
    MANDATORY_LANES,
    CounterevidenceHarvester,
    CounterevidenceReport,
    save_lane_searches,
)
from .harvest import execute_harvest


#: Words that carry no discriminating power in a bibliographic search and only dilute it.
_STOPWORDS = frozenset(
    {
        "the", "and", "or", "of", "in", "to", "a", "an", "for", "with", "by", "on",
        "not", "is", "are", "may", "must", "be", "been", "that", "this", "than",
        "after", "before", "under", "from", "at", "as", "its", "their",
    }
)


@dataclass(frozen=True)
class PropositionQuery:
    proposition_id: str
    model_family: str
    domain: str
    concept: str
    outcome_construct: str


@dataclass(frozen=True)
class KernelHarvestReport:
    per_proposition: dict[str, int] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    evidence: list[EvidenceObject] = field(default_factory=list)

    @property
    def attempted(self) -> int:
        return len(self.per_proposition) + len(self.failures)

    def summary(self) -> dict[str, object]:
        counts = sorted(self.per_proposition.values())
        return {
            "propositions_attempted": self.attempted,
            "propositions_harvested": len(self.per_proposition),
            "propositions_failed": len(self.failures),
            "total_records": len(self.evidence),
            "median_records_per_proposition": counts[len(counts) // 2] if counts else 0,
            "propositions_with_no_results": [
                key for key, value in self.per_proposition.items() if value == 0
            ],
            "failures": self.failures,
        }


def _terms(text: str, limit: int) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text.lower())
    seen: list[str] = []
    for word in words:
        if word in _STOPWORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) >= limit:
            break
    return seen


def build_proposition_queries(registry_root: str | Path) -> list[PropositionQuery]:
    """Derive one search concept per proposition from the registry.

    Built from the domain and the primary outcome construct rather than the statement.
    A proposition statement is a claim, and searching a claim biases retrieval towards
    papers that phrase things the same way - which is the selection MD11 is about. The
    domain and outcome describe the subject matter without asserting a direction.
    """

    rows = list(
        csv.DictReader((Path(registry_root) / "hypotheses.csv").open(encoding="utf-8-sig"))
    )
    queries: list[PropositionQuery] = []
    for row in rows:
        domain = (row.get("domain") or "").strip()
        outcome = (row.get("primary_outcome_construct") or "").strip()
        concept = " ".join(_terms(f"{domain} {outcome}", limit=8))
        if not concept:
            continue
        queries.append(
            PropositionQuery(
                proposition_id=row.get("proposition_id", ""),
                model_family=row.get("model_family", ""),
                domain=domain,
                concept=concept,
                outcome_construct=outcome,
            )
        )
    return queries


async def harvest_for_kernels(
    *,
    queries: Sequence[PropositionQuery],
    connectors: Iterable[SourceConnector],
    store=None,
    max_records_per_proposition: int = 100,
    cohort_lexicon: Sequence[str] = (),
) -> KernelHarvestReport:
    """Harvest evidence for every proposition, tagging each record with its proposition.

    One connector failing on one proposition must not sink the sweep: a partial corpus
    with the gaps named is usable, and an aborted sweep is not.
    """

    connector_list = list(connectors)
    per_proposition: dict[str, int] = {}
    failures: dict[str, str] = {}
    collected: dict[str, EvidenceObject] = {}

    for item in queries:
        found = 0
        errors: list[str] = []
        for connector in connector_list:
            query = HarvestQuery(
                query_id=f"KH-{item.proposition_id}",
                concept=item.concept,
                proposition_ids=[item.proposition_id],
                max_records=max_records_per_proposition,
            )
            try:
                result = await execute_harvest(
                    connector, query, store=store, cohort_lexicon=cohort_lexicon
                )
            except Exception as exc:  # noqa: BLE001 - one source must not sink the sweep
                errors.append(f"{connector.source_name}:{type(exc).__name__}")
                continue
            for record in result.evidence:
                found += 1
                existing = collected.get(record.evidence_id)
                if existing is None:
                    collected[record.evidence_id] = record
                    continue
                # The same paper can answer to several propositions. Merge rather than
                # discard, or the corpus silently loses proposition coverage.
                merged = sorted(set(existing.proposition_ids) | set(record.proposition_ids))
                collected[record.evidence_id] = existing.model_copy(
                    update={"proposition_ids": merged}
                )

        if errors and found == 0:
            failures[item.proposition_id] = ",".join(errors)
        else:
            per_proposition[item.proposition_id] = found

    return KernelHarvestReport(
        per_proposition=per_proposition,
        failures=failures,
        evidence=list(collected.values()),
    )


# ------------------------------------------------- counterevidence on the corpus path


@dataclass(frozen=True)
class CounterevidenceSweepReport:
    """The result of running lane-targeted counterevidence searches per proposition.

    Carries the incomplete propositions as data rather than raising, because a sweep that
    covered 60 of 64 propositions is worth keeping - provided the 4 gaps are named. What
    it must never do is present a gap as a zero.
    """

    per_proposition: dict[str, CounterevidenceReport] = field(default_factory=dict)
    persisted_search_ids: list[str] = field(default_factory=list)
    run_id: str = ""

    @property
    def incomplete_propositions(self) -> dict[str, list[str]]:
        return {
            key: [lane.value for lane in report.missing_mandatory_lanes()]
            for key, report in self.per_proposition.items()
            if not report.mandatory_lanes_satisfied()
        }

    @property
    def complete(self) -> bool:
        return not self.incomplete_propositions

    def lane_totals(self) -> dict[str, dict[str, int]]:
        totals: dict[str, dict[str, int]] = {}
        for report in self.per_proposition.values():
            for lane, record in report.lane_searches.items():
                bucket = totals.setdefault(
                    lane.value,
                    {
                        "returned": 0,
                        "lane_confirmed": 0,
                        "searched_complete": 0,
                        "searched_partial": 0,
                        "unsearched": 0,
                        "genuine_zero": 0,
                    },
                )
                bucket["returned"] += record.records_returned
                bucket["lane_confirmed"] += record.records_lane_confirmed
                if record.status == "SEARCHED_COMPLETE":
                    bucket["searched_complete"] += 1
                elif record.status == "SEARCHED_PARTIAL":
                    bucket["searched_partial"] += 1
                else:
                    bucket["unsearched"] += 1
                bucket["genuine_zero"] += int(record.genuine_zero)
        return totals

    def summary(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "propositions": len(self.per_proposition),
            "mandatory_lanes": [lane.value for lane in MANDATORY_LANES],
            "complete": self.complete,
            "incomplete_propositions": self.incomplete_propositions,
            "lane_totals": self.lane_totals(),
            "persisted_search_records": len(self.persisted_search_ids),
            "per_proposition": {
                key: report.summary() for key, report in self.per_proposition.items()
            },
        }


async def harvest_counterevidence_for_kernels(
    *,
    queries: Sequence[PropositionQuery],
    connectors: Iterable[SourceConnector],
    store=None,
    run_id: str,
    max_records_per_query: int = 25,
    request_delay_seconds: float = 1.0,
    lanes: Sequence[EvidenceLane] | None = None,
) -> CounterevidenceSweepReport:
    """Run the counterevidence lane sweep on the corpus path, once per proposition.

    Uses `PropositionQuery.concept` as the base concept, which
    `build_proposition_queries` derives from the registry's `domain` and
    `primary_outcome_construct` - never from `statement`. Searching the statement would
    retrieve papers phrased like the claim, which is mechanised confirmation bias; the
    lane terms are then appended to that neutral subject-matter stem, identically for
    every lane, so the SUPPORT and CONTRADICT searches differ only by the mirrored lane
    terms and nothing else.

    Lane searches are persisted for every lane attempted, including lanes whose every
    query failed. That is the whole point: "searched and found nothing" and "never
    searched" have to be different rows, not the same absence.
    """

    harvester = CounterevidenceHarvester(
        max_records_per_query=max_records_per_query,
        request_delay_seconds=request_delay_seconds,
        lanes=lanes,
    )
    connector_list = list(connectors)
    per_proposition: dict[str, CounterevidenceReport] = {}
    persisted: list[str] = []

    for item in queries:
        report = await harvester.harvest(
            base_concept=item.concept,
            connectors=connector_list,
            store=store,
            proposition_ids=[item.proposition_id],
            query_id_prefix=f"CE-{item.proposition_id}",
        )
        per_proposition[item.proposition_id] = report
        if store is not None:
            persisted.extend(save_lane_searches(store, run_id=run_id, report=report))

    return CounterevidenceSweepReport(
        per_proposition=per_proposition,
        persisted_search_ids=persisted,
        run_id=run_id,
    )
