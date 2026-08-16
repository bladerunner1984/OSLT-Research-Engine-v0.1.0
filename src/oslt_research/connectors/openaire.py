from __future__ import annotations

import json
from typing import Any

import httpx

from oslt_research.evidence.provenance import sha256_text

from .base import HarvestQuery, RawRecord, SourceConnector


#: DS075 in the source register (added 2026-08). OpenAIRE AGGREGATES Crossref (DS034),
#: PubMed (DS036) and repository records, so records from here are not independent
#: corroboration of those sources. NOTE: ``pipelines.harvest.SOURCE_IDS`` still maps
#: "OpenAIRE" to DS041, which is OSF Registries - a mislabel flagged for human
#: correction; it is not changed here because it relabels already-stored provenance.
SOURCE_ID = "DS075"


def _unwrap(value: Any) -> Any:
    """Strip OpenAIRE's ``{"$": ...}`` scalar wrapper.

    The API is a JSON rendering of XML, so every leaf value is either a bare scalar, a
    dict whose ``$`` key holds the text and whose ``@`` keys hold attributes, or a list
    of such dicts when the element repeated. Every field must be read through here or
    through :func:`_as_list`; assuming any one shape produces silent data loss on the
    records that happen to use another.
    """
    if isinstance(value, dict):
        return value.get("$")
    return value


