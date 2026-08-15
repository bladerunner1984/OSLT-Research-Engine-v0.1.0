from __future__ import annotations

import json
from typing import Any

import httpx

from oslt_research.evidence.provenance import sha256_text

from .base import HarvestQuery, RawRecord, SourceConnector


class ClinicalTrialsConnector(SourceConnector):
    source_name = "ClinicalTrials.gov"
    connector_version = "1"
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    version_url = "https://clinicaltrials.gov/api/v2/version"

    def __init__(self, *, client: httpx.AsyncClient | None = None):
        self._client = client

    @staticmethod
    def _record(study: dict[str, Any], raw_hash: str, data_version: str | None) -> RawRecord:
        protocol = study.get("protocolSection") or {}
        identification = protocol.get("identificationModule") or {}
        status = protocol.get("statusModule") or {}
        description = protocol.get("descriptionModule") or {}
        design = protocol.get("designModule") or {}
        conditions = protocol.get("conditionsModule") or {}
        sponsor = protocol.get("sponsorCollaboratorsModule") or {}
        nct_id = str(identification.get("nctId") or "UNKNOWN_NCT")
        title = (
            identification.get("briefTitle")
            or identification.get("officialTitle")
            or f"ClinicalTrials.gov {nct_id}"
        )
        content = "\n\n".join(
            part
            for part in [
                title,
                description.get("briefSummary"),
                description.get("detailedDescription"),
            ]
            if part
        )
        authors = []
        lead_sponsor = sponsor.get("leadSponsor") or {}
        if lead_sponsor.get("name"):
            authors.append(str(lead_sponsor["name"]))
        posted = status.get("studyFirstPostDateStruct") or {}
        results_section = study.get("resultsSection")
        return RawRecord(
            source_name="ClinicalTrials.gov",
            source_record_id=nct_id,
            title=title,
            content=content,
            source_uri=f"https://clinicaltrials.gov/study/{nct_id}",
            published_at=posted.get("date"),
            identifiers={"nct": nct_id},
            authors=authors,
            metadata={
                "record_kind": "registration",
                "published": False,
                "has_results_posted": bool(results_section),
                "overall_status": status.get("overallStatus"),
                "study_type": design.get("studyType"),
                "phases": design.get("phases", []),
                "conditions": conditions.get("conditions", []),
                "keywords": conditions.get("keywords", []),
                "enrollment_info": design.get("enrollmentInfo"),
                "data_version": data_version,
            },
            raw_response_hash=raw_hash,
        )

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30)
        try:
            version_response = await client.get(self.version_url)
            version_response.raise_for_status()
            version_payload = version_response.json()
            data_version = version_payload.get("dataTimestamp") or version_payload.get("version")

            records: list[RawRecord] = []
            page_token: str | None = None
            while len(records) < query.max_records:
                page_size = min(1000, query.max_records - len(records))
                params: dict[str, str | int] = {
                    "query.term": query.concept,
                    "pageSize": page_size,
                    "format": "json",
                }
                if page_token:
                    params["pageToken"] = page_token
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
                raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
                studies = payload.get("studies") or []
                records.extend(self._record(study, raw_hash, data_version) for study in studies)
                page_token = payload.get("nextPageToken")
                if len(studies) < page_size or not page_token:
                    break
            return records[: query.max_records]
        finally:
            if own_client:
                await client.aclose()
