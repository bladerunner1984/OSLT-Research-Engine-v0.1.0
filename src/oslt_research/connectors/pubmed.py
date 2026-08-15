from __future__ import annotations

import json
from typing import Any

import httpx

from oslt_research.evidence.provenance import sha256_text

from .base import HarvestQuery, RawRecord, SourceConnector


class PubMedConnector(SourceConnector):
    source_name = "PubMed"
    connector_version = "2"
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, *, api_key: str | None = None, client: httpx.AsyncClient | None = None):
        self.api_key = api_key
        self._client = client

    @staticmethod
    def _records_from_payload(
        payload: dict[str, Any], ids: list[str], raw_hash: str
    ) -> list[RawRecord]:
        result: dict[str, Any] = payload.get("result") or {}
        records: list[RawRecord] = []
        for pmid in ids:
            item = result.get(pmid) or {}
            article_ids = {
                str(entry.get("idtype")): str(entry.get("value"))
                for entry in item.get("articleids", [])
                if entry.get("idtype") and entry.get("value")
            }
            article_ids["pmid"] = pmid
            authors = [author.get("name", "") for author in item.get("authors", [])]
            title = item.get("title") or f"PubMed {pmid}"
            records.append(
                RawRecord(
                    source_name="PubMed",
                    source_record_id=pmid,
                    title=title,
                    content=title,
                    source_uri=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    published_at=item.get("pubdate"),
                    identifiers=article_ids,
                    authors=[name for name in authors if name],
                    metadata={
                        "source": item.get("source"),
                        "pubtype": item.get("pubtype", []),
                        "fulljournalname": item.get("fulljournalname"),
                        "sortpubdate": item.get("sortpubdate"),
                    },
                    raw_response_hash=raw_hash,
                )
            )
        return records

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30)
        try:
            search_params: dict[str, str | int] = {
                "db": "pubmed",
                "term": query.concept,
                "retmode": "json",
                "retmax": min(query.max_records, 10_000),
                "sort": "relevance",
            }
            if query.from_date or query.to_date:
                start = query.from_date or "1800/01/01"
                end = query.to_date or "3000/12/31"
                search_params["mindate"] = start.replace("-", "/")
                search_params["maxdate"] = end.replace("-", "/")
                search_params["datetype"] = "pdat"
            if self.api_key:
                search_params["api_key"] = self.api_key

            search_response = await client.get(self.search_url, params=search_params)
            search_response.raise_for_status()
            ids = ((search_response.json().get("esearchresult") or {}).get("idlist") or [])
            if not ids:
                return []

            records: list[RawRecord] = []
            for offset in range(0, len(ids), 200):
                batch = ids[offset : offset + 200]
                summary_params: dict[str, str] = {
                    "db": "pubmed",
                    "id": ",".join(batch),
                    "retmode": "json",
                }
                if self.api_key:
                    summary_params["api_key"] = self.api_key
                if len(batch) > 100:
                    summary_response = await client.post(self.summary_url, data=summary_params)
                else:
                    summary_response = await client.get(self.summary_url, params=summary_params)
                summary_response.raise_for_status()
                payload = summary_response.json()
                raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
                records.extend(self._records_from_payload(payload, batch, raw_hash))
            return records[: query.max_records]
        finally:
            if own_client:
                await client.aclose()
