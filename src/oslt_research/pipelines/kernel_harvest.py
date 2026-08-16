from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from oslt_research.connectors.base import HarvestQuery, SourceConnector
from oslt_research.domain.enums import AuthorityLevel, EvidenceLane
from oslt_research.domain.models import EvidenceObject, RunManifest
from oslt_research.evidence.journal import ResearchComputationJournal
from oslt_research.evidence.provenance import canonical_json_hash, sha256_bytes
from oslt_research.governance.authority import NOT_PREREGISTERED
from oslt_research.settings import repository_root

from .counterevidence import (
    MANDATORY_LANES,
    CounterevidenceHarvester,
    CounterevidenceReport,
    save_lane_searches,
)
from .harvest import execute_harvest
from .run_manifest import build_run_manifest


#: Recorded on every corpus-path manifest. The bibliographic APIs this pipeline reads are
#: live services whose server-side indexes are revised without notice and which expose no
#: snapshot identifier, so an identical query on an identical commit can legitimately
#: return a different record set. Stating that limit is part of the manifest's job;
#: omitting it would let the commit and config hashes imply a reproducibility the sources
#: cannot actually provide.
_SERVER_STATE_LIMIT = (
    "NOT_CAPTURABLE: upstream bibliographic APIs expose no index snapshot id or version; "
    "re-running this manifest reproduces the query, not necessarily the record set"
)


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
    run_id: str = ""

    @property
    def attempted(self) -> int:
        return len(self.per_proposition) + len(self.failures)

    def summary(self) -> dict[str, object]:
        counts = sorted(self.per_proposition.values())
        return {
            "run_id": self.run_id,
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


def _registry_hashes(root: Path | None = None) -> dict[str, str]:
    """Hash the registry files that decide which propositions were searched and how.

    Concepts are derived from `hypotheses.csv`, so a change to that file changes what the
    run means even when the code and the query parameters are byte-identical.
    """

    resolved = (root or repository_root()) / "registries"
    hashes: dict[str, str] = {}
    for path in sorted(resolved.glob("*.csv")):
        try:
            hashes[f"registries/{path.name}"] = sha256_bytes(path.read_bytes())
        except OSError:
            continue
    return hashes


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
    run_id: str | None = None,
    journal: ResearchComputationJournal | None = None,
    preregistration_ref: str = NOT_PREREGISTERED,
    authority: AuthorityLevel = AuthorityLevel.A3_VERIFIED_EVIDENCE_COMPUTATION,
    explicit_human_authorisation: bool = False,
) -> KernelHarvestReport:
    """Harvest evidence for every proposition, tagging each record with its proposition.

    One connector failing on one proposition must not sink the sweep: a partial corpus
    with the gaps named is usable, and an aborted sweep is not.

    When a `store` is given the sweep also seals a :class:`RunManifest`, because a record
    in the store with no run describing how it was obtained is not evidence of anything.
    The manifest is sealed twice: once before the first request, so a run interrupted
    half-way still leaves a run record rather than orphan rows, and once on completion
    carrying the record counts, per-proposition corpus hashes and the completion time.

    `preregistration_ref` defaults to `NOT_PREREGISTERED` and never to the frozen
    specification id. Rule EXC2 of the frozen record makes this corpus permanently
    exploratory, and binding a run to a preregistration is a PROTECTED_TYPE mutation
    requiring explicit human authorisation - so the parameter is exposed and not
    exercised. An A3 pipeline computation cannot promote its own run to confirmatory.
    """

    connector_list = list(connectors)
    resolved_run_id = run_id or f"KH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    proposition_ids = [item.proposition_id for item in queries]
    query_parameters = {
        "harvest.max_records_per_proposition": str(max_records_per_proposition),
        "harvest.query_id_prefix": "KH-<proposition_id>",
        "harvest.concept_derivation": "registry domain + primary_outcome_construct",
        "harvest.cohort_lexicon_terms": str(len(list(cohort_lexicon))),
        "harvest.source_ids": ",".join(
            sorted(connector.source_name for connector in connector_list)
        ),
        "harvest.server_side_state": _SERVER_STATE_LIMIT,
    }
    concept_hashes = {
        f"concept:{item.proposition_id}": canonical_json_hash(
            {"concept": item.concept, "max_records": max_records_per_proposition}
        )
        for item in queries
    }

    def _seal(report: KernelHarvestReport | None) -> RunManifest:
        """Build and persist this run's manifest at its current state of completion.

        Called with `None` before the first request and with the report afterwards, so an
        aborted run is still described - as a STARTED run with no counts, which is honest,
        rather than as no run at all.
        """

        corpus_hashes = dict(concept_hashes)
        environment_extra = dict(query_parameters)
        if report is None:
            environment_extra["harvest.status"] = "STARTED"
        else:
            environment_extra["harvest.status"] = "COMPLETED"
            environment_extra["harvest.records_total"] = str(len(report.evidence))
            environment_extra["harvest.propositions_attempted"] = str(report.attempted)
            environment_extra["harvest.propositions_failed"] = str(len(report.failures))
            for key, value in sorted(report.per_proposition.items()):
                environment_extra[f"harvest.records.{key}"] = str(value)
            for key, value in sorted(report.failures.items()):
                environment_extra[f"harvest.failure.{key}"] = value
            corpus_hashes["evidence_ids"] = canonical_json_hash(
                sorted(record.evidence_id for record in report.evidence)
            )
            for item in queries:
                ids = sorted(
                    record.evidence_id
                    for record in report.evidence
                    if item.proposition_id in record.proposition_ids
                )
                corpus_hashes[f"records:{item.proposition_id}"] = canonical_json_hash(ids)

        manifest = build_run_manifest(
            run_id=resolved_run_id,
            objective="Kernel corpus harvest: one search per registry proposition",
            proposition_ids=proposition_ids,
            connectors=connector_list,
            corpus_hashes=corpus_hashes,
            registry_hashes=_registry_hashes(),
            preregistration_ref=preregistration_ref,
        )
        manifest = manifest.model_copy(
            update={
                "environment": {**manifest.environment, **environment_extra},
                "completed_at": datetime.now(timezone.utc) if report is not None else None,
            }
        )
        if store is not None:
            store.save_run(
                manifest,
                authority=authority,
                explicit_human_authorisation=explicit_human_authorisation,
            )
        if journal is not None:
            journal.append("RUN_MANIFEST_SEALED", manifest.model_dump(mode="json"))
        return manifest

    if store is not None or journal is not None:
        _seal(None)
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

    report = KernelHarvestReport(
        per_proposition=per_proposition,
        failures=failures,
        evidence=list(collected.values()),
        run_id=resolved_run_id,
    )
    if store is not None or journal is not None:
        _seal(report)
    return report


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
