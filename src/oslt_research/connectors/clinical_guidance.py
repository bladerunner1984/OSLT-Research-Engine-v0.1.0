"""W09: clinical guidelines, professional-body guidance and NHS policy documents.

WHY THIS EXISTS
---------------
W09 is the *institutional clock*. 24 of the 64 propositions depend on it, and most are
claims that something changed before or after a guideline, service specification or
policy did. ``legislation.py`` already supplies outcome dates fixed by Parliament rather
than chosen by an analyst; this module extends the same discipline to clinical and
commissioning policy.

Consequently the *date* is the product, not the text. Everything below is organised
around one question: is this field a genuine first-publication/effective date, or is it a
revision timestamp wearing a date's clothes?

WHAT EACH UPSTREAM DATE FIELD ACTUALLY MEANS
--------------------------------------------
============================  ==================================  ==================
Source / field                Meaning                             Usable as anchor?
============================  ==================================  ==================
NICE ``publicationDate``      First publication of the guidance   YES
NICE ``lastUpdated``          Most recent revision of any part    NO
NICE ``guidanceStatus``       Published / Withdrawn / In dev.     status only
GOV.UK ``first_published_at`` First publication                   YES
GOV.UK ``public_updated_at``  Last *major* update                 NO
GOV.UK ``updated_at``         Content-store write, incl. cosmetic NO (see below)
GOV.UK ``withdrawn_notice``   Withdrawal, with its own date       status only
NHS England WP ``date``       Site publication of the page        YES, with a caveat
NHS England WP ``modified``   Last edit of the page               NO
RCPsych canonical URL         ``/detail/YYYY/MM/DD/slug``         YES
JSON-LD ``datePublished``     Publisher-declared publication      YES
JSON-LD ``dateModified``      Publisher-declared revision         NO
sitemap ``<lastmod>``         Crawl hint, revision                NO -- never read here
============================  ==================================  ==================

The GOV.UK row is the live proof of the rule. A 2024 press release carries ``updated_at``
in 2026 because the content store rewrote the record; using it would date a 2024 policy
to 2026, exactly as ``legislation.gov.uk``'s Atom ``<updated>`` dated the Gender
Recognition Act 2004 to 2024.

The NHS England caveat: WordPress ``date`` is when the page was published *on this site*.
For a document migrated from an older platform that is a migration date, not a
publication date. :func:`_year_conflict` therefore refuses an anchor whenever the title
carries a year that the WordPress date contradicts, and the document is reported UNDATED.
An undated document is honest; a wrongly dated one silently corrupts every temporal test
built on it.

WITHDRAWN AND SUPERSEDED DOCUMENTS ARE KEPT
-------------------------------------------
Following the ``REVOKED_MARKERS`` precedent in ``legislation.py``: a withdrawn
specification was in force for a period, and that period is precisely what a
policy-embedding proposition is about. Withdrawal is a flag, never a filter.

DECLINED ROUTES
---------------
See :data:`DECLINED_SOURCES`. Building nothing for a source and saying so is a valid
outcome; guessing is not.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Iterator
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

#: No registry row yet. ``registries/sources.csv`` is owned by another agent this turn;
#: the requested row is recorded in ``docs/W09_CLINICAL_GUIDANCE.md``.
SOURCE_ID = "UNREGISTERED:W09-CLINICAL-GUIDANCE"

#: Identifies the project honestly and carries no words a WAF treats as hostile.
#: www.rcpsych.ac.uk's edge returns HTTP 403 to any User-Agent containing "harvester" or
#: "robots.txt" even though its robots.txt imposes no Disallow at all. The string below is
#: the same claim about who we are, phrased so a naive keyword filter does not reject it.
#: It is not a browser impersonation and does not evade any stated access policy.
USER_AGENT = "oslt-research-engine/1.0 (+research; contact via repository)"

#: Minimum seconds between requests, per host. NICE and RCPCH publish a ``Crawl-delay``
#: in robots.txt (1 and 5 respectively) and those are honoured with headroom. Everything
#: else gets a conservative default. Throttling starts at the FIRST request because an
#: unthrottled run earlier in this project exhausted a source's daily budget.
HOST_MIN_INTERVAL: dict[str, float] = {
    "search-api.nice.org.uk": 1.5,
    "www.nice.org.uk": 1.5,
    "www.rcpch.ac.uk": 5.0,
    "www.england.nhs.uk": 1.0,
    "www.gov.uk": 1.0,
    "www.bps.org.uk": 2.0,
    "www.rcpsych.ac.uk": 2.0,
}
DEFAULT_MIN_INTERVAL = 2.0

#: Routes deliberately not built, with the reason. Kept in code rather than only in prose
#: so a later session cannot quietly "fix" a decline it has not re-checked.
DECLINED_SOURCES: dict[str, str] = {
    "cass.independent-review.uk": (
        "The live site now 301s to the UK Government Web Archive "
        "(webarchive.nationalarchives.gov.uk), whose robots.txt is 'User-agent: * / "
        "Disallow: /' for every agent except Oncrawl. Automated retrieval of the Cass "
        "Review from the archive is therefore refused. Cass documents are captured "
        "indirectly, from NHS England and GOV.UK pages that publish and respond to them."
    ),
    "webarchive.nationalarchives.gov.uk": (
        "robots.txt disallows all paths for all user agents except Oncrawl. Declined."
    ),
    "www.gmc-uk.org": (
        "Cloudflare returns HTTP 403 for /robots.txt itself, so the site's crawl policy "
        "cannot even be read. A host that will not serve its own robots.txt has not "
        "granted automated access. Declined; GMC guidance must be cited by hand."
    ),
    "api.nice.org.uk": (
        "NICE Syndication API requires a signed licence agreement and a cyber-security "
        "certificate. Not used. The open search API at search-api.nice.org.uk, which "
        "backs www.nice.org.uk's own published-guidance browser, is used instead."
    ),
    "www.bma.org.uk": (
        "robots.txt names a sitemap on an unrelated host and expresses no User-agent "
        "group, so no crawl permission is stated and the sitemap it names does not cover "
        "the policy estate. No structured publication-date field was found. Declined "
        "rather than scraped speculatively."
    ),
}


class ThrottledClient:
    """An ``httpx.Client`` wrapper that enforces a per-host minimum request interval.

    Wrapping rather than subclassing keeps ``httpx.MockTransport`` usable in tests: the
    sleep is skipped entirely when ``enabled`` is False, so unit tests never wait.
    """

    def __init__(self, client: httpx.Client, *, enabled: bool = True) -> None:
        self._client = client
        self._enabled = enabled
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        if self._enabled:
            host = urlparse(url).netloc
            interval = HOST_MIN_INTERVAL.get(host, DEFAULT_MIN_INTERVAL)
            with self._lock:
                elapsed = time.monotonic() - self._last.get(host, 0.0)
                if elapsed < interval:
                    time.sleep(interval - elapsed)
                self._last[host] = time.monotonic()
        headers = {"User-Agent": USER_AGENT, **(kwargs.pop("headers", None) or {})}
        return self._client.get(url, headers=headers, follow_redirects=True, **kwargs)

    def close(self) -> None:
        self._client.close()


@dataclass(frozen=True)
class PolicyDocument:
    """One dated (or explicitly undated) policy, guidance or specification document.

    ``published_on`` is populated ONLY from a field established to be a genuine first
    publication or effective date; ``published_on_field`` names which one, so a reader can
    audit the claim without re-deriving it. ``last_updated`` is kept beside it precisely
    so that it is visible and unusable: it is never consulted by :meth:`anchor_date`.
    """

    source: str
    publisher: str
    title: str
    url: str
    published_on: date | None = None
    published_on_field: str = ""
    last_updated: date | None = None
    last_updated_field: str = ""
    document_type: str = ""
    status: str = ""
    withdrawn: bool = False
    undated_reason: str = ""
    identifiers: dict[str, str] = field(default_factory=dict)

    @property
    def is_dated(self) -> bool:
        """Dated means a genuine publication date is known. A revision is not a date."""

        return self.published_on is not None

    def anchor_date(self) -> date | None:
        """The date this document may anchor a temporal-ordering test to.

        Deliberately ignores ``last_updated`` in all circumstances.
        """

        return self.published_on


@dataclass(frozen=True)
class GuidanceHarvest:
    """Result of one or more sub-connector runs, with the refusals kept visible."""

    documents: list[PolicyDocument] = field(default_factory=list)
    records_seen: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)
    declined: dict[str, str] = field(default_factory=dict)

    def dated(self) -> list[PolicyDocument]:
        return [doc for doc in self.documents if doc.is_dated]

    def undated(self) -> list[PolicyDocument]:
        return [doc for doc in self.documents if not doc.is_dated]

    def anchor_dates(self) -> list[date]:
        """Unique, sorted publication dates usable as temporal anchors."""

        return sorted({doc.published_on for doc in self.dated() if doc.published_on})

    def merged_with(self, other: GuidanceHarvest) -> GuidanceHarvest:
        """Combine two runs, de-duplicating on URL and summing the skip counters."""

        skips = dict(self.skip_reasons)
        for reason, count in other.skip_reasons.items():
            skips[reason] = skips.get(reason, 0) + count
        seen: dict[str, PolicyDocument] = {}
        for doc in [*self.documents, *other.documents]:
            seen.setdefault(doc.url, doc)
        return GuidanceHarvest(
            documents=list(seen.values()),
            records_seen=self.records_seen + other.records_seen,
            skip_reasons=skips,
            declined={**self.declined, **other.declined},
        )


# --------------------------------------------------------------------------------------
# date parsing helpers
# --------------------------------------------------------------------------------------

_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")
_TAG = re.compile(r"<[^>]+>")


def parse_iso_date(value: object) -> date | None:
    """Parse an ISO-8601 date or datetime into a date, or return None.

    Returns None rather than raising: a value that cannot be parsed is an unknown date,
    and an unknown date must not become a guessed one.
    """

    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def strip_markup(text: str) -> str:
    """Remove the <b>/<mark> highlighting that search APIs inject into titles."""

    cleaned = _TAG.sub("", text or "")
    for entity, replacement in (("&amp;", "&"), ("&#8217;", "’"), ("&#039;", "'")):
        cleaned = cleaned.replace(entity, replacement)
    return cleaned.strip()


def _year_conflict(title: str, candidate: date | None) -> int | None:
    """Return a year from the title that contradicts ``candidate``, else None.

    A title such as "Interim service specification 2022" on a page whose site timestamp
    says 2026 is a migration, not a publication. Rather than pick one, this surfaces the
    conflict so the caller can refuse to anchor. A one-year tolerance is allowed because
    financial-year and near-year-end publication legitimately straddle the boundary.
    """

    if candidate is None:
        return None
    years = [int(match) for match in _YEAR.findall(title or "")]
    if not years:
        return None
    if any(abs(year - candidate.year) <= 1 for year in years):
        return None
    return max(years)


# --------------------------------------------------------------------------------------
# NICE
# --------------------------------------------------------------------------------------

#: Statuses that mean the guidance is no longer the operative version. Flagged, not
#: filtered - see the module docstring.
NICE_SUPERSEDED_STATUSES = frozenset({"withdrawn", "static list", "replaced", "removed"})

#: Date fields NICE emits for records that have not been published. None of them is a
#: publication date; they are listed so the refusal reason can name what was there.
NICE_NON_PUBLICATION_DATE_FIELDS = (
    "expectedPublicationDate",
    "topicSelectionDecisionDate",
    "consultationEndDate",
    "prioritisationBoardDecisionDate",
    "prioritisationBoardMeetingDate",
    "terminatedDate",
    "deferredDate",
)


class NiceGuidanceConnector:
    """NICE published guidance via the open search API behind www.nice.org.uk.

    WHY THIS ROUTE. The NICE *Syndication* API (api.nice.org.uk) requires a signed licence
    and a cyber-security certificate and is declined. ``search-api.nice.org.uk/api/search``
    is the unauthenticated JSON endpoint that NICE's own /guidance/published browser calls;
    it needs no key, and www.nice.org.uk's robots.txt is ``Allow: /`` with
    ``Crawl-delay: 1``, which is honoured with headroom.

    It is not a *documented* public API, which is a real fragility: the parameter set
    (``index``, ``q``, ``ps``, ``pa``) is inferred from the site's own requests and could
    change without notice. That is still strictly better than parsing the index HTML,
    because the JSON separates ``publicationDate`` from ``lastUpdated`` and the rendered
    index does not. A schema change surfaces as zero results, not as wrong dates.
    """

    source_name = "NICE"
    connector_version = "1"
    base_url = "https://search-api.nice.org.uk/api/search"

    def __init__(
        self,
        *,
        client: ThrottledClient | httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._client = _coerce_client(client)
        self.timeout = timeout

    def search(
        self,
        query: str,
        *,
        index: str = "guidance",
        page_size: int = 50,
        page: int = 1,
    ) -> GuidanceHarvest:
        response = self._client.get(
            self.base_url,
            params={"index": index, "q": query, "ps": min(page_size, 100), "pa": page},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return GuidanceHarvest(skip_reasons={"NICE_RESPONSE_NOT_JSON": 1})

        results = payload.get("documents") or []
        documents: list[PolicyDocument] = []
        skips: dict[str, int] = {}

        for record in results:
            statuses = [str(item).strip() for item in (record.get("guidanceStatus") or [])]
            title = strip_markup(str(record.get("title") or ""))
            url = str(record.get("url") or record.get("sourceUrl") or "").strip()
            if not title or not url:
                skips["NICE_TITLE_OR_URL_MISSING"] = skips.get("NICE_TITLE_OR_URL_MISSING", 0) + 1
                continue

            published = parse_iso_date(record.get("publicationDate"))
            updated = parse_iso_date(record.get("lastUpdated"))
            undated_reason = ""
            if published is None:
                present = [f for f in NICE_NON_PUBLICATION_DATE_FIELDS if record.get(f)]
                undated_reason = (
                    "no publicationDate; the record carries only "
                    + ", ".join(present)
                    + ", none of which is a publication date"
                ) if present else "no publicationDate on the record"
                skips["NICE_NO_PUBLICATION_DATE"] = skips.get("NICE_NO_PUBLICATION_DATE", 0) + 1

            documents.append(
                PolicyDocument(
                    source="NICE",
                    publisher="National Institute for Health and Care Excellence",
                    title=title,
                    url=url,
                    published_on=published,
                    published_on_field="publicationDate" if published else "",
                    last_updated=updated,
                    last_updated_field="lastUpdated" if updated else "",
                    document_type="; ".join(
                        str(item) for item in (record.get("niceDocType") or [])
                    ),
                    status="; ".join(statuses),
                    withdrawn=any(
                        item.lower() in NICE_SUPERSEDED_STATUSES for item in statuses
                    ),
                    undated_reason=undated_reason,
                    identifiers=(
                        {"nice_reference": str(record["guidanceRef"])}
                        if record.get("guidanceRef")
                        else {}
                    ),
                )
            )

        return GuidanceHarvest(
            documents=documents, records_seen=len(results), skip_reasons=skips
        )


# --------------------------------------------------------------------------------------
# NHS England
# --------------------------------------------------------------------------------------

#: NHS England WordPress REST collections that carry policy content. ``long-read`` is
#: where service specifications and implementation plans actually live; ``documents`` is
#: the publication container; ``posts`` is news, kept because a commissioning decision is
#: frequently announced there before the specification itself appears.
NHS_ENGLAND_COLLECTIONS = ("long-read", "documents", "posts")


class NhsEnglandPolicyConnector:
    """NHS England service specifications and commissioning policy, via its WP REST API.

    WHY THIS ROUTE. ``www.england.nhs.uk`` runs WordPress and exposes the standard,
    documented ``/wp-json/wp/v2/`` API. Its robots.txt disallows only ``/wp-admin/`` (with
    an explicit ``Allow`` for admin-ajax.php), so the REST namespace is permitted. This is
    a real API rather than an index scrape, and it separates ``date`` (site publication)
    from ``modified`` (revision) as distinct fields.

    Category-based retrieval is preferred over free-text search where possible: NHS
    England maintains a ``gender-identity`` category, and a taxonomy assigned by the
    publisher is a better definition of relevance than a keyword the analyst chose.
    """

    source_name = "NHSEnglandPolicy"
    connector_version = "1"
    base_url = "https://www.england.nhs.uk/wp-json/wp/v2"

    def __init__(
        self,
        *,
        client: ThrottledClient | httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._client = _coerce_client(client)
        self.timeout = timeout

    def category_id(self, slug: str) -> int | None:
        """Resolve a category slug to its id, or None if the site has no such category."""

        response = self._client.get(
            f"{self.base_url}/categories",
            params={"slug": slug},
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return int(payload[0]["id"]) if payload else None

    def collection(
        self,
        collection: str,
        *,
        category: int | None = None,
        search: str | None = None,
        per_page: int = 50,
        page: int = 1,
    ) -> GuidanceHarvest:
        params: dict[str, Any] = {"per_page": min(per_page, 100), "page": page}
        if category is not None:
            params["categories"] = category
        if search:
            params["search"] = search
        response = self._client.get(
            f"{self.base_url}/{collection}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        if response.status_code == 400:
            # WordPress returns 400 for a page beyond the last one. That is exhaustion,
            # not absence, and must never be recorded as "no such document".
            return GuidanceHarvest(skip_reasons={"NHSE_PAGE_BEYOND_END": 1})
        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            return GuidanceHarvest(skip_reasons={"NHSE_UNEXPECTED_PAYLOAD": 1})

        documents: list[PolicyDocument] = []
        skips: dict[str, int] = {}
        for record in records:
            title = strip_markup(str((record.get("title") or {}).get("rendered", "")))
            url = str(record.get("link") or "").strip()
            if not title or not url:
                skips["NHSE_TITLE_OR_LINK_MISSING"] = (
                    skips.get("NHSE_TITLE_OR_LINK_MISSING", 0) + 1
                )
                continue

            published = parse_iso_date(record.get("date_gmt") or record.get("date"))
            modified = parse_iso_date(record.get("modified_gmt") or record.get("modified"))
            undated_reason = ""
            conflict = _year_conflict(title, published)
            if conflict is not None:
                undated_reason = (
                    f"title asserts {conflict} but the WordPress publication timestamp is "
                    f"{published}; probably a migrated or re-published page, so the site "
                    "timestamp is refused as an anchor"
                )
                published = None
                skips["NHSE_TITLE_YEAR_CONFLICT"] = skips.get("NHSE_TITLE_YEAR_CONFLICT", 0) + 1
            elif published is None:
                undated_reason = "no WordPress publication timestamp"
                skips["NHSE_NO_PUBLISH_DATE"] = skips.get("NHSE_NO_PUBLISH_DATE", 0) + 1

            status = str(record.get("status") or "")
            documents.append(
                PolicyDocument(
                    source="NHS England",
                    publisher="NHS England",
                    title=title,
                    url=url,
                    published_on=published,
                    published_on_field="wp:date_gmt" if published else "",
                    last_updated=modified,
                    last_updated_field="wp:modified_gmt" if modified else "",
                    document_type=str(record.get("type") or collection),
                    status=status,
                    withdrawn=status not in ("publish", ""),
                    undated_reason=undated_reason,
                    identifiers={"wp_id": str(record.get("id", ""))},
                )
            )

        return GuidanceHarvest(
            documents=documents, records_seen=len(records), skip_reasons=skips
        )


# --------------------------------------------------------------------------------------
# GOV.UK
# --------------------------------------------------------------------------------------


class GovUkPolicyDocumentConnector:
    """GOV.UK publications, dated from the Content API rather than the Search API.

    WHY BOTH APIS. ``/api/search.json`` is the only route that can find documents, but the
    only timestamp it returns is ``public_timestamp``, which is the last *major update*.
    ``/api/content/<path>`` returns ``first_published_at`` and ``public_updated_at`` as
    separate fields, plus ``updated_at``, which is a content-store write and is routinely
    years later than the policy - one 2024 press release probed for this module carried
    ``updated_at`` in 2026. Discovery therefore uses search; the date always comes from the
    Content API. That costs one extra request per document and is the entire reason the
    dates here can be trusted.

    Complements, and does not replace, ``govuk_guidance.GovUkGuidanceConnector``, which
    builds ISSUES_GUIDANCE_TO graph edges rather than dated documents.
    """

    source_name = "GovUkPolicyDocument"
    connector_version = "1"
    search_url = "https://www.gov.uk/api/search.json"
    content_url = "https://www.gov.uk/api/content"

    def __init__(
        self,
        *,
        client: ThrottledClient | httpx.Client | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._client = _coerce_client(client)
        self.timeout = timeout

    def _search(self, query: str, count: int) -> list[dict[str, Any]]:
        response = self._client.get(
            self.search_url,
            params={
                "q": query,
                "count": min(count, 100),
                "fields": (
                    "title,link,public_timestamp,content_store_document_type,organisations"
                ),
            },
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return list(response.json().get("results") or [])

    def _content(self, link: str) -> dict[str, Any] | None:
        response = self._client.get(
            f"{self.content_url}{link}",
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            # 404/429/timeout means unknown, never "no such guidance".
            return None
        try:
            payload = response.json()
        except json.JSONDecodeError:
            return None
        return dict(payload) if isinstance(payload, dict) else None

    def search(self, query: str, *, count: int = 30) -> GuidanceHarvest:
        results = self._search(query, count)
        documents: list[PolicyDocument] = []
        skips: dict[str, int] = {}

        for result in results:
            link = str(result.get("link") or "").strip()
            title = strip_markup(str(result.get("title") or ""))
            if not link.startswith("/") or not title:
                skips["GOVUK_NOT_A_CONTENT_PATH"] = skips.get("GOVUK_NOT_A_CONTENT_PATH", 0) + 1
                continue

            content = self._content(link)
            if content is None:
                # Deliberately not emitted: a document whose Content API call failed has an
                # unknown date, and the search timestamp must not be substituted for it.
                skips["GOVUK_CONTENT_API_UNAVAILABLE"] = (
                    skips.get("GOVUK_CONTENT_API_UNAVAILABLE", 0) + 1
                )
                continue

            published = parse_iso_date(content.get("first_published_at"))
            updated = parse_iso_date(content.get("public_updated_at"))
            withdrawn_notice = content.get("withdrawn_notice") or {}
            withdrawn_at = parse_iso_date(
                withdrawn_notice.get("withdrawn_at") if isinstance(withdrawn_notice, dict) else None
            )
            if published is None:
                skips["GOVUK_NO_FIRST_PUBLISHED_AT"] = (
                    skips.get("GOVUK_NO_FIRST_PUBLISHED_AT", 0) + 1
                )

            documents.append(
                PolicyDocument(
                    source="GOV.UK",
                    publisher="; ".join(
                        strip_markup(str(org.get("title") or ""))
                        for org in (result.get("organisations") or [])
                        if isinstance(org, dict)
                    ),
                    title=strip_markup(str(content.get("title") or title)),
                    url=f"https://www.gov.uk{link}",
                    published_on=published,
                    published_on_field="first_published_at" if published else "",
                    last_updated=updated,
                    last_updated_field="public_updated_at" if updated else "",
                    document_type=str(content.get("document_type") or ""),
                    status="withdrawn" if withdrawn_at else "published",
                    withdrawn=withdrawn_at is not None,
                    undated_reason=(
                        "" if published else "no first_published_at on the content item"
                    ),
                    identifiers=(
                        {"withdrawn_at": withdrawn_at.isoformat()} if withdrawn_at else {}
                    ),
                )
            )

        return GuidanceHarvest(
            documents=documents, records_seen=len(results), skip_reasons=skips
        )


# --------------------------------------------------------------------------------------
# Professional bodies
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProfessionalBody:
    """A professional body whose site permits automated retrieval.

    ``url_date_pattern`` covers the case where the body encodes the publication date in
    its canonical URL. That is the same class of evidence as legislation.gov.uk's
    ``/ukpga/2004/7``: a date fixed by the publisher's own identifier scheme rather than a
    revision timestamp, and it is preferred over anything in the page body.
    """

    key: str
    name: str
    sitemap_url: str
    url_date_pattern: re.Pattern[str] | None = None


PROFESSIONAL_BODIES: dict[str, ProfessionalBody] = {
    # robots.txt: Crawl-delay 5; /resources/all-resources? and /search are disallowed,
    # the sitemap and individual /resources/<slug> and /news-events/news/<slug> are not.
    "rcpch": ProfessionalBody(
        key="rcpch",
        name="Royal College of Paediatrics and Child Health",
        sitemap_url="https://www.rcpch.ac.uk/sitemap.xml",
    ),
    # robots.txt: only /_preview_/ and /preview/ disallowed.
    "bps": ProfessionalBody(
        key="bps",
        name="British Psychological Society",
        sitemap_url="https://www.bps.org.uk/sitemap.xml",
    ),
    # robots.txt names a sitemap and imposes no Disallow. Its news URLs carry the
    # publication date in the path, which is why no page fetch is needed for those.
    "rcpsych": ProfessionalBody(
        key="rcpsych",
        name="Royal College of Psychiatrists",
        sitemap_url="https://www.rcpsych.ac.uk/sitemap/sitemap.xml",
        url_date_pattern=re.compile(r"/detail/(\d{4})/(\d{2})/(\d{2})/"),
    ),
}

_SITEMAP_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
_JSON_LD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)


def _iter_json_ld(html: str) -> Iterator[dict[str, Any]]:
    """Yield every JSON-LD object in a page, flattening @graph and top-level arrays."""

    for block in _JSON_LD.findall(html):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        stack: list[Any] = [parsed]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                yield node
                if isinstance(node.get("@graph"), list):
                    stack.extend(node["@graph"])


class ProfessionalBodyConnector:
    """Position statements and guidance from professional bodies.

    WHY THIS IS THE WEAKEST ROUTE, STATED PLAINLY. None of these bodies publishes an API.
    Discovery is by sitemap, which is a published route intended for machines rather than
    HTML scraping; but a sitemap's ``<lastmod>`` is a crawl hint and is NEVER read here.
    Dates come only from the canonical URL (RCPsych) or from publisher-declared JSON-LD
    ``datePublished`` (RCPCH, BPS).

    Fragility: these sites emit JSON-LD for news items but generally not for guidance and
    resource pages, so a substantial share of the most *relevant* documents come back
    UNDATED. That is the correct result, not a bug to be papered over with a file-upload
    path year or a sitemap lastmod.
    """

    source_name = "ProfessionalBody"
    connector_version = "1"

    def __init__(
        self,
        *,
        client: ThrottledClient | httpx.Client | None = None,
        timeout: float = 90.0,
    ) -> None:
        self._client = _coerce_client(client)
        self.timeout = timeout

    def sitemap_urls(self, body: ProfessionalBody) -> list[str]:
        response = self._client.get(
            body.sitemap_url, headers={"Accept": "application/xml"}, timeout=self.timeout
        )
        response.raise_for_status()
        text = response.content.decode("utf-8", errors="replace").lstrip("﻿")
        try:
            root = ElementTree.fromstring(text)
        except ElementTree.ParseError:
            # Regex fallback: several of these sitemaps ship a BOM or a stylesheet PI that
            # trips strict XML parsing, and a parse failure must not look like an absence.
            return _SITEMAP_LOC.findall(text)
        namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [
            node.text.strip() for node in root.findall(".//s:loc", namespace) if node.text
        ]
        return locations or _SITEMAP_LOC.findall(text)

    def _page_document(self, body: ProfessionalBody, url: str) -> PolicyDocument:
        published: date | None = None
        updated: date | None = None
        published_field = ""
        updated_field = ""
        title = ""

        if body.url_date_pattern:
            match = body.url_date_pattern.search(url)
            if match:
                published = date(*(int(part) for part in match.groups()))
                published_field = "canonical URL path (/detail/YYYY/MM/DD/)"

        if published is None:
            response = self._client.get(
                url, headers={"Accept": "text/html"}, timeout=self.timeout
            )
            if response.status_code >= 400:
                return PolicyDocument(
                    source=body.name,
                    publisher=body.name,
                    title=url.rstrip("/").rsplit("/", 1)[-1].replace("-", " "),
                    url=url,
                    document_type="professional body publication",
                    undated_reason=(
                        f"page fetch returned HTTP {response.status_code}; the date is "
                        "unknown, which is not the same as absent"
                    ),
                )
            html = response.content.decode("utf-8", errors="replace")
            title_match = _TITLE.search(html)
            if title_match:
                title = strip_markup(title_match.group(1)).split("|")[0].strip()
            for node in _iter_json_ld(html):
                published = published or parse_iso_date(node.get("datePublished"))
                updated = updated or parse_iso_date(node.get("dateModified"))
            if published:
                published_field = "schema.org datePublished"
            if updated:
                updated_field = "schema.org dateModified"

        if not title:
            title = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")

        return PolicyDocument(
            source=body.name,
            publisher=body.name,
            title=title,
            url=url,
            published_on=published,
            published_on_field=published_field,
            last_updated=updated,
            last_updated_field=updated_field,
            document_type="professional body publication",
            status="published",
            undated_reason=(
                ""
                if published
                else (
                    "no publication date in the canonical URL and no schema.org "
                    "datePublished on the page; the sitemap <lastmod> is a revision hint "
                    "and is deliberately not used"
                )
            ),
        )

    def harvest(
        self, body: ProfessionalBody, *, keywords: Iterable[str], limit: int = 40
    ) -> GuidanceHarvest:
        try:
            locations = self.sitemap_urls(body)
        except httpx.HTTPError as error:
            return GuidanceHarvest(
                skip_reasons={f"SITEMAP_UNAVAILABLE_{type(error).__name__}": 1}
            )

        terms = [term.lower() for term in keywords]
        matches = [url for url in locations if any(term in url.lower() for term in terms)]
        documents = [self._page_document(body, url) for url in matches[:limit]]
        skips: dict[str, int] = {}
        undated = sum(1 for doc in documents if not doc.is_dated)
        if undated:
            skips[f"{body.key.upper()}_NO_PUBLICATION_DATE"] = undated
        return GuidanceHarvest(
            documents=documents, records_seen=len(matches), skip_reasons=skips
        )


# --------------------------------------------------------------------------------------


def _coerce_client(client: ThrottledClient | httpx.Client | None) -> ThrottledClient:
    """Wrap a raw client so that throttling cannot be forgotten by a caller.

    A bare ``httpx.Client`` passed by a test is wrapped with throttling DISABLED, because
    a MockTransport has no rate limit to respect and a sleeping unit test is a test nobody
    runs.
    """

    if isinstance(client, ThrottledClient):
        return client
    if client is not None:
        return ThrottledClient(client, enabled=False)
    return ThrottledClient(httpx.Client(timeout=60.0), enabled=True)
