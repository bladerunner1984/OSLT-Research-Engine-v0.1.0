from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Iterable

import httpx

from oslt_research.ontology.entities import InstitutionalEntity, normalise_name


#: Companies House allows 600 requests per five minutes. Staying under it by pacing is
#: better than being throttled mid-run and leaving a graph half-resolved.
DEFAULT_MIN_INTERVAL_SECONDS = 0.55

#: Company statuses whose match we accept. A dissolved company with the right name is
#: usually the wrong entity for a live contract or grant, and accepting one silently
#: swaps a real body for a defunct namesake.
ACCEPTABLE_STATUSES = frozenset({"active", "open"})


@dataclass(frozen=True)
class ResolutionAttempt:
    entity_id: str
    query: str
    resolved: bool
    company_number: str | None = None
    matched_title: str | None = None
    candidates_considered: int = 0
    reason: str = ""


@dataclass(frozen=True)
class ResolutionReport:
    attempts: list[ResolutionAttempt] = field(default_factory=list)
    entities: list[InstitutionalEntity] = field(default_factory=list)

    @property
    def resolved(self) -> int:
        return sum(1 for item in self.attempts if item.resolved)

    def reasons(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for item in self.attempts:
            if not item.resolved:
                tally[item.reason] = tally.get(item.reason, 0) + 1
        return dict(sorted(tally.items()))

    def summary(self) -> dict[str, object]:
        return {
            "attempted": len(self.attempts),
            "resolved": self.resolved,
            "unresolved": len(self.attempts) - self.resolved,
            "unresolved_reasons": self.reasons(),
        }


class CompaniesHouseResolver:
    """Attach Companies House numbers to entities that have no strong identifier.

    The point of this is to replace merges made on a naming coincidence with merges made
    on a registry identifier. That only works if the matching is strict. A fuzzy match
    would recreate the same problem with an identifier bolted on top, and would be worse
    than the original because the result would look authoritative.

    So a match is accepted only when the normalised name is EXACTLY equal and exactly one
    acceptable-status candidate matches. Two same-named active companies, a near miss, or
    a dissolved-only match all leave the entity unresolved with a recorded reason. An
    unresolved entity is a visible gap; a wrong identifier is an invisible error.
    """

    source_name = "CompaniesHouse"
    connector_version = "1"
    base_url = "https://api.company-information.service.gov.uk"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 45.0,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
    ):
        self.api_key = api_key or os.getenv("OSLT_COMPANIES_HOUSE_API_KEY", "")
        if not self.api_key and client is None:
            raise ValueError(
                "Companies House API key required; set OSLT_COMPANIES_HOUSE_API_KEY"
            )
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _search(self, query: str, limit: int) -> list[dict]:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._throttle()
            response = client.get(
                f"{self.base_url}/search/companies",
                params={"q": query, "items_per_page": limit},
                auth=(self.api_key, ""),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json().get("items") or []
        finally:
            if self._client is None:
                client.close()

    def resolve_entity(self, entity: InstitutionalEntity, *, limit: int = 20) -> ResolutionAttempt:
        if entity.strong_identifiers():
            return ResolutionAttempt(
                entity.entity_id, entity.canonical_name, False,
                reason="ALREADY_HAS_STRONG_IDENTIFIER",
            )

        query = entity.canonical_name.strip()
        if not query:
            return ResolutionAttempt(entity.entity_id, query, False, reason="EMPTY_NAME")

        try:
            candidates = self._search(query, limit)
        except httpx.HTTPError as exc:
            return ResolutionAttempt(
                entity.entity_id, query, False, reason=f"SEARCH_FAILED_{type(exc).__name__}"
            )

        target = normalise_name(query)
        exact = [
            item
            for item in candidates
            if normalise_name(str(item.get("title") or "")) == target
            and str(item.get("company_status") or "").lower() in ACCEPTABLE_STATUSES
        ]

        if not exact:
            near = any(
                normalise_name(str(item.get("title") or "")) == target for item in candidates
            )
            reason = "ONLY_DISSOLVED_NAME_MATCH" if near else "NO_EXACT_NAME_MATCH"
            return ResolutionAttempt(
                entity.entity_id, query, False,
                candidates_considered=len(candidates), reason=reason,
            )

        if len(exact) > 1:
            # Two live companies share this normalised name. Picking one would be a guess
            # dressed as an identifier.
            return ResolutionAttempt(
                entity.entity_id, query, False,
                candidates_considered=len(candidates),
                reason=f"AMBIGUOUS_{len(exact)}_ACTIVE_MATCHES",
            )

        match = exact[0]
        return ResolutionAttempt(
            entity_id=entity.entity_id,
            query=query,
            resolved=True,
            company_number=str(match.get("company_number") or "").upper(),
            matched_title=str(match.get("title") or ""),
            candidates_considered=len(candidates),
            reason="EXACT_UNIQUE_ACTIVE_MATCH",
        )

    def resolve(self, entities: Iterable[InstitutionalEntity]) -> ResolutionReport:
        attempts: list[ResolutionAttempt] = []
        updated: list[InstitutionalEntity] = []

        for entity in entities:
            attempt = self.resolve_entity(entity)
            attempts.append(attempt)
            if attempt.resolved and attempt.company_number:
                identifiers = {
                    **entity.identifiers,
                    "companies_house": attempt.company_number,
                }
                metadata = {
                    **entity.metadata,
                    "companies_house_matched_title": attempt.matched_title or "",
                    "companies_house_match_basis": attempt.reason,
                }
                updated.append(
                    entity.model_copy(update={"identifiers": identifiers, "metadata": metadata})
                )
            else:
                updated.append(entity)

        return ResolutionReport(attempts=attempts, entities=updated)
