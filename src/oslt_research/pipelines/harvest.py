from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from oslt_research.connectors.base import HarvestQuery, RawRecord, SourceConnector
from oslt_research.domain.enums import AccessClass, EpistemicStatus, EvidenceLane, SourceStatus
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.lane_coding import apply_lane_assignment
from oslt_research.evidence.provenance import admit_evidence, sha256_text
from oslt_research.persistence.sqlite import SQLiteStore


SOURCE_IDS = {
    "OpenAlex": "DS033",
    "Crossref": "DS034",
    "PubMed": "DS036",
    "EuropePMC": "DS035",
    "OpenAIRE": "DS041",
    "ClinicalTrials.gov": "DS037",
    "Fixture": "FIXTURE",
}


def normalise_doi(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    return value


def dependency_family_for(record: RawRecord) -> str:
    doi = record.identifiers.get("doi") or record.identifiers.get("DOI")
    if doi:
        return f"doi:{normalise_doi(doi)}"
    pmid = record.identifiers.get("pmid")
    if pmid:
        return f"pmid:{pmid}"
    title_key = re.sub(r"[^a-z0-9]+", "-", record.title.casefold()).strip("-")[:100]
    first_author = record.authors[0].casefold() if record.authors else "unknown"
    year = (record.published_at or "unknown")[:4]
    return f"heuristic:{title_key}:{first_author}:{year}"


def evidence_id_for(record: RawRecord) -> str:
    digest = sha256_text(f"{record.source_name}|{record.source_record_id}")[:20]
    return f"EV-{digest.upper()}"


def raw_record_to_evidence(record: RawRecord, query: HarvestQuery) -> EvidenceObject:
    content_hash = sha256_text(record.content)
    evidence = EvidenceObject(
        evidence_id=evidence_id_for(record),
        proposition_ids=query.proposition_ids,
        # Left UNCLASSIFIED here and set below: the classifier reads title+content, so
        # it needs the assembled record rather than the raw one.
        lane=EvidenceLane.UNCLASSIFIED,
        source_status=SourceStatus.VERIFIED,
        epistemic_status=EpistemicStatus.OBSERVATION,
        title=record.title,
        content=record.content,
        provenance=ProvenanceRecord(
            source_id=SOURCE_IDS.get(record.source_name, record.source_name),
            source_uri=record.source_uri,
            retrieved_at=record.retrieved_at,
            published_at=record.published_at,
            source_version=record.metadata.get("data_version")
            or record.metadata.get("source_version"),
            retrieval_query=query.concept,
            field_or_document_locator=record.source_record_id,
            checksum_sha256=record.raw_response_hash,
            access_class=AccessClass.OPEN,
            licence_or_approval="PUBLIC_API_TERMS_APPLY",
            transformation_ids=["RAW_RECORD_TO_EVIDENCE_V1"],
            codebook_or_schema_ref=(
                f"connector:{record.source_name}:v"
                f"{record.metadata.get('connector_version', 'UNKNOWN')}"
            ),
        ),
        dependency_family=dependency_family_for(record),
        metadata={
            **record.metadata,
            "identifiers": record.identifiers,
            "authors": record.authors,
            "content_sha256": content_hash,
            "query_id": query.query_id,
            "connector_source": record.source_name,
        },
    )
    # Lane-code every harvested record at the point of construction. Without this the
    # corpus persists lane-blind, and a lane-blind corpus cannot support triangulation
    # at all - the lanes are how evidence is partitioned before it is compared.
    return admit_evidence(apply_lane_assignment(evidence))


@dataclass(frozen=True)
class HarvestResult:
    query: HarvestQuery
    evidence: list[EvidenceObject]

    @property
    def admitted(self) -> list[EvidenceObject]:
        return [item for item in self.evidence if item.admitted]

    @property
    def rejected(self) -> list[EvidenceObject]:
        return [item for item in self.evidence if not item.admitted]


async def execute_harvest(
    connector: SourceConnector,
    query: HarvestQuery,
    *,
    store: SQLiteStore | None = None,
) -> HarvestResult:
    harvested = await connector.harvest(query)
    raw = [
        record.model_copy(
            update={
                "metadata": {
                    **record.metadata,
                    "connector_version": connector.connector_version,
                }
            }
        )
        for record in harvested
    ]
    evidence = [raw_record_to_evidence(record, query) for record in raw]
    if store:
        store.initialise()
        store.save_evidence_many(evidence)
    return HarvestResult(query=query, evidence=evidence)


def unique_dependency_families(evidence: Iterable[EvidenceObject]) -> set[str]:
    return {item.dependency_family for item in evidence}
