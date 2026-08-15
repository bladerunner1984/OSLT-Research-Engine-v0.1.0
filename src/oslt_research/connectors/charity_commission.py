from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Iterable

import httpx

from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    SystemDomain,
    normalise_name,
)

from .companies_house import ResolutionAttempt, ResolutionReport


#: reg_status on the Register of Charities. "R" is registered; "RM" is removed. A removed
#: charity sharing a name with a live one is a different body, and the register returns
#: both - searching "Mermaids" yields one R and one RM.
REGISTERED_STATUS = "R"


@dataclass(frozen=True)
class CharityTyping:
    """What resolving a charity number tells us beyond identity."""

    entity_id: str
    charity_number: str
    charity_name: str
    registered_on: str | None = None


class CharityCommissionResolver:
    """Attach charity numbers to entities, and type them as advocacy bodies.

    Does two jobs the Companies House resolver cannot. It identifies bodies that are not
    companies - which is most of the 109 names Companies House could not match - and it
    resolves SystemDomain.UNKNOWN, because a body on the Register of Charities is by
    definition a charitable one rather than commercial. That matters for MD10 and MD15,
    where an UNKNOWN domain is deliberately excluded from cross-system spread and so
    cannot contribute to a coupling verdict.

    Matching strictness is identical to the Companies House resolver, for the same reason:
    a fuzzy match would put an authoritative-looking identifier on a guess. Exactly one
    REGISTERED charity whose normalised name matches exactly, or the entity stays
    unresolved with a recorded reason.
    """

    source_name = "CharityCommission"
    connector_version = "1"
    base_url = "https://api.charitycommission.gov.uk/register/api"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 45.0,
        min_interval_seconds: float = 0.3,
    ):
        self.api_key = api_key or os.getenv("OSLT_CHARITY_COMMISSION_API_KEY", "")
        if not self.api_key and client is None:
            raise ValueError(
                "Charity Commission API key required; set OSLT_CHARITY_COMMISSION_API_KEY"
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

    def _search(self, name: str) -> list[dict]:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._throttle()
            response = client.get(
                f"{self.base_url}/searchCharityName/{name}",
                headers={
                    "Ocp-Apim-Subscription-Key": self.api_key,
                    "Accept": "application/json",
                },
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, list) else [payload]
        finally:
            if self._client is None:
                client.close()

    def resolve_entity(self, entity: InstitutionalEntity) -> ResolutionAttempt:
        if entity.strong_identifiers():
            return ResolutionAttempt(
                entity.entity_id, entity.canonical_name, False,
                reason="ALREADY_HAS_STRONG_IDENTIFIER",
            )

        query = entity.canonical_name.strip()
        if not query:
            return ResolutionAttempt(entity.entity_id, query, False, reason="EMPTY_NAME")

        try:
            candidates = self._search(query)
        except httpx.HTTPError as exc:
            return ResolutionAttempt(
                entity.entity_id, query, False, reason=f"SEARCH_FAILED_{type(exc).__name__}"
            )

        target = normalise_name(query)
        exact = [
            item
            for item in candidates
            if normalise_name(str(item.get("charity_name") or "")) == target
            and str(item.get("reg_status") or "").upper() == REGISTERED_STATUS
        ]

        if not exact:
            removed = any(
                normalise_name(str(item.get("charity_name") or "")) == target
                for item in candidates
            )
            return ResolutionAttempt(
                entity.entity_id, query, False,
                candidates_considered=len(candidates),
                reason="ONLY_REMOVED_NAME_MATCH" if removed else "NO_EXACT_NAME_MATCH",
            )

        # Group and subsidiary entries share a charity number under different suffixes;
        # collapsing on the number stops that looking like genuine ambiguity.
        numbers = {str(item.get("reg_charity_number") or "") for item in exact}
        if len(numbers) > 1:
            return ResolutionAttempt(
                entity.entity_id, query, False,
                candidates_considered=len(candidates),
                reason=f"AMBIGUOUS_{len(numbers)}_REGISTERED_MATCHES",
            )

        match = exact[0]
        return ResolutionAttempt(
            entity_id=entity.entity_id,
            query=query,
            resolved=True,
            company_number=str(match.get("reg_charity_number") or ""),
            matched_title=str(match.get("charity_name") or ""),
            candidates_considered=len(candidates),
            reason="EXACT_UNIQUE_REGISTERED_MATCH",
        )

    def resolve(self, entities: Iterable[InstitutionalEntity]) -> ResolutionReport:
        attempts: list[ResolutionAttempt] = []
        updated: list[InstitutionalEntity] = []

        for entity in entities:
            attempt = self.resolve_entity(entity)
            attempts.append(attempt)
            if not (attempt.resolved and attempt.company_number):
                updated.append(entity)
                continue

            update: dict[str, object] = {
                "identifiers": {
                    **entity.identifiers,
                    "charity_number": attempt.company_number,
                },
                "metadata": {
                    **entity.metadata,
                    "charity_matched_name": attempt.matched_title or "",
                    "charity_match_basis": attempt.reason,
                },
            }
            # Being on the register types the body. An UNKNOWN domain that stays UNKNOWN
            # can never contribute to a coupling verdict, so this is the point of doing it.
            if entity.system_domain is SystemDomain.UNKNOWN:
                update["system_domain"] = SystemDomain.ADVOCACY
                update["roles"] = [EntityRole.ADVOCACY_ORGANISATION]
                update["metadata"] = {
                    **update["metadata"],  # type: ignore[dict-item]
                    "domain_undetermined": False,
                    "domain_source": "charity_commission_register",
                }
            updated.append(entity.model_copy(update=update))

        return ResolutionReport(attempts=attempts, entities=updated)
