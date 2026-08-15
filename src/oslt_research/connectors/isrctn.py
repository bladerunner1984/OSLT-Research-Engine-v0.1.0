from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from xml.etree import ElementTree

import httpx

from oslt_research.pipelines.registration_linkage import (
    RegistrationRecord,
    parse_registration_date,
)


#: DS038 in the source register. The ISRCTN registry answers in XML under its own
#: namespace, so every element lookup has to be namespace-qualified.
SOURCE_ID = "DS038"
NAMESPACE = "http://www.67bricks.com/isrctn"
_NS = {"i": NAMESPACE}


@dataclass(frozen=True)
class IsrctnSweep:
    registrations: list[RegistrationRecord] = field(default_factory=list)
    trials_seen: int = 0
    total_available: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)


def _text(node: ElementTree.Element | None, path: str) -> str:
    if node is None:
        return ""
    found = node.find(path, _NS)
    return (found.text or "").strip() if found is not None else ""


class IsrctnConnector:
    """Trial registrations from the ISRCTN registry.

    Widens the MD11 denominator, which is the weakest part of that analysis: publication
    probability cannot be estimated from a corpus of publications, only from registrations
    followed forward. ClinicalTrials.gov alone supplied 20 registrations, which is far too
    few to estimate a rate from.

    Registration dates come from the publicIdentifierDateAssigned attribute rather than
    any element, because that is when the registration entered the public record - the
    point from which a publication window can be measured.

    Requires no API key.
    """

    source_name = "ISRCTN"
    connector_version = "1"
    base_url = "https://www.isrctn.com/api/query/format/default"

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 60.0):
        self._client = client
        self.timeout = timeout

    def _fetch(self, params: dict[str, object]) -> str:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.text
        finally:
            if self._client is None:
                client.close()

    @staticmethod
    def _registration(trial: ElementTree.Element) -> RegistrationRecord | None:
        number = _text(trial, "i:isrctn")
        if not number:
            return None

        # The attribute records when the identifier entered the public record. An element
        # date would describe the study, not its registration.
        assigned = trial.get("publicIdentifierDateAssigned") or ""
        registered_on = parse_registration_date(assigned[:10]) if assigned else None

        description = trial.find("i:trialDescription", _NS)
        title = _text(description, "i:scientificTitle") or _text(description, "i:title")

        return RegistrationRecord(
            registration_id=f"ISRCTN{number}" if not number.upper().startswith("ISRCTN") else number,
            registered_on=registered_on,
            title=title[:200],
            status="published" if trial.get("isPublished") == "true" else "unpublished",
        )

    def sweep(self, *, concept: str, limit: int = 100) -> IsrctnSweep:
        payload = self._fetch({"q": concept, "limit": min(limit, 100)})
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError:
            return IsrctnSweep(skip_reasons={"XML_PARSE_FAILED": 1})

        total = int(root.get("totalCount") or 0)
        registrations: list[RegistrationRecord] = []
        skips: dict[str, int] = {}
        trials = root.findall(".//i:trial", _NS)

        for trial in trials:
            record = self._registration(trial)
            if record is None:
                skips["NO_REGISTRATION_NUMBER"] = skips.get("NO_REGISTRATION_NUMBER", 0) + 1
                continue
            if record.registered_on is None:
                # An undated registration cannot anchor a publication window, so it would
                # contribute to the numerator without a denominator.
                skips["REGISTRATION_UNDATED"] = skips.get("REGISTRATION_UNDATED", 0) + 1
                continue
            registrations.append(record)

        return IsrctnSweep(
            registrations=registrations,
            trials_seen=len(trials),
            total_available=total,
            skip_reasons=skips,
        )
