from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

#: Party identifier schemes strong enough to merge two entities during resolution.
#: GB-COH is Companies House; GB-CHC/SC/NIC are the charity regulators.
STRONG_SCHEMES = {
    "GB-COH": "companies_house",
    "GB-CHC": "charity_number",
    "OSCR": "charity_number",
    "GB-SC": "charity_number",
    "GB-NIC": "charity_number",
    "LEI": "lei",
}

#: Identifiers embedded in an OCDS party id string, e.g. "GB-COH-01234567".
_EMBEDDED = re.compile(r"^(?P<scheme>GB-COH|GB-CHC|GB-NIC)-(?P<number>[0-9A-Z]{5,10})$", re.I)


def parse_ocds_date(value: str | None) -> date | None:
    """Parse an OCDS datetime to a date, returning None rather than raising."""

    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def identifiers_from_party(party: dict[str, Any] | None, party_id: str | None) -> dict[str, str]:
    """Extract identifiers from an OCDS party, preferring the structured identifier block.

    Publishers differ: Find a Tender supplies {"scheme": "GB-COH", "id": "08664789"} while
    Contracts Finder embeds the scheme in the party id string. Both routes are handled, and
    anything unrecognised is kept only as a weak ocds_party_id so it can never drive an
    entity merge on its own.
    """

    found: dict[str, str] = {}
    identifier = (party or {}).get("identifier") or {}
    scheme = str(identifier.get("scheme") or "").upper()
    number = str(identifier.get("id") or "").strip()
    if scheme in STRONG_SCHEMES and number:
        found[STRONG_SCHEMES[scheme]] = number.upper()

    if not found and party_id:
        match = _EMBEDDED.match(party_id.strip())
        if match:
            key = STRONG_SCHEMES.get(match.group("scheme").upper())
            if key:
                found[key] = match.group("number").upper()

    if party_id:
        found["ocds_party_id"] = party_id
    return found


def index_parties(release: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a release's parties[] by their OCDS id for lookup from award/buyer blocks."""

    index: dict[str, dict[str, Any]] = {}
    for party in release.get("parties") or []:
        party_id = party.get("id")
        if party_id:
            index[str(party_id)] = party
    return index
