from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


#: DS014 in the source register (the Census 2021 gender identity publication),
#: open aggregate portion. The mid-year population estimates streamed by
#: connectors.ons_population are DS076, not this row. This is the published,
#: openly accessible part of ONS - not the Secure Research Service, which needs
#: accreditation. Population estimates matter most: the ascertainment propositions are
#: about RATES, and a rate without a denominator is a count wearing a percentage sign.
SOURCE_ID = "DS014"
BASE_URL = "https://api.beta.ons.gov.uk/v1"


@dataclass(frozen=True)
class OnsDataset:
    dataset_id: str
    title: str
    description: str = ""

    def matches(self, *terms: str) -> bool:
        haystack = f"{self.title} {self.description}".lower()
        return any(term.lower() in haystack for term in terms)


@dataclass(frozen=True)
class OnsVersion:
    dataset_id: str
    edition: str
    version: str
    dimensions: list[str] = field(default_factory=list)
    csv_url: str | None = None
    release_date: str | None = None

    @property
    def has_download(self) -> bool:
        return bool(self.csv_url)


class OnsDatasetsConnector:
    """Discovery and metadata for ONS open datasets.

    Deliberately stops at metadata and a download URL rather than parsing observations.
    ONS dimensions vary per dataset (time, geography, sex, age for population estimates;
    quite different elsewhere), so a generic observation parser would either be wrong for
    most datasets or silently coerce them into a shape they do not have. Choosing the
    right slice is a study design decision and belongs in a preregistered specification.

    Requires no API key.
    """

    source_name = "ONS"
    connector_version = "1"
    base_url = BASE_URL

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 45.0):
        self._client = client
        self.timeout = timeout

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            response = client.get(url, params=params, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        finally:
            if self._client is None:
                client.close()

    def list_datasets(self, *, limit: int = 200) -> list[OnsDataset]:
        payload = self._get(f"{self.base_url}/datasets", {"limit": min(limit, 500)})
        return [
            OnsDataset(
                dataset_id=str(item.get("id") or ""),
                title=str(item.get("title") or ""),
                description=str(item.get("description") or ""),
            )
            for item in payload.get("items") or []
            if item.get("id")
        ]

    def search(self, *terms: str, limit: int = 500) -> list[OnsDataset]:
        return [item for item in self.list_datasets(limit=limit) if item.matches(*terms)]

    def latest_version(self, dataset_id: str, *, edition: str | None = None) -> OnsVersion | None:
        """Resolve a dataset to its most recent published version.

        Follows the edition's latest_version link rather than composing a versions URL.
        Composing one returns 404: the version path is not derivable from the edition name,
        and the API expects the link to be followed.
        """

        editions = self._get(f"{self.base_url}/datasets/{dataset_id}/editions").get("items") or []
        if not editions:
            return None

        chosen = None
        if edition:
            chosen = next((item for item in editions if item.get("edition") == edition), None)
        # Editions are not ordered by recency, and their names encode periods rather than
        # sort keys, so without an explicit choice the first is taken and the edition is
        # recorded on the result so a caller can see which one they got.
        chosen = chosen or editions[0]

        href = ((chosen.get("links") or {}).get("latest_version") or {}).get("href")
        if not href:
            return None

        version = self._get(href)
        downloads = version.get("downloads") or {}
        csv_entry = downloads.get("csv") or {}
        return OnsVersion(
            dataset_id=dataset_id,
            edition=str(chosen.get("edition") or ""),
            version=str(version.get("version") or ""),
            dimensions=[
                str(item.get("name") or "") for item in version.get("dimensions") or []
            ],
            csv_url=str(csv_entry.get("href") or "") or None,
            release_date=str(version.get("release_date") or "") or None,
        )
