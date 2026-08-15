from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

import httpx

from oslt_research.domain.enums import (
    AccessClass,
    EpistemicStatus,
    EvidenceLane,
    SourceStatus,
)
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.provenance import admit_evidence, sha256_text
from oslt_research.pipelines.harvest import normalise_doi


#: DS043 in the source register. Crossref carries the Retraction Watch data as typed
#: update relationships, so a retraction notice points at the work it retracts.
SOURCE_ID = "DS043"
DEPENDENCY_FAMILY = "register:crossref-retraction-watch"

#: Update types that invalidate or qualify a prior work. Distinguished because they are
#: not equivalent: a retraction withdraws a finding, a corrigendum amends one.
INVALIDATING_TYPES = frozenset({"retraction", "withdrawal", "removal"})
QUALIFYING_TYPES = frozenset({"correction", "corrigendum", "erratum", "expression_of_concern"})


@dataclass(frozen=True)
class RetractionRecord:
    notice_doi: str
    retracted_doi: str
    update_type: str
    notice_title: str = ""
    issued: str | None = None

    @property
    def invalidates(self) -> bool:
        return self.update_type.lower().replace(" ", "_") in INVALIDATING_TYPES


@dataclass(frozen=True)
class RetractionSweep:
    records: list[RetractionRecord] = field(default_factory=list)
    evidence: list[EvidenceObject] = field(default_factory=list)
    notices_seen: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)

    def by_retracted_doi(self) -> dict[str, RetractionRecord]:
        return {item.retracted_doi: item for item in self.records}


class RetractionConnector:
    """Retraction and correction notices from Crossref.

    Serves the CORRECTION_RETRACTION lane, which the constitution makes mandatory and
    which the automated classifier could barely populate from abstracts. More usefully, it
    can be pointed at an existing corpus to ask whether anything already admitted as
    evidence has since been withdrawn - a check no amount of careful reading of the
    original abstracts would ever catch, because the retraction is a different document.

    Requires no API key.
    """

    source_name = "CrossrefRetractions"
    connector_version = "1"
    base_url = "https://api.crossref.org/works"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        mailto: str | None = None,
        timeout: float = 60.0,
    ):
        self._client = client
        self.mailto = mailto
        self.timeout = timeout

    def _fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        if self.mailto:
            params = {**params, "mailto": self.mailto}
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        finally:
            if self._client is None:
                client.close()

    @staticmethod
    def _notice_to_records(item: dict[str, Any]) -> list[RetractionRecord]:
        notice_doi = normalise_doi(str(item.get("DOI") or ""))
        titles = item.get("title") or []
        title = str(titles[0]) if titles else ""
        issued = None
        parts = (item.get("issued") or {}).get("date-parts") or []
        if parts and parts[0]:
            issued = "-".join(str(value).zfill(2) for value in parts[0])

        records: list[RetractionRecord] = []
        for update in item.get("update-to") or []:
            target = normalise_doi(str(update.get("DOI") or ""))
            if not target or target == notice_doi:
                # A notice pointing at itself carries no information about another work.
                continue
            records.append(
                RetractionRecord(
                    notice_doi=notice_doi,
                    retracted_doi=target,
                    update_type=str(update.get("type") or "unknown"),
                    notice_title=title,
                    issued=issued,
                )
            )
        return records

    def _to_evidence(self, record: RetractionRecord, raw_hash: str) -> EvidenceObject:
        content = (
            f"{record.update_type} notice for {record.retracted_doi}. {record.notice_title}"
        )
        return admit_evidence(
            EvidenceObject(
                evidence_id=f"EV-RETRACT-{sha256_text(record.notice_doi)[:16].upper()}",
                lane=EvidenceLane.CORRECTION_RETRACTION,
                source_status=SourceStatus.VERIFIED,
                epistemic_status=EpistemicStatus.OBSERVATION,
                title=record.notice_title or f"{record.update_type} notice",
                content=content,
                provenance=ProvenanceRecord(
                    source_id=SOURCE_ID,
                    source_uri=f"https://doi.org/{record.notice_doi}",
                    published_at=record.issued,
                    field_or_document_locator=record.notice_doi,
                    checksum_sha256=raw_hash,
                    access_class=AccessClass.OPEN,
                    licence_or_approval="CROSSREF_OPEN_METADATA",
                    transformation_ids=["CROSSREF_UPDATE_TO_RETRACTION_EVIDENCE_V1"],
                ),
                dependency_family=DEPENDENCY_FAMILY,
                metadata={
                    "retracted_doi": record.retracted_doi,
                    "update_type": record.update_type,
                    "invalidates": record.invalidates,
                    "content_sha256": sha256_text(content),
                },
            )
        )

    def sweep(
        self,
        *,
        concept: str | None = None,
        update_type: str = "retraction",
        rows: int = 100,
    ) -> RetractionSweep:
        params: dict[str, Any] = {
            "filter": f"update-type:{update_type}",
            "rows": min(rows, 1000),
            "select": "DOI,title,update-to,issued",
        }
        if concept:
            params["query.bibliographic"] = concept

        payload = self._fetch(params)
        raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
        items = (payload.get("message") or {}).get("items") or []

        records: list[RetractionRecord] = []
        skips: dict[str, int] = {}
        for item in items:
            produced = self._notice_to_records(item)
            if not produced:
                skips["NO_RESOLVABLE_TARGET"] = skips.get("NO_RESOLVABLE_TARGET", 0) + 1
            records.extend(produced)

        return RetractionSweep(
            records=records,
            evidence=[self._to_evidence(item, raw_hash) for item in records],
            notices_seen=len(items),
            skip_reasons=skips,
        )

    def check_corpus(
        self, evidence: Iterable[EvidenceObject], *, sweep: RetractionSweep
    ) -> list[tuple[EvidenceObject, RetractionRecord]]:
        """Find records in an existing corpus that have since been retracted or corrected.

        The corpus was admitted on the strength of the original papers. A retraction is a
        separate document published later, so nothing about re-reading the originals would
        surface it. This is the only way the check happens.
        """

        index = sweep.by_retracted_doi()
        hits: list[tuple[EvidenceObject, RetractionRecord]] = []
        for item in evidence:
            identifiers = item.metadata.get("identifiers") or {}
            doi = normalise_doi(str(identifiers.get("doi") or identifiers.get("DOI") or ""))
            if not doi:
                family = item.dependency_family
                if family.startswith("doi:"):
                    doi = normalise_doi(family[4:])
            if doi and doi in index:
                hits.append((item, index[doi]))
        return hits


