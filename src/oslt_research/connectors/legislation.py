from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from xml.etree import ElementTree

import httpx


#: DS032 in the source register. legislation.gov.uk publishes an Atom feed; it returns 406
#: to an application/json Accept header, so the Accept must be atom+xml.
SOURCE_ID = "DS032"
ATOM = "http://www.w3.org/2005/Atom"
_NS = {"a": ATOM}

#: Titles carrying these markers describe an instrument that has been withdrawn or
#: superseded. Kept as a flag rather than filtered out: a revoked instrument was in force
#: for a period, and that period is exactly what a policy-embedding proposition is about.
REVOKED_MARKERS = ("(revoked)", "(repealed)")


@dataclass(frozen=True)
class LegislationItem:
    """A statute or statutory instrument.

    `enacted_year` comes from the legislation.gov.uk identifier (/ukpga/2004/7), which
    encodes the year Parliament made the instrument. `record_updated` comes from the Atom
    <updated> element and is when the WEBSITE record was last revised - the Gender
    Recognition Act 2004 carries a record_updated in 2024. The two are unrelated, and
    only the first can anchor a policy outcome.
    """

    title: str
    url: str
    enacted_year: int | None = None
    record_updated: date | None = None
    revoked: bool = False

    @property
    def is_dated(self) -> bool:
        """Dated means the enactment year is known. A website revision is not a date."""

        return self.enacted_year is not None

    def anchor_date(self) -> date | None:
        """The date this instrument can anchor an outcome to.

        Deliberately ignores record_updated. Using a website revision timestamp as a
        policy date would place the Gender Recognition Act 2004 in 2024 and make any
        temporal-ordering test meaningless.

        Resolves to 1 January of the enactment year, which is the precision the identifier
        actually carries. A day-level date would be invented.
        """

        return date(self.enacted_year, 1, 1) if self.enacted_year else None


@dataclass(frozen=True)
class LegislationFeed:
    query: str
    items: list[LegislationItem] = field(default_factory=list)
    entries_seen: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)

    def dated(self) -> list[LegislationItem]:
        return [item for item in self.items if item.is_dated]

    def outcome_dates(self) -> list[date]:
        """Real, citable policy dates.

        MD10 and MD15 are claims about ties preceding a change. Every run so far has used
        an outcome date chosen by hand, and the coupling verdict proved highly sensitive to
        that choice. Legislation supplies dates that were not chosen to suit the analysis.
        """

        return sorted({item.anchor_date() for item in self.dated() if item.anchor_date()})


class LegislationConnector:
    """Dated UK legislation from the legislation.gov.uk Atom feed.

    Its value here is anchoring rather than volume. The coupling test needs an outcome
    that ties can be said to precede, and a date picked by the analyst is a free parameter
    the verdict turns on - demonstrated earlier when the same graph returned MD15 against
    an arbitrary future date and MX09 against a real one. Statutes and statutory
    instruments carry dates fixed by Parliament rather than by the person running the test.

    Requires no API key.
    """

    source_name = "Legislation"
    connector_version = "1"
    base_url = "https://www.legislation.gov.uk/all/data.feed"

    #: Year in a legislation.gov.uk identifier, e.g. /ukpga/2004/7 or /uksi/2023/1234
    _YEAR_IN_URL = re.compile(r"/(?:ukpga|uksi|ssi|asp|nisr|nia|wsi)/(\d{4})/")

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 45.0):
        self._client = client
        self.timeout = timeout

    def _fetch(self, params: dict[str, object]) -> str:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            response = client.get(
                self.base_url,
                params=params,
                headers={"Accept": "application/atom+xml"},
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text
        finally:
            if self._client is None:
                client.close()

    @classmethod
    def _item(cls, entry: ElementTree.Element) -> LegislationItem | None:
        title_node = entry.find("a:title", _NS)
        title = (title_node.text or "").strip() if title_node is not None else ""
        if not title or title.lower() == "search results":
            return None

        link = entry.find("a:link", _NS)
        url = (link.get("href") or "") if link is not None else ""

        year: int | None = None
        match = cls._YEAR_IN_URL.search(url)
        if match:
            year = int(match.group(1))
        else:
            trailing = re.search(r"\b(19|20)\d{2}\b", title)
            if trailing:
                year = int(trailing.group(0))

        record_updated: date | None = None
        updated = entry.find("a:updated", _NS)
        if updated is not None and updated.text:
            try:
                record_updated = datetime.fromisoformat(
                    updated.text.strip().replace("Z", "+00:00")
                ).date()
            except ValueError:
                record_updated = None

        return LegislationItem(
            title=title,
            url=url,
            enacted_year=year,
            record_updated=record_updated,
            revoked=any(marker in title.lower() for marker in REVOKED_MARKERS),
        )

    def search(self, *, title: str, page_size: int = 50) -> LegislationFeed:
        payload = self._fetch({"title": title, "results-count": min(page_size, 100)})
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError:
            return LegislationFeed(query=title, skip_reasons={"ATOM_PARSE_FAILED": 1})

        entries = root.findall("a:entry", _NS)
        items: list[LegislationItem] = []
        skips: dict[str, int] = {}
        for entry in entries:
            item = self._item(entry)
            if item is None:
                skips["NOT_AN_INSTRUMENT"] = skips.get("NOT_AN_INSTRUMENT", 0) + 1
                continue
            if not item.is_dated:
                skips["NO_ENACTMENT_YEAR"] = skips.get("NO_ENACTMENT_YEAR", 0) + 1
                continue
            items.append(item)

        return LegislationFeed(
            query=title, items=items, entries_seen=len(entries), skip_reasons=skips
        )
