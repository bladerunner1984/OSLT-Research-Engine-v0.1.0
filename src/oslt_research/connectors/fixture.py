from __future__ import annotations

from oslt_research.evidence.provenance import canonical_json_hash

from .base import HarvestQuery, RawRecord, SourceConnector


class FixtureConnector(SourceConnector):
    source_name = "Fixture"
    connector_version = "1"

    def __init__(self, records: list[dict[str, object]]):
        self.records = records

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        output: list[RawRecord] = []
        for index, record in enumerate(self.records[: query.max_records], start=1):
            payload = dict(record)
            title = str(payload.get("title") or f"Fixture record {index}")
            output.append(
                RawRecord(
                    source_name="Fixture",
                    source_record_id=str(payload.get("id") or index),
                    title=title,
                    content=str(payload.get("content") or title),
                    source_uri=str(payload.get("uri") or f"fixture://{index}"),
                    published_at=str(payload["published_at"]) if payload.get("published_at") else None,
                    identifiers={
                        str(key): str(value)
                        for key, value in dict(payload.get("identifiers") or {}).items()
                    },
                    authors=[str(value) for value in list(payload.get("authors") or [])],
                    metadata=dict(payload.get("metadata") or {}),
                    raw_response_hash=canonical_json_hash(payload),
                )
            )
        return output
