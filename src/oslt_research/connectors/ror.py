from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import httpx

from oslt_research.connectors.companies_house import ResolutionAttempt, ResolutionReport
from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    SystemDomain,
    normalise_name,
)


#: DS059 in the source register. ROR covers research organisations - universities,
#: institutes, funders - which neither Companies House nor the Charity Commission reaches.
#: Universities are the largest remaining class of unidentified entity in the graph.
SOURCE_ID = "DS059"

#: ROR organisation types that map cleanly onto a system domain. Anything else is left
#: UNKNOWN rather than guessed, since an entity typed by assumption can widen apparent
#: cross-system spread and manufacture the coupling MD15 is meant to detect.
TYPE_TO_DOMAIN: dict[str, tuple[SystemDomain, EntityRole]] = {
    "education": (SystemDomain.ACADEMIC, EntityRole.ACADEMIC_BODY),
    "facility": (SystemDomain.ACADEMIC, EntityRole.ACADEMIC_BODY),
    "healthcare": (SystemDomain.CLINICAL, EntityRole.PROVIDER),
    "funder": (SystemDomain.PHILANTHROPIC, EntityRole.PHILANTHROPIC_FUNDER),
    "government": (SystemDomain.POLICY, EntityRole.GOVERNMENT_DEPARTMENT),
    "nonprofit": (SystemDomain.ADVOCACY, EntityRole.ADVOCACY_ORGANISATION),
}

#: Types checked in this order, so a university that also funds is typed academic rather
#: than philanthropic. Most UK universities carry the funder type.
TYPE_PRECEDENCE = ("education", "healthcare", "government", "nonprofit", "facility", "funder")


@dataclass(frozen=True)
class RorTyping:
    entity_id: str
    ror_id: str
    display_name: str
    types: list[str] = field(default_factory=list)
    domain_assigned: SystemDomain | None = None


class RorResolver:
    """Attach ROR identifiers to research organisations, and type them.

    Does for universities and institutes what Companies House does for companies. Also
    resolves SystemDomain.UNKNOWN where the ROR type maps unambiguously, which matters
    because an UNKNOWN entity is excluded from cross-system spread and so cannot
    contribute to a coupling verdict at all.

    Matching is exact on the normalised display name and requires an active record, for
    the same reason as the other resolvers: a fuzzy match would put an authoritative
    identifier on a guess.

    Requires no API key.
    """

    source_name = "ROR"
    connector_version = "1"
    base_url = "https://api.ror.org/organizations"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 45.0,
        min_interval_seconds: float = 0.15,
        country_code: str | None = "GB",
    ):
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self.country_code = country_code
        self._last_call = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    @staticmethod
    def display_name(item: dict[str, Any]) -> str:
        """ROR v2 carries names as a list; the display name is the one tagged ror_display."""

        names = item.get("names") or []
        for entry in names:
            if "ror_display" in (entry.get("types") or []):
                return str(entry.get("value") or "")
        for entry in names:
            if "label" in (entry.get("types") or []):
                return str(entry.get("value") or "")
        return str(names[0].get("value")) if names else ""

    @staticmethod
    def _in_country(item: dict[str, Any], code: str | None) -> bool:
        if not code:
            return True
        for location in item.get("locations") or []:
            details = location.get("geonames_details") or {}
            if str(details.get("country_code") or "").upper() == code.upper():
                return True
        return False

    @classmethod
    def _domain_for(cls, types: list[str]) -> tuple[SystemDomain, EntityRole] | None:
        lowered = [str(item).lower() for item in types]
        for candidate in TYPE_PRECEDENCE:
            if candidate in lowered:
                return TYPE_TO_DOMAIN[candidate]
        return None

    def _search(self, query: str) -> list[dict[str, Any]]:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._throttle()
            response = client.get(
                self.base_url, params={"query": query}, headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json().get("items") or []
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
            if normalise_name(self.display_name(item)) == target
            and str(item.get("status") or "").lower() == "active"
            and self._in_country(item, self.country_code)
        ]

        if not exact:
            return ResolutionAttempt(
                entity.entity_id, query, False,
                candidates_considered=len(candidates), reason="NO_EXACT_ACTIVE_MATCH",
            )
        if len({str(item.get("id")) for item in exact}) > 1:
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
            company_number=str(match.get("id") or "").rsplit("/", 1)[-1],
            matched_title=self.display_name(match),
            candidates_considered=len(candidates),
            reason="EXACT_UNIQUE_ACTIVE_MATCH",
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

            update: dict[str, Any] = {
                "identifiers": {**entity.identifiers, "ror": attempt.company_number},
                "metadata": {
                    **entity.metadata,
                    "ror_matched_name": attempt.matched_title or "",
                    "ror_match_basis": attempt.reason,
                },
            }
            updated.append(entity.model_copy(update=update))

        return ResolutionReport(attempts=attempts, entities=updated)
