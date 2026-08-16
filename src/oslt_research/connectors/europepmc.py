from __future__ import annotations

import json
from typing import Any

import httpx

from oslt_research.evidence.provenance import sha256_text

from .base import HarvestQuery, RawRecord, SourceConnector


#: DS035 in the source register, as the class docstring already states. Declared as a
#: module constant so the connector inventory can see it.
SOURCE_ID = "DS035"


class EuropePmcConnector(SourceConnector):
    """Europe PMC search. DS035 in the source register, priority P0.

    The widest open biomedical index available without a licence, and it carries abstract
    text inline rather than requiring a second lookup. That matters here: the corpus
    assembled from other sources had a median content length of 113 characters, which
    starved lane coding until abstracts were backfilled.

    Paged with cursorMark rather than an offset. Deep offset paging silently caps or
    duplicates on this API, and a corpus with unnoticed duplicates would inflate apparent
    independence exactly where dependency collapse is supposed to prevent it.

    Requires no API key.
    """

    source_name = "EuropePMC"
    connector_version = "1"
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    #: Europe PMC accepts up to 1000 per page.
    MAX_PAGE_SIZE = 1000

    def __init__(self, *, client: httpx.AsyncClient | None = None, email: str | None = None):
        self._client = client
        self.email = email

    def _params(self, query: HarvestQuery, cursor: str, page_size: int) -> dict[str, Any]:
        parts = [query.concept]
        if query.from_date:
            parts.append(f'FIRST_PDATE:[{query.from_date} TO {query.to_date or "3000-01-01"}]')
        elif query.to_date:
            parts.append(f'FIRST_PDATE:[1800-01-01 TO {query.to_date}]')
        for key, value in query.extra_filters.items():
            parts.append(f"{key}:{value}")

        params: dict[str, Any] = {
            "query": " AND ".join(parts),
            "format": "json",
            "resultType": "core",
            "pageSize": page_size,
            "cursorMark": cursor,
        }
        if self.email:
            params["email"] = self.email
        return params

    @staticmethod
    def _record(item: dict[str, Any], raw_hash: str) -> RawRecord:
        identifiers: dict[str, str] = {}
        for key, field in (("pmid", "pmid"), ("pmcid", "pmcid"), ("doi", "doi")):
            value = str(item.get(field) or "").strip()
            if value:
                identifiers[key] = value
        record_id = str(item.get("id") or identifiers.get("doi") or identifiers.get("pmid") or "")

        authors = [
            part.strip()
            for part in str(item.get("authorString") or "").split(",")
            if part.strip()
        ]

        source = str(item.get("source") or "MED")
        return RawRecord(
            source_name=EuropePmcConnector.source_name,
            source_record_id=f"{source}:{record_id}",
            title=str(item.get("title") or "").strip(),
            content=str(item.get("abstractText") or "").strip(),
            source_uri=(
                f"https://europepmc.org/article/{source}/{record_id}" if record_id else
                "https://europepmc.org/"
            ),
            published_at=str(item.get("firstPublicationDate") or item.get("pubYear") or "") or None,
            identifiers=identifiers,
            authors=authors,
            metadata={
                "journal": str((item.get("journalInfo") or {}).get("journal", {}).get("title") or ""),
                "pub_type": str(item.get("pubTypeList") or ""),
                "cited_by_count": item.get("citedByCount"),
                "is_open_access": str(item.get("isOpenAccess") or ""),
                # Europe PMC flags these directly, which is a cheaper retraction signal
                # than joining against Crossref - though it does not replace that check.
                "has_retraction_notice": str(item.get("hasSuppl") or ""),
                "connector_version": EuropePmcConnector.connector_version,
                "source_database": source,
            },
            raw_response_hash=raw_hash,
        )

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        client = self._client or httpx.AsyncClient(timeout=60.0)
        records: list[RawRecord] = []
        seen: set[str] = set()
        cursor = "*"
        try:
            while len(records) < query.max_records:
                page_size = min(self.MAX_PAGE_SIZE, query.max_records - len(records))
                response = await client.get(
                    self.base_url,
                    params=self._params(query, cursor, page_size),
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
                raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))

                items = (payload.get("resultList") or {}).get("result") or []
                if not items:
                    break
                for item in items:
                    record = self._record(item, raw_hash)
                    if record.source_record_id in seen:
                        continue
                    seen.add(record.source_record_id)
                    records.append(record)

                next_cursor = payload.get("nextCursorMark")
                # A cursor that does not advance means the server has no more pages;
                # continuing would loop on the same results forever.
                if not next_cursor or next_cursor == cursor:
                    break
                cursor = next_cursor
            return records[: query.max_records]
        finally:
            if self._client is None:
                await client.aclose()
