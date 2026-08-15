from __future__ import annotations

import re
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import time

import httpx

from oslt_research.domain.models import EvidenceObject
from oslt_research.evidence.provenance import admit_evidence, sha256_text


EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"

#: Appended to provenance rather than replacing anything, so a downstream reader can tell that
#: the content of an admitted record is no longer byte-identical to what the harvest connector
#: returned. Versioned because a future merge strategy must be distinguishable from this one.
ABSTRACT_ENRICHMENT_TRANSFORMATION_ID = "ABSTRACT_ENRICHED_V1"

SOURCE_EUROPE_PMC = "europe_pmc"
SOURCE_OPENALEX = "openalex"

#: Below this, a returned "abstract" is almost always a placeholder ("No abstract available.",
#: a copyright line, a section heading) and admitting it would fabricate substance.
MINIMUM_ABSTRACT_LENGTH = 40

#: Records at or above this already carry enough text for lane coding; querying an external API
#: for them spends quota without changing any downstream decision.
DEFAULT_MIN_CONTENT_LENGTH = 200

_DOI_URL_PREFIX = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)
_DIGITS = re.compile(r"(\d+)")


@dataclass(frozen=True)
class EnrichmentSummary:
    """Outcome of one enrichment pass.

    Reported rather than logged because the median content length before and after is the
    figure that justifies (or refutes) running enrichment at all: if the median does not move,
    the corpus is still too thin to code and the answer is a different source, not a retry.
    """

    attempted: int = 0
    enriched: int = 0
    unenriched: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    source_errors: dict[str, int] = field(default_factory=dict)
    median_content_length_before: float = 0.0
    median_content_length_after: float = 0.0


@dataclass(frozen=True)
class _LookupKey:
    kind: str
    value: str


#: Minimum seconds between calls to one host. OpenAlex refused 1,379 requests with HTTP
#: 429 during an unthrottled enrichment run over 857 records, so 808 stayed unenriched not
#: because no abstract existed but because the source stopped answering. Politeness here
#: is not courtesy, it is the difference between getting the data and not.
MIN_INTERVAL_SECONDS = 0.12

#: Give up on a host for the rest of the run after this many consecutive 429s. Continuing
#: to hammer a source that is refusing wastes the whole run and worsens the throttle.
RATE_LIMIT_GIVE_UP_AFTER = 5


class _HostThrottle:
    """Paces calls per host and stops asking a host that is refusing."""

    def __init__(self, min_interval: float = MIN_INTERVAL_SECONDS):
        self.min_interval = min_interval
        self._last: dict[str, float] = {}
        self._consecutive_429: dict[str, int] = {}

    def blocked(self, host: str) -> bool:
        return self._consecutive_429.get(host, 0) >= RATE_LIMIT_GIVE_UP_AFTER

    def wait(self, host: str) -> None:
        elapsed = time.monotonic() - self._last.get(host, 0.0)
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last[host] = time.monotonic()

    def record(self, host: str, status_code: int) -> None:
        if status_code == 429:
            self._consecutive_429[host] = self._consecutive_429.get(host, 0) + 1
        else:
            self._consecutive_429[host] = 0