def _as_list(value: Any) -> list[Any]:
    """Normalise single-dict / list / missing into a list, since cardinality varies per record."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(value: Any) -> str:
    unwrapped = _unwrap(value)
    return "" if unwrapped is None else str(unwrapped).strip()


class OpenAireConnector(SourceConnector):
    """OpenAIRE Explore publication search: a keyless aggregator over ~150M open records.

    Its value here is breadth of *aggregation* — it pulls from Crossref, PubMed Central,
    DataCite and thousands of institutional repositories — which makes it a useful
    cross-check on coverage claims from any single index. That same aggregation means one
    work often appears more than once, so records are deduplicated on the deduplicated
    object identifier and DOI before being returned.

    Paged with ``page``/``size``; verified live that ``keywords`` genuinely filters
    (distinct terms return disjoint result sets) and that successive pages do not overlap.
    """

    source_name = "OpenAIRE"
    connector_version = "1"
    base_url = "https://api.openaire.eu/search/publications"

    #: OpenAIRE rejects larger pages on this endpoint.
    MAX_PAGE_SIZE = 100

    #: Ordered preference for what counts as the publication date. ``created`` is
    #: deliberately excluded: it is the date the metadata record was registered with the
    #: aggregator, and is routinely years adrift of publication (a 2018 article carrying
    #: ``created: 2020-12-24``). ``dri:dateOfCollection`` is worse still — it is OpenAIRE's
    #: own harvest timestamp and is identical across unrelated records.
    DATE_PREFERENCE = ("published-print", "published-online", "issued")

    def __init__(self, *, client: httpx.AsyncClient | None = None):
        self._client = client

    @staticmethod
    def _params(query: HarvestQuery, page: int, page_size: int) -> dict[str, Any]:
        params: dict[str, Any] = {
            "keywords": query.concept,
            "size": page_size,
            "page": page,
            "format": "json",
        }
        if query.from_date:
            params["fromDateAccepted"] = query.from_date
        if query.to_date:
            params["toDateAccepted"] = query.to_date
        params.update(query.extra_filters)
        return params

    @classmethod
    def _published_at(cls, entity: dict[str, Any]) -> str | None:
        by_class: dict[str, str] = {}
        for item in _as_list(entity.get("relevantdate")):
            if isinstance(item, dict):
                class_id = str(item.get("@classid") or "")
                text = _text(item)
                if class_id and text:
                    by_class.setdefault(class_id, text)
        for class_id in cls.DATE_PREFERENCE:
            if by_class.get(class_id):
                return by_class[class_id]
        # Acceptance date is the last resort: it precedes print publication but at least
        # describes the work rather than the aggregator's bookkeeping.
        return _text(entity.get("dateofacceptance")) or None

    @staticmethod
    def _identifiers(entity: dict[str, Any]) -> dict[str, str]:
        identifiers: dict[str, str] = {}
        for item in _as_list(entity.get("pid")):
            if not isinstance(item, dict):
                continue
            class_id = str(item.get("@classid") or "").strip().lower()
            value = _text(item)
            if class_id and value:
                identifiers.setdefault(class_id, value)
        return identifiers

    @staticmethod
    def _title(entity: dict[str, Any]) -> str:
        titles = _as_list(entity.get("title"))
        for item in titles:
            if isinstance(item, dict) and str(item.get("@classid") or "") == "main title":
                text = _text(item)
                if text:
                    return text
        for item in titles:
            text = _text(item)
            if text:
                return text
        return ""

    @staticmethod
    def _authors(entity: dict[str, Any]) -> list[str]:
        ranked: list[tuple[float, str]] = []
        for item in _as_list(entity.get("creator")):
            name = _text(item)
            if not name:
                continue
            rank = 0.0
            if isinstance(item, dict):
                try:
                    rank = float(item.get("@rank") or 0)
                except (TypeError, ValueError):
                    rank = 0.0
            ranked.append((rank, name))
        # Author order carries meaning in bibliometrics; @rank is authoritative where the
        # JSON array order is not guaranteed.
        ranked.sort(key=lambda pair: pair[0])
        return [name for _, name in ranked]

    @classmethod
    def _record(cls, result: dict[str, Any], raw_hash: str) -> RawRecord | None:
        metadata = result.get("metadata") or {}
        entity = ((metadata.get("oaf:entity") or {}).get("oaf:result")) or {}
        if not entity:
            return None

        header = result.get("header") or {}
        obj_id = _text(header.get("dri:objIdentifier"))
        identifiers = cls._identifiers(entity)
        record_id = obj_id or identifiers.get("doi") or ""
        if not record_id:
            return None

        doi = identifiers.get("doi", "")
        abstracts = [_text(item) for item in _as_list(entity.get("description"))]
        content = max(abstracts, key=len, default="")

        if doi:
            source_uri = f"https://doi.org/{doi}"
        else:
            source_uri = f"https://explore.openaire.eu/search/publication?articleId={obj_id}"

        return RawRecord(
            source_name=cls.source_name,
            source_record_id=record_id,
            title=cls._title(entity),
            content=content,
            source_uri=source_uri,
            published_at=cls._published_at(entity),
            identifiers=identifiers,
            authors=cls._authors(entity),
            metadata={
                "publisher": _text(entity.get("publisher")),
                "journal": _text(entity.get("journal")),
                "language": (
                    str((entity.get("language") or {}).get("@classname") or "")
                    if isinstance(entity.get("language"), dict)
                    else ""
                ),
                "access_right": (
                    str((entity.get("bestaccessright") or {}).get("@classname") or "")
                    if isinstance(entity.get("bestaccessright"), dict)
                    else ""
                ),
                "collected_from": [
                    str(item.get("@name") or "")
                    for item in _as_list(entity.get("collectedfrom"))
                    if isinstance(item, dict)
                ],
                # Retained so downstream code can tell publication date from the
                # aggregator's harvest date rather than conflating them.
                "openaire_collected_at": _text(header.get("dri:dateOfCollection")),
                "connector_version": cls.connector_version,
            },
            raw_response_hash=raw_hash,
        )

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        client = self._client or httpx.AsyncClient(timeout=60.0)
        records: list[RawRecord] = []
        seen: set[str] = set()
        page = 1
        try:
            while len(records) < query.max_records:
                page_size = min(self.MAX_PAGE_SIZE, query.max_records - len(records))
                response = await client.get(
                    self.base_url,
                    params=self._params(query, page, page_size),
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
                raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))

                results = _as_list(
                    ((payload.get("response") or {}).get("results") or {}).get("result")
                )
                if not results:
                    break

                for result in results:
                    if not isinstance(result, dict):
                        continue
                    record = self._record(result, raw_hash)
                    if record is None:
                        continue
                    # The same work reaches OpenAIRE through several repositories, so the
                    # DOI is deduplicated alongside the object id.
                    keys = {record.source_record_id}
                    if record.identifiers.get("doi"):
                        keys.add(f"doi:{record.identifiers['doi'].lower()}")
                    if keys & seen:
                        continue
                    seen |= keys
                    records.append(record)

                # A short page means the result set is exhausted; asking for page n+1
                # would return an empty body at best and repeat page 1 at worst.
                if len(results) < page_size:
                    break
                page += 1
            return records[: query.max_records]
        finally:
            if self._client is None:
                await client.aclose()
