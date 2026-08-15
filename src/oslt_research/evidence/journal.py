from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .provenance import sha256_text


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class JournalEntry:
    sequence: int
    timestamp: str
    event_type: str
    payload: dict[str, Any]
    previous_hash: str
    entry_hash: str


class ResearchComputationJournal:
    """Append-only JSONL journal with a cryptographic hash chain."""

    GENESIS_HASH = "0" * 64

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _entry_hash(
        sequence: int,
        timestamp: str,
        event_type: str,
        payload: dict[str, Any],
        previous_hash: str,
    ) -> str:
        canonical = json.dumps(
            {
                "sequence": sequence,
                "timestamp": timestamp,
                "event_type": event_type,
                "payload": payload,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256_text(canonical)

    def entries(self) -> list[JournalEntry]:
        if not self.path.exists():
            return []
        result: list[JournalEntry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            result.append(JournalEntry(**json.loads(line)))
        return result

    def append(self, event_type: str, payload: dict[str, Any]) -> JournalEntry:
        existing = self.entries()
        sequence = len(existing) + 1
        previous_hash = existing[-1].entry_hash if existing else self.GENESIS_HASH
        timestamp = utc_now_iso()
        entry_hash = self._entry_hash(sequence, timestamp, event_type, payload, previous_hash)
        entry = JournalEntry(
            sequence=sequence,
            timestamp=timestamp,
            event_type=event_type,
            payload=payload,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
        )
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(asdict(entry), sort_keys=True, default=str) + "\n")
        return entry

    @classmethod
    def verify_entries(cls, entries: Iterable[JournalEntry]) -> bool:
        previous_hash = cls.GENESIS_HASH
        expected_sequence = 1
        for entry in entries:
            if entry.sequence != expected_sequence:
                return False
            if entry.previous_hash != previous_hash:
                return False
            expected_hash = cls._entry_hash(
                entry.sequence,
                entry.timestamp,
                entry.event_type,
                entry.payload,
                entry.previous_hash,
            )
            if entry.entry_hash != expected_hash:
                return False
            previous_hash = entry.entry_hash
            expected_sequence += 1
        return True

    def verify(self) -> bool:
        return self.verify_entries(self.entries())
