from __future__ import annotations

import json
from typing import Any

import httpx

from oslt_research.evidence.provenance import sha256_text

from .base import HarvestQuery, RawRecord, SourceConnector


class OpenAlexConnector(SourceConnector):
    source_name = "OpenAlex"
    connector_version = "2"
    base_url = "https://api.openalex.org/works"

    def __init__(
        self,
        *,
        mailto: str | None = None,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.mailto = mailto
        self.api_key = api_key
        self._client = client

    @staticmethod
    def _abstract_from_index(index: dict[str, list[int]] | None) -> str:
        if not index:
            return ""
        positions: list[tuple[int, str]] = []
        for word, indices in index.items():
            positions.extend((position, word) for position in indices)
        return " ".join(word for _, word in sorted(positions))

    @staticmethod
    def _record(item: dict[str, Any], raw_hash: str) -> RawRecord:
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in item.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        identifiers = {
            key: str(value)
            for key, value in (item.get("ids") or {}).items()
            if value is not None
        }
        title = item.get("display_name") or item.get("title") or "Untitled OpenAlex work"
        abstract = OpenAlexConnector._abstract_from_index(item.get("abstract_inverted_index"))
        content = "\n\n".join(part for part in [title, abstract] if part)
        return RawRecord(
            source_name="OpenAlex",
            source_record_id=str(item.get("id") or identifiers.get("openalex") or title),
            title=title,
            content=content,
            source_uri=str(item.get("id") or "https://openalex.org"),
            published_at=item.get("publication_date"),
            identifiers=identifiers,
            authors=authors,
            metadata={
                "type": item.get("type"),
                "cited_by_count": item.get("cited_by_count"),
                "is_retracted": item.get("is_retracted"),
                "primary_location": item.get("primary_location"),
                "topics": item.get("topics", []),
                "authorships": item.get("authorships", []),
                "grants": item.get("grants", []),
                "referenced_works": item.get("referenced_works", []),
            },
            raw_response_hash=raw_hash,
        )

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30)
        try:
            records: list[RawRecord] = []
            cursor: str | None = "*"
            while cursor and len(records) < query.max_records:
                page_size = min(200, query.max_records - len(records))
                params: dict[str, str | int] = {
                    "search": query.concept,
                    "per_page": page_size,
                    "cursor": cursor,
                }
                if self.mailto:
                    params["mailto"] = self.mailto
                if self.api_key:
                    params["api_key"] = self.api_key
                filters: list[str] = []
                if query.from_date:
                    filters.append(f"from_publication_date:{query.from_date}")
                if query.to_date:
                    filters.append(f"to_publication_date:{query.to_date}")
                filters.extend(f"{key}:{value}" for key, value in query.extra_filters.items())
                if filters:
                    params["filter"] = ",".join(filters)

                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
                raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
                page = [self._record(item, raw_hash) for item in payload.get("results", [])]
                records.extend(page)
                cursor = (payload.get("meta") or {}).get("next_cursor")
                if len(page) < page_size:
                    break
            return records[: query.max_records]
        finally:
            if own_client:
                await client.aclose()
