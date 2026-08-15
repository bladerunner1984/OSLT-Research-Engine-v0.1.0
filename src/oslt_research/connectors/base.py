from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HarvestQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    concept: str = Field(min_length=1)
    proposition_ids: list[str] = Field(default_factory=list)
    max_records: int = Field(default=100, ge=1, le=10_000)
    from_date: str | None = None
    to_date: str | None = None
    extra_filters: dict[str, str] = Field(default_factory=dict)


class RawRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str
    source_record_id: str
    title: str
    content: str
    source_uri: str
    published_at: str | None = None
    identifiers: dict[str, str] = Field(default_factory=dict)
    authors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: datetime = Field(default_factory=utc_now)
    raw_response_hash: str


class SourceConnector(ABC):
    source_name: str
    connector_version: str = "1"

    @abstractmethod
    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        raise NotImplementedError