def apply_retraction_status(
    evidence: Iterable[EvidenceObject],
    *,
    sweep: RetractionSweep,
    connector: "RetractionConnector | None" = None,
) -> tuple[list[EvidenceObject], dict[str, int]]:
    """Stamp retraction status onto a corpus and re-run admission.

    Records whose source work has been retracted are flagged and lose admission. Records
    carrying a correction or corrigendum are flagged too, but keep it: a corrigendum
    amends a finding rather than withdrawing it, and treating the two alike would either
    discard usable evidence or retain withdrawn evidence.

    The flag is written to metadata rather than applied silently, so a later reader can
    see why a record was refused and check it.
    """

    checker = connector or RetractionConnector()
    index = sweep.by_retracted_doi()
    matched = {
        item.evidence_id: record
        for item, record in checker.check_corpus(evidence, sweep=sweep)
    }

    updated: list[EvidenceObject] = []
    tally: dict[str, int] = {"retracted": 0, "corrected": 0, "unaffected": 0}
    for item in evidence:
        record = matched.get(item.evidence_id)
        if record is None:
            tally["unaffected"] += 1
            updated.append(item)
            continue

        metadata = {
            **item.metadata,
            "source_work_retracted": record.invalidates,
            "retraction_notice_doi": record.notice_doi,
            "retraction_update_type": record.update_type,
        }
        stamped = admit_evidence(
            item.model_copy(
                update={
                    "metadata": metadata,
                    "lane": EvidenceLane.CORRECTION_RETRACTION,
                }
            )
        )
        tally["retracted" if record.invalidates else "corrected"] += 1
        updated.append(stamped)

    return updated, tally
