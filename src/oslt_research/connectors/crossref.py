from __future__ import annotations

import json
from typing import Any

import httpx

from oslt_research.evidence.provenance import sha256_text

from .base import HarvestQuery, RawRecord, SourceConnector


class CrossrefConnector(SourceConnector):
    source_name = "Crossref"
    connector_version = "2"
    base_url = "https://api.crossref.org/works"

    def __init__(self, *, mailto: str | None = None, client: httpx.AsyncClient | None = None):
        self.mailto = mailto
        self._client = client

    @staticmethod
    def _date(item: dict[str, Any]) -> str | None:
        for key in ("published-print", "published-online", "issued", "created"):
            parts = ((item.get(key) or {}).get("date-parts") or [])
            if parts and parts[0]:
                values = parts[0]
                return "-".join(str(value).zfill(2) for value in values)
        return None

    @staticmethod
    def _record(item: dict[str, Any], raw_hash: str) -> RawRecord:
        title_values = item.get("title") or []
        title = title_values[0] if title_values else "Untitled Crossref work"
        abstract = item.get("abstract") or ""
        authors = [
            " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
            for author in item.get("author", [])
        ]
        doi = item.get("DOI")
        uri = item.get("URL") or (f"https://doi.org/{doi}" if doi else "https://crossref.org")
        identifiers = {"doi": doi} if doi else {}
        return RawRecord(
            source_name="Crossref",
            source_record_id=doi or str(item.get("URL") or title),
            title=title,
            content="\n\n".join(part for part in [title, abstract] if part),
            source_uri=uri,
            published_at=CrossrefConnector._date(item),
            identifiers=identifiers,
            authors=[name for name in authors if name],
            metadata={
                "type": item.get("type"),
                "publisher": item.get("publisher"),
                "container_title": item.get("container-title", []),
                "reference_count": item.get("references-count", item.get("reference-count")),
                "is_referenced_by_count": item.get("is-referenced-by-count"),
                "funder": item.get("funder", []),
                "relation": item.get("relation", {}),
                "update_to": item.get("update-to", []),
                "license": item.get("license", []),
            },
            raw_response_hash=raw_hash,
        )

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        own_client = self._client is None
        headers = {"User-Agent": f"OSLT/0.1 ({self.mailto or 'no-mailto'})"}
        client = self._client or httpx.AsyncClient(timeout=30, headers=headers)
        try:
            records: list[RawRecord] = []
            cursor = "*"
            while len(records) < query.max_records:
                rows = min(1000, query.max_records - len(records))
                params: dict[str, str | int] = {
                    "query.bibliographic": query.concept,
                    "rows": rows,
                    "cursor": cursor,
                    "select": (
                        "DOI,title,abstract,author,URL,published-print,published-online,issued,created,"
                        "type,publisher,container-title,references-count,is-referenced-by-count,funder,"
                        "relation,update-to,license"
                    ),
                }
                if self.mailto:
                    params["mailto"] = self.mailto
                filters: list[str] = []
                if query.from_date:
                    filters.append(f"from-pub-date:{query.from_date}")
                if query.to_date:
                    filters.append(f"until-pub-date:{query.to_date}")
                if filters:
                    params["filter"] = ",".join(filters)
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
                message = payload.get("message") or {}
                raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
                items = message.get("items") or []
                records.extend(self._record(item, raw_hash) for item in items)
                if len(items) < rows:
                    break
                next_cursor = message.get("next-cursor")
                if not next_cursor or next_cursor == cursor:
                    break
                cursor = next_cursor
            return records[: query.max_records]
        finally:
            if own_client:
                await client.aclose()