class AbstractEnricher:
    """Backfills abstracts for evidence whose content is title-only.

    Two rules govern everything here. First, nothing is invented: an abstract is only written
    when a keyless public API returned one for an identifier carried by the record, and a record
    with no hit is returned byte-identical to its input. Second, an enrichment is never silent:
    the content hash in metadata is recomputed and the transformation id is appended to
    provenance, so an enriched record remains admissible under ``assess_evidence_admission``
    while still declaring that it was altered after harvest.
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        min_content_length: int = DEFAULT_MIN_CONTENT_LENGTH,
        mailto: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = client
        self._throttle = _HostThrottle()
        self.min_content_length = min_content_length
        self.mailto = mailto
        self.timeout = timeout

    # ---------------------------------------------------------------- identifiers

    @staticmethod
    def _normalise_doi(value: str) -> str:
        return _DOI_URL_PREFIX.sub("", value.strip()).strip().lower()

    @staticmethod
    def _normalise_pmid(value: str) -> str:
        # OpenAlex hands back PMIDs as pubmed URLs; PubMed hands back bare digits.
        match = _DIGITS.search(str(value))
        return match.group(1) if match else ""

    @classmethod
    def _lookup_keys(cls, evidence: EvidenceObject) -> list[_LookupKey]:
        """DOI, then PMID, then title -- strongest identifier first.

        Title search is last and deliberately reluctant: it is the only key that can match the
        wrong paper, so it is used only when the record carries no identifier at all.
        """

        identifiers: dict[str, Any] = evidence.metadata.get("identifiers") or {}
        lowered = {str(key).lower(): value for key, value in identifiers.items() if value}

        doi = lowered.get("doi") or lowered.get("doi_url")
        pmid = lowered.get("pmid") or lowered.get("pubmed")

        family = evidence.dependency_family or ""
        if not doi and family.startswith("doi:"):
            doi = family[len("doi:") :]
        if not pmid and family.startswith("pmid:"):
            pmid = family[len("pmid:") :]

        keys: list[_LookupKey] = []
        if doi:
            normalised = cls._normalise_doi(str(doi))
            if normalised:
                keys.append(_LookupKey("doi", normalised))
        if pmid:
            normalised = cls._normalise_pmid(pmid)
            if normalised:
                keys.append(_LookupKey("pmid", normalised))
        title = evidence.title.strip()
        if title:
            keys.append(_LookupKey("title", title))
        return keys

    # ---------------------------------------------------------------- sources

    @staticmethod
    def _clean_abstract(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        text = " ".join(value.split())
        return text if len(text) >= MINIMUM_ABSTRACT_LENGTH else None

    @staticmethod
    def _europe_pmc_query(key: _LookupKey) -> str:
        if key.kind == "doi":
            return f'DOI:"{key.value}"'
        if key.kind == "pmid":
            return f"EXT_ID:{key.value} AND SRC:MED"
        return f'TITLE:"{key.value}"'

    def _fetch_europe_pmc(self, client: httpx.Client, key: _LookupKey) -> str | None:
        params = {
            "query": self._europe_pmc_query(key),
            "format": "json",
            "resultType": "core",
            "pageSize": 1,
        }
        if self._throttle.blocked("europe_pmc"):
            return None
        self._throttle.wait("europe_pmc")
        response = client.get(EUROPE_PMC_SEARCH_URL, params=params)
        self._throttle.record("europe_pmc", response.status_code)
        response.raise_for_status()
        payload = response.json()
        results = ((payload or {}).get("resultList") or {}).get("result") or []
        for item in results:
            abstract = self._clean_abstract(item.get("abstractText"))
            if abstract:
                return abstract
        return None

    @staticmethod
    def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
        # Same reconstruction as OpenAlexConnector; duplicated rather than imported so that a
        # connector-layer refactor cannot silently change the text written into provenance.
        if not index:
            return ""
        positions: list[tuple[int, str]] = []
        for word, indices in index.items():
            positions.extend((position, word) for position in indices)
        return " ".join(word for _, word in sorted(positions))

    def _fetch_openalex(self, client: httpx.Client, key: _LookupKey) -> str | None:
        params: dict[str, str | int] = {"per_page": 1}
        if key.kind == "doi":
            params["filter"] = f"doi:{key.value}"
        elif key.kind == "pmid":
            params["filter"] = f"pmid:{key.value}"
        else:
            params["filter"] = f"title.search:{key.value}"
        if self.mailto:
            params["mailto"] = self.mailto

        if self._throttle.blocked("openalex"):
            return None
        self._throttle.wait("openalex")
        response = client.get(OPENALEX_WORKS_URL, params=params)
        self._throttle.record("openalex", response.status_code)
        response.raise_for_status()
        payload = response.json()
        for item in (payload or {}).get("results") or []:
            reconstructed = self._abstract_from_inverted_index(item.get("abstract_inverted_index"))
            abstract = self._clean_abstract(reconstructed)
            if abstract:
                return abstract
        return None

    def _resolve(
        self, client: httpx.Client, evidence: EvidenceObject, summary_errors: dict[str, int]
    ) -> tuple[str, str, _LookupKey] | None:
        """Return (abstract, source, key) for the first hit, or None.

        Identifier strength outranks source preference: an exact DOI hit on OpenAlex is worth
        more than a title-search hit on Europe PMC, so the key loop is the outer one.
        """

        fetchers = (
            (SOURCE_EUROPE_PMC, self._fetch_europe_pmc),
            (SOURCE_OPENALEX, self._fetch_openalex),
        )
        for key in self._lookup_keys(evidence):
            for source, fetch in fetchers:
                try:
                    abstract = fetch(client, key)
                except httpx.HTTPError:
                    # A source that is down or rate-limiting must degrade the pass, not abort
                    # it: a partial enrichment is recoverable, a half-written corpus is not.
                    summary_errors[source] = summary_errors.get(source, 0) + 1
                    continue
                if abstract:
                    return abstract, source, key
        return None

    # ---------------------------------------------------------------- application

    @staticmethod
    def _merged_content(evidence: EvidenceObject, abstract: str) -> str | None:
        """Append the abstract to whatever the harvest captured; None if it adds nothing."""

        existing = evidence.content.strip()
        if not existing:
            return f"{evidence.title.strip()}\n\n{abstract}"
        if abstract.casefold() in existing.casefold():
            return None
        return f"{existing}\n\n{abstract}"

    def _apply(
        self, evidence: EvidenceObject, abstract: str, source: str, key: _LookupKey
    ) -> EvidenceObject | None:
        content = self._merged_content(evidence, abstract)
        if content is None:
            return None

        provenance = evidence.provenance.model_copy(
            update={
                "transformation_ids": [
                    *evidence.provenance.transformation_ids,
                    ABSTRACT_ENRICHMENT_TRANSFORMATION_ID,
                ]
            }
        )
        metadata = {
            **evidence.metadata,
            "content_sha256": sha256_text(content),
            "abstract_enrichment": {
                "source": source,
                "lookup_kind": key.kind,
                "lookup_value": key.value,
                "abstract_sha256": sha256_text(abstract),
                "abstract_length": len(abstract),
                "transformation_id": ABSTRACT_ENRICHMENT_TRANSFORMATION_ID,
            },
        }
        # provenance.checksum_sha256 is the attestation of the *original* API response and is
        # left alone; overwriting it would destroy the only link back to the harvested bytes.
        enriched = evidence.model_copy(
            update={"content": content, "provenance": provenance, "metadata": metadata}
        )
        return admit_evidence(enriched)

    def enrich(
        self, evidence: Sequence[EvidenceObject]
    ) -> tuple[list[EvidenceObject], EnrichmentSummary]:
        """Return a new list plus a summary; inputs are never mutated in place."""

        before = [len(item.content) for item in evidence]
        own_client = self._client is None
        client = self._client or httpx.Client(timeout=self.timeout)

        results: list[EvidenceObject] = []
        attempted = 0
        enriched_count = 0
        by_source: dict[str, int] = {}
        source_errors: dict[str, int] = {}
        try:
            for item in evidence:
                if len(item.content) >= self.min_content_length:
                    results.append(item)
                    continue
                attempted += 1
                hit = self._resolve(client, item, source_errors)
                updated = self._apply(item, *hit) if hit else None
                if updated is None:
                    results.append(item)
                    continue
                results.append(updated)
                enriched_count += 1
                by_source[hit[1]] = by_source.get(hit[1], 0) + 1
        finally:
            if own_client:
                client.close()

        after = [len(item.content) for item in results]
        return results, EnrichmentSummary(
            attempted=attempted,
            enriched=enriched_count,
            unenriched=attempted - enriched_count,
            by_source=by_source,
            source_errors=source_errors,
            median_content_length_before=_median(before),
            median_content_length_after=_median(after),
        )


def _median(values: Sequence[int]) -> float:
    return float(statistics.median(values)) if values else 0.0
