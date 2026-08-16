"""Openly published NHS England / NHS England Digital aggregate data.

Workstream W02 (NHS referrals, diagnoses and service pathways) is required by 40 of the
64 propositions and is empty, because individual-level NHS data sits behind access
processes measured in months. The propositions are claims about *rates*, and NHS England
publishes a great deal of aggregate, keyless, licence-free material that speaks to rates.
This module is the open-route half of W02. It deliberately does two narrow things and
refuses a third.

What it does
------------

1. **Organisation reference data** from the ODS ORD API
   (``directory.spineservices.nhs.uk/ORD/2-0-0``). Verified live: keyless, JSON,
   ``Access-Control-Allow-Origin: *``, real ``X-Total-Count`` / ``Next-Page`` pagination,
   and the host serves no ``robots.txt`` at all. This is what resolves an ODS code such as
   ``RW1`` into a named trust with its roles, its relationships and its *typed* dates, so
   the institutional ontology can carry provider identity rather than a bare string.

2. **Discovery of NHS England statistics publication files** on
   ``www.england.nhs.uk/statistics/...``. Its ``robots.txt`` disallows only ``/wp-admin/``,
   so retrieval is permitted. But see :class:`NhsEnglandStatisticsIndex` - the only route
   is scraping a work-area index page for arbitrary WordPress upload URLs, which is
   fragile, so this module returns *file references*, never numbers.

What it refuses
---------------

3. It will not fetch from a host whose published policy forbids automated access. The
   Mental Health Services Data Set monthly files - the single most relevant open source
   for W02, and genuinely open in the sense that no login or application is needed - are
   all served from ``files.digital.nhs.uk``, whose ``robots.txt`` has read
   ``User-agent: * / Disallow: /`` since 2018. That is a blanket refusal of automated
   retrieval and it is honoured here: see :data:`DECLINED_ROUTES` and :func:`guard_route`,
   which make the refusal executable rather than a comment.

The four hazards this module is shaped around
---------------------------------------------

* **A hole is never a zero.** NHS publications suppress small numbers, and they do it with
  a zoo of markers (``*``, ``.``, ``..``, ``c``, ``z``, ``w``, blank). Every one means
  MISSING. Read as zero, a suppressed cell manufactures exactly the trough these
  propositions test for. :func:`parse_cell` maps them all to ``None`` and
  :func:`build_series` refuses to emit a series containing one.
* **Overlapping aggregates.** NHS tables carry England alongside regions alongside
  providers, and "All ages" alongside age bands, in the same file. :func:`build_series`
  pins one stratum and raises unless the selection is exactly one row per period. It never
  sums.
* **Date-looking fields usually mean something else.** ODS ``LastChangeDate`` is when the
  *record* was amended, not when the organisation started; ``Date[Type=Operational]`` and
  ``Date[Type=Legal]`` are two further different things; and NHSE period labels mix
  financial years ("2023/24"), quarters ("Q4 2022-23") and publication months. See
  :class:`NhsPeriod` and :class:`OdsOrganisation`, which preserve labels verbatim and
  refuse to coerce a financial year into a calendar one.
* **A query parameter may be silently discarded.** ODS filters were verified live to be
  honoured (``Name=tavistock`` gives ``X-Total-Count: 69`` against 305,791 unfiltered).
  :meth:`NhsOdsConnector.verify_filter_honoured` re-runs that check on demand so the
  assumption is testable rather than remembered.

Throttling is on from the first request.
"""

from __future__ import annotations

import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from oslt_research.governance.mechanism_simulation import ObservedSeries

#: DS068 in the source register (added 2026-08). The row states the two limits that
#: matter: ODS supplies ORGANISATION REFERENCE DATA, not clinical activity, and the
#: statistics route INDEXES files without fetching them, because files.digital.nhs.uk
#: disallows automated retrieval.
SOURCE_ID = "DS068"

#: The ODS ORD API. Version is pinned in the path: 2-0-0 is the current published major.
ODS_BASE_URL = "https://directory.spineservices.nhs.uk/ORD/2-0-0"

#: NHS England statistics live under one WordPress site with per-topic "work areas".
NHSE_STATISTICS_BASE = "https://www.england.nhs.uk/statistics/statistical-work-areas"

#: Host that serves NHS England statistics attachments. Its robots.txt disallows only
#: /wp-admin/, so these are retrievable.
NHSE_HOST = "www.england.nhs.uk"

#: ODS rejects Limit above this with HTTP 406, so it is enforced locally instead of
#: burning a request to discover it.
ODS_MAX_LIMIT = 1000

#: ODS primary role ids that matter for provider identity in W02.
ODS_ROLE_NHS_TRUST = "RO197"
ODS_ROLE_CCG = "RO98"

#: Total organisations in ODS with no filter applied, observed 2026-08-15. Used only as a
#: sanity anchor when checking that a filter was actually applied; it drifts, so it is
#: never asserted as equality.
ODS_UNFILTERED_TOTAL_ORDER_OF_MAGNITUDE = 300_000


class NhsDataError(RuntimeError):
    """Raised when NHS data cannot be trusted to mean what it appears to mean."""


class RouteDeclinedError(NhsDataError):
    """Raised when a host's own published policy forbids the fetch being attempted."""


# --------------------------------------------------------------------------------------
# Declined routes: published policy, made executable
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class DeclinedRoute:
    """A real, open, relevant NHS data route that this project will not automate.

    Recorded as data rather than prose so that W02's thinness is auditable: a reader can
    see that the gap is a policy decision with a citation, not an oversight.
    """

    host: str
    path_prefix: str
    offers: str
    policy: str
    policy_url: str
    checked_on: str

    def matches(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc.lower() != self.host:
            return False
        return (parsed.path or "/").startswith(self.path_prefix)


#: Verified by fetching each robots.txt on 2026-08-15.
DECLINED_ROUTES: tuple[DeclinedRoute, ...] = (
    DeclinedRoute(
        host="files.digital.nhs.uk",
        path_prefix="/",
        offers=(
            "Mental Health Services Data Set monthly statistics: CSV and ZIP bulk files "
            "including a full Apr-2016-to-date time series, plus data-quality coverage "
            "CSVs. No login, no application, no key. The most relevant open source for "
            "W02 referrals and service contacts."
        ),
        policy="User-agent: *\nDisallow: /",
        policy_url="https://files.digital.nhs.uk/robots.txt",
        checked_on="2026-08-15",
    ),
    DeclinedRoute(
        host="ckan.publishing.service.gov.uk",
        path_prefix="/api/",
        offers="data.gov.uk CKAN package_search, including NHS dataset metadata.",
        policy="User-agent: *\nDisallow: /api/\nCrawl-Delay: 10",
        policy_url="https://ckan.publishing.service.gov.uk/robots.txt",
        checked_on="2026-08-15",
    ),
    DeclinedRoute(
        host="data.england.nhs.uk",
        path_prefix="/api/",
        offers=(
            "NHS England public data gateway API. The gateway's HTML pages are an index "
            "that links back out to digital.nhs.uk publications; it hosts no data files "
            "of its own, so declining the API costs nothing here."
        ),
        policy="User-Agent: *\nAllow: /\nDisallow: /api/",
        policy_url="https://data.england.nhs.uk/robots.txt",
        checked_on="2026-08-15",
    ),
)


def declined_route_for(url: str) -> DeclinedRoute | None:
    """Return the policy that forbids fetching ``url``, or ``None`` if it is permitted."""

    for route in DECLINED_ROUTES:
        if route.matches(url):
            return route
    return None


def guard_route(url: str) -> str:
    """Return ``url`` unchanged, or raise because its host forbids automated access.

    Every fetch in this module goes through here. The point is that no future edit can
    quietly point this connector at ``files.digital.nhs.uk`` by changing a base URL: the
    refusal lives on the path the request actually takes, not in a docstring.
    """

    route = declined_route_for(url)
    if route is not None:
        raise RouteDeclinedError(
            f"{route.host} forbids automated retrieval in its own published policy "
            f"({route.policy_url}, checked {route.checked_on}):\n{route.policy}\n"
            f"What is being declined: {route.offers}\n"
            "This is not a technical block to work around. Obtain the files by the route "
            "the publisher intends, or record the gap."
        )
    return url


# --------------------------------------------------------------------------------------
# Suppression: a hole is never a zero
# --------------------------------------------------------------------------------------

#: Markers NHS publications use for "there is no number here". They mean different things
#: to the publisher - disclosure control, not applicable, not available, low data quality -
#: but they share the only property that matters downstream: none of them is a quantity.
#: ``0`` is deliberately absent; a genuine published zero is a real observation.
SUPPRESSION_MARKERS: frozenset[str] = frozenset(
    {
        "*",
        "**",
        ".",
        "..",
        "...",
        "-",
        "--",
        ":",
        "c",
        "z",
        "w",
        "x",
        "u",
        "n/a",
        "na",
        "n/k",
        "nk",
        "null",
        "none",
        "suppressed",
        "not available",
        "not applicable",
        "no data",
    }
)


def parse_cell(raw: object) -> float | None:
    """Return a number, or ``None`` for anything meaning "no value here".

    This is the single most important function in the module. NHS England suppresses small
    numbers, and small numbers are precisely where the ascertainment propositions live. A
    ``*`` read as ``0.0`` does not merely lose a data point - it fabricates a trough, and a
    mechanism fitted to a fabricated trough is the wrong mechanism, confidently.

    Thousands separators are stripped because NHSE spreadsheets emit "1,234" as text.
    Percentages are *not* silently divided by 100: a "%" suffix changes the unit, and
    guessing the unit is how a rate becomes a proportion halfway through a series.
    """

    if raw is None:
        return None
    if isinstance(raw, bool):
        raise NhsDataError("a boolean is not a published statistic")
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text or text.lower() in SUPPRESSION_MARKERS:
        return None
    candidate = text.replace(",", "").replace(" ", "")
    if candidate.endswith("%"):
        raise NhsDataError(
            f"cell {text!r} carries a percent sign; its unit differs from a count and "
            "must be handled explicitly rather than coerced"
        )
    try:
        return float(candidate)
    except ValueError:
        return None


# --------------------------------------------------------------------------------------
# Periods: the label is the truth
# --------------------------------------------------------------------------------------

_FINANCIAL_YEAR = re.compile(r"^\s*(\d{4})\s*[/-]\s*(\d{2}|\d{4})\s*$")
_QUARTER = re.compile(r"^\s*Q([1-4])\s+(\d{4})\s*[/-]\s*(\d{2}|\d{4})\s*$", re.IGNORECASE)
_CALENDAR_MONTH = re.compile(r"^\s*([A-Za-z]{3,9})\s+(\d{4})\s*$")
_CALENDAR_YEAR = re.compile(r"^\s*(\d{4})\s*$")


@dataclass(frozen=True)
class NhsPeriod:
    """One reporting period, with its basis established rather than assumed.

    Five distinct things in NHS publications look like dates and are not interchangeable:

    * a **financial year** ("2023/24") runs April to March and is not calendar 2023;
    * a **financial quarter** ("Q4 2022-23") is Jan-Mar of the *following* calendar year;
    * a **reporting month** ("May 2026") is the month measured;
    * a **performance/publication month** is when the figure was released, which for MHSDS
      is roughly two months after the month measured;
    * an ODS ``LastChangeDate`` is when a *record* was edited (see
      :class:`OdsOrganisation`).

    Nothing here converts a label into a ``date``. :attr:`label` is preserved verbatim and
    is what any downstream series is keyed and reported on. :attr:`start_year` is offered
    only as the first calendar year the window *touches*, and :attr:`basis` says which of
    the above it is so a caller cannot mix two of them into one axis by accident.
    """

    label: str
    basis: str = "unknown"

    @classmethod
    def parse(cls, label: str) -> NhsPeriod:
        text = (label or "").strip()
        if not text:
            raise NhsDataError("an empty period label cannot be placed on a time axis")
        if _QUARTER.match(text):
            return cls(label=text, basis="financial_quarter")
        if _FINANCIAL_YEAR.match(text):
            return cls(label=text, basis="financial_year")
        if _CALENDAR_MONTH.match(text):
            return cls(label=text, basis="reporting_month")
        if _CALENDAR_YEAR.match(text):
            return cls(label=text, basis="calendar_year")
        return cls(label=text, basis="unknown")

    @property
    def is_financial(self) -> bool:
        return self.basis in {"financial_year", "financial_quarter"}

    @property
    def start_year(self) -> int | None:
        """First calendar year the window touches - not "the year of" the period."""

        for pattern, group in ((_QUARTER, 2), (_FINANCIAL_YEAR, 1), (_CALENDAR_YEAR, 1)):
            match = pattern.match(self.label)
            if match:
                return int(match.group(group))
        match = _CALENDAR_MONTH.match(self.label)
        return int(match.group(2)) if match else None

    def as_calendar_year(self) -> int:
        """The calendar year, or a refusal.

        A financial year label has no single calendar year. Returning ``start_year`` here
        would shift a whole series by up to twelve months without anything looking wrong,
        which is how a lag gets invented.
        """

        if self.is_financial:
            raise NhsDataError(
                f"{self.label!r} is a {self.basis.replace('_', ' ')} and does not map to "
                "one calendar year; keep the label or model the window explicitly"
            )
        year = self.start_year
        if year is None:
            raise NhsDataError(f"cannot establish a calendar year from {self.label!r}")
        return year


# --------------------------------------------------------------------------------------
# Aggregate cells and series construction
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AggregateCell:
    """One published aggregate figure, with its stratum carried alongside it.

    ``breakdown_level`` is the axis that most often goes wrong. NHS tables ship England,
    region, ICB and provider rows in the same sheet; ``age_group`` ships "All ages"
    beside "18-24". Carrying the level on every cell is what lets :func:`build_series`
    detect that a selection straddles two of them instead of quietly summing.
    """

    measure: str
    breakdown_level: str
    breakdown_code: str
    breakdown_name: str
    age_group: str
    gender: str
    period: NhsPeriod
    value: float | None
    suppression_marker: str = ""

    @property
    def missing(self) -> bool:
        return self.value is None

    @property
    def stratum(self) -> tuple[str, str, str, str, str]:
        return (
            self.measure,
            self.breakdown_level,
            self.breakdown_code,
            self.age_group,
            self.gender,
        )


def build_series(cells: Sequence[AggregateCell], *, name: str | None = None) -> ObservedSeries:
    """Turn cells into a calibration target, or refuse and say why.

    Three refusals, each corresponding to a way this project has already been burned:

    1. **Mixed strata.** More than one ``(measure, level, area, age, gender)`` present
       means the caller has selected across an England total and its own parts, or across
       "All ages" and an age band. Summing or averaging that double-counts. Pin one
       stratum first.
    2. **More than one row per period.** Even within a stratum, a duplicate period means
       the selection is not what the caller thinks it is - a revised and an original
       figure, or two geographies sharing a name.
    3. **Any hole.** A suppressed cell is missing, not zero. Refusing here is the whole
       point: it is better to have no W02 series than a W02 series with an invented dip.
    """

    if not cells:
        raise NhsDataError("no cells supplied; there is nothing to calibrate against")

    strata = {cell.stratum for cell in cells}
    if len(strata) > 1:
        rendered = "; ".join(" / ".join(item) for item in sorted(strata))
        raise NhsDataError(
            f"selection spans {len(strata)} strata ({rendered}); NHS tables carry totals "
            "beside their own parts, so these must never be combined - pin one stratum"
        )

    by_period: dict[str, list[AggregateCell]] = {}
    for cell in cells:
        by_period.setdefault(cell.period.label, []).append(cell)
    duplicated = sorted(key for key, group in by_period.items() if len(group) > 1)
    if duplicated:
        raise NhsDataError(
            f"more than one row for period(s) {', '.join(duplicated)}; the selection is "
            "not unique and collapsing it would double-count"
        )

    bases = {cell.period.basis for cell in cells}
    if len(bases) > 1:
        raise NhsDataError(
            f"period labels mix {', '.join(sorted(bases))}; a financial year and a "
            "calendar year are not points on the same axis"
        )

    missing = sorted(cell.period.label for cell in cells if cell.missing)
    if missing:
        raise NhsDataError(
            f"series has no value for {', '.join(missing)}; NHS England suppresses small "
            "numbers and a suppressed cell is MISSING, never 0 - refusing to build a "
            "series with holes"
        )

    ordered = sorted(cells, key=lambda cell: cell.period.label)
    first = ordered[0]
    return ObservedSeries(
        name=name
        or f"{first.measure} - {first.breakdown_name} ({first.age_group}, {first.gender})",
        source_id=SOURCE_ID,
        values=tuple(float(cell.value) for cell in ordered),  # type: ignore[arg-type]
        periods=tuple(cell.period.label for cell in ordered),
    )


# --------------------------------------------------------------------------------------
# ODS ORD API
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OdsDate:
    """A typed ODS date. The ``type`` is load-bearing, so it is never dropped.

    ``Operational`` is when the organisation began or ceased operating; ``Legal`` is when
    the legal entity came into or went out of existence. They routinely differ, and
    neither is ``LastChangeDate``. Values are kept as the published ``YYYY-MM-DD``
    strings; nothing here parses them, because the only thing a caller can get wrong more
    easily than the value is which of the three they picked up.
    """

    type: str
    start: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class OdsRole:
    """One role an organisation holds. An organisation holds several at once."""

    role_id: str
    unique_role_id: int | None
    primary: bool
    status: str
    dates: tuple[OdsDate, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OdsOrganisation:
    """An NHS organisation as ODS publishes it.

    Two traps are encoded here.

    ``last_change_date`` looks like the most authoritative date on the record and is the
    least useful: it is when the *record* was last amended. North London NHS Foundation
    Trust carries ``2026-04-10`` while having operated for years. Anything treating it as
    a formation or opening date will produce a fictitious cohort of brand-new trusts.
    :attr:`operational_start` is the one to use, and it comes from ``Date[Type=
    Operational]``.

    ``status`` being ``Inactive`` does not mean the organisation's activity is absent from
    historical statistics - it means the ODS code is retired. Provider codes are reissued
    and superseded across reorganisations, so a single real trust can appear under several
    ``org_id`` values over a time series. Joining statistics to ODS on code alone, without
    following ``Rels``, silently splits one provider into several.
    """

    org_id: str
    name: str
    status: str
    record_class: str
    post_code: str
    last_change_date: str
    primary_role_id: str
    primary_role_description: str
    source_uri: str
    dates: tuple[OdsDate, ...] = field(default_factory=tuple)
    roles: tuple[OdsRole, ...] = field(default_factory=tuple)

    @property
    def active(self) -> bool:
        return self.status.lower() == "active"

    @property
    def operational_start(self) -> str | None:
        """When the organisation began operating, if published. Not the record date."""

        for item in self.dates:
            if item.type.lower() == "operational":
                return item.start
        return None

    @property
    def role_ids(self) -> tuple[str, ...]:
        return tuple(role.role_id for role in self.roles)


@dataclass(frozen=True)
class OdsSearchResult:
    """A page of ODS results, with the server's own counts kept for verification.

    ``total_count`` is ODS's ``X-Total-Count`` header and it respects the filter (verified
    live: 69 for ``Name=tavistock``, 305,791 unfiltered). That property is what makes
    :meth:`NhsOdsConnector.verify_filter_honoured` able to detect a discarded parameter,
    so it is surfaced rather than thrown away.
    """

    organisations: tuple[OdsOrganisation, ...]
    total_count: int | None
    returned_records: int | None
    next_page: str | None

    @property
    def exhausted(self) -> bool:
        return self.next_page is None


def _ods_dates(payload: object) -> tuple[OdsDate, ...]:
    if not isinstance(payload, list):
        return ()
    return tuple(
        OdsDate(
            type=str(item.get("Type") or "Unknown"),
            start=item.get("Start"),
            end=item.get("End"),
        )
        for item in payload
        if isinstance(item, dict)
    )


class NhsOdsConnector:
    """Keyless client for the ODS ORD organisation reference API.

    Chosen over every statistics route investigated because it is the only NHS surface
    found that is simultaneously a documented, versioned API, machine-readable JSON, and
    unrestricted by its host's published policy (``directory.spineservices.nhs.uk`` serves
    no ``robots.txt``). It carries no statistics itself - it carries the institutional
    identities that statistics are reported against, which W02 needs before it can join
    anything to anything.
    """

    source_name = "NHS England ODS (ORD API)"
    connector_version = "1"
    base_url = ODS_BASE_URL

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
        min_interval_seconds: float = 1.0,
    ) -> None:
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    def _throttle(self) -> None:
        """Throttled from the first request, not after the first complaint."""

        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _get(self, path: str, params: dict[str, str | int] | None = None) -> httpx.Response:
        url = guard_route(f"{self.base_url}{path}")
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._throttle()
            response = client.get(url, params=params or {})
            response.raise_for_status()
            return response
        finally:
            if self._client is None:
                client.close()

    @staticmethod
    def _int_header(response: httpx.Response, key: str) -> int | None:
        raw = response.headers.get(key)
        try:
            return int(raw) if raw is not None else None
        except ValueError:
            return None

    def search_organisations(
        self,
        *,
        name: str | None = None,
        primary_role_id: str | None = None,
        status: str | None = None,
        post_code: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> OdsSearchResult:
        """Search organisations. At least one filter is required.

        The unfiltered index is ~300,000 records covering every GP practice, site, ward
        and long-dead primary care trust. An unfiltered "search" is not a search, and
        paging it would be both useless and rude to a free public service, so it is
        refused here rather than attempted.
        """

        if not any((name, primary_role_id, status, post_code)):
            raise ValueError(
                "supply at least one of name, primary_role_id, status or post_code; the "
                f"unfiltered index is ~{ODS_UNFILTERED_TOTAL_ORDER_OF_MAGNITUDE:,} records"
            )
        if not 1 <= limit <= ODS_MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {ODS_MAX_LIMIT}; ODS returns 406 above")

        params: dict[str, str | int] = {"Limit": limit}
        if offset:
            params["Offset"] = offset
        if name:
            params["Name"] = name
        if primary_role_id:
            params["PrimaryRoleId"] = primary_role_id
        if status:
            params["Status"] = status
        if post_code:
            params["PostCode"] = post_code

        response = self._get("/organisations", params)
        payload = response.json()
        if not isinstance(payload, dict) or "Organisations" not in payload:
            raise NhsDataError("ODS did not return an Organisations envelope")

        organisations = tuple(
            OdsOrganisation(
                org_id=str(row.get("OrgId") or ""),
                name=str(row.get("Name") or ""),
                status=str(row.get("Status") or ""),
                record_class=str(row.get("OrgRecordClass") or ""),
                post_code=str(row.get("PostCode") or ""),
                last_change_date=str(row.get("LastChangeDate") or ""),
                primary_role_id=str(row.get("PrimaryRoleId") or ""),
                primary_role_description=str(row.get("PrimaryRoleDescription") or ""),
                source_uri=str(row.get("OrgLink") or ""),
            )
            for row in payload["Organisations"]
            if isinstance(row, dict)
        )
        return OdsSearchResult(
            organisations=organisations,
            total_count=self._int_header(response, "X-Total-Count"),
            returned_records=self._int_header(response, "Returned-Records"),
            next_page=response.headers.get("Next-Page"),
        )

    def organisation(self, org_id: str) -> OdsOrganisation:
        """Full record for one ODS code, including typed dates and every role."""

        code = (org_id or "").strip().upper()
        if not code:
            raise ValueError("org_id must not be empty")
        payload = self._get(f"/organisations/{code}").json()
        body = payload.get("Organisation") if isinstance(payload, dict) else None
        if not isinstance(body, dict):
            raise NhsDataError(f"ODS returned no Organisation body for {code!r}")

        raw_roles = ((body.get("Roles") or {}).get("Role")) or []
        roles = tuple(
            OdsRole(
                role_id=str(item.get("id") or ""),
                unique_role_id=item.get("uniqueRoleId"),
                primary=bool(item.get("primaryRole", False)),
                status=str(item.get("Status") or ""),
                dates=_ods_dates(item.get("Date")),
            )
            for item in raw_roles
            if isinstance(item, dict)
        )
        primary = next((role for role in roles if role.primary), None)
        org_id_field = body.get("OrgId")
        extension = (
            org_id_field.get("extension") if isinstance(org_id_field, dict) else org_id_field
        )
        location = ((body.get("GeoLoc") or {}).get("Location")) or {}

        return OdsOrganisation(
            org_id=str(extension or code),
            name=str(body.get("Name") or ""),
            status=str(body.get("Status") or ""),
            record_class=str(body.get("orgRecordClass") or body.get("OrgRecordClass") or ""),
            post_code=str(location.get("PostCode") or ""),
            last_change_date=str(body.get("LastChangeDate") or ""),
            primary_role_id=primary.role_id if primary else "",
            primary_role_description="",
            source_uri=f"{self.base_url}/organisations/{code}",
            dates=_ods_dates(body.get("Date")),
            roles=roles,
        )

    def verify_filter_honoured(self, *, field_name: str, value_a: str, value_b: str) -> bool:
        """Send two genuinely different queries and confirm the results differ.

        Two connectors in this project accepted a search term the upstream API silently
        discarded, and produced confident, wrong, unfiltered results. This makes that
        check a callable rather than a memory. It compares ``X-Total-Count`` first because
        that is the cheapest discriminator, and falls back to comparing the returned
        identity sets when both pages are capped at the same total.
        """

        if value_a == value_b:
            raise ValueError("the two probe values must genuinely differ")
        first = self.search_organisations(**{_ODS_FILTER_KWARGS[field_name]: value_a}, limit=5)
        second = self.search_organisations(**{_ODS_FILTER_KWARGS[field_name]: value_b}, limit=5)
        if first.total_count is not None and second.total_count is not None:
            if first.total_count != second.total_count:
                return True
        ids_a = {org.org_id for org in first.organisations}
        ids_b = {org.org_id for org in second.organisations}
        return bool(ids_a or ids_b) and ids_a != ids_b


#: Maps a user-facing filter name onto the keyword :meth:`search_organisations` expects.
_ODS_FILTER_KWARGS: dict[str, str] = {
    "Name": "name",
    "PrimaryRoleId": "primary_role_id",
    "Status": "status",
    "PostCode": "post_code",
}


# --------------------------------------------------------------------------------------
# NHS England statistics publication index
# --------------------------------------------------------------------------------------

_HREF = re.compile(r"""href=["'](?P<url>[^"'>\s]+\.(?:csv|xlsx|xlsm|xls|zip))["']""", re.I)

#: Work areas most relevant to W02 referrals and pathways, confirmed to exist 2026-08-15.
W02_WORK_AREAS: tuple[str, ...] = (
    "cyped-waiting-times",
    "eip-waiting-times",
    "rtt-waiting-times",
    "mental-health-five-year-forward-view-dashboard",
)


@dataclass(frozen=True)
class PublicationFile:
    """A reference to one published NHS England statistics attachment.

    A *reference*, emphatically not its contents. See
    :class:`NhsEnglandStatisticsIndex` for why nothing here parses the file.
    """

    work_area: str
    url: str
    filename: str
    extension: str
    page_url: str

    @property
    def is_spreadsheet(self) -> bool:
        return self.extension in {"xls", "xlsx", "xlsm"}


class NhsEnglandStatisticsIndex:
    """Discovers published statistics files on ``www.england.nhs.uk``.

    **Read this before relying on it.** There is no API and no stable URL scheme. NHS
    England publishes each release as a WordPress media upload, so the URLs look like
    ``/statistics/wp-content/uploads/sites/2/2023/06/CYPED-Publication-Q4-2022-23-Provider-
    SubICB-new-codes-V2-1.xlsx``. Observed live in the same index: ``-V2-1``,
    ``-broken-links-to-publish-1``, ``-XLS-62K``, and the same quarter appearing under two
    different upload months. The path segment is the *upload* month, not the period the
    data covers, and the filename is hand-written each time.

    Consequences, stated plainly rather than discovered later:

    * A URL cannot be constructed for a given period. It can only be found by reading the
      index page, so this is HTML scraping and it will break when the page template
      changes. That is tolerable *only* because of the next point.
    * This class produces no numbers. It returns references with the filename preserved
      verbatim, for a human to select and cite. Nothing downstream can therefore inherit a
      wrong figure from a mis-scraped link - the worst failure mode is a missing link,
      which is visible, rather than a wrong value, which is not.
    * Do not infer the reporting period from the filename or the upload path. Both have
      been observed to disagree with the period the file covers. Establish the period from
      inside the file, by hand.

    ``robots.txt`` for ``www.england.nhs.uk`` disallows only ``/wp-admin/``, so this
    retrieval is permitted. Requests are throttled anyway.
    """

    source_name = "NHS England statistical work areas"
    connector_version = "1"
    base_url = NHSE_STATISTICS_BASE

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
        min_interval_seconds: float = 2.0,
    ) -> None:
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def publication_files(self, work_area: str) -> tuple[PublicationFile, ...]:
        """File references linked from one work-area index page, in page order.

        Links to hosts on :data:`DECLINED_ROUTES` are dropped rather than returned, so a
        caller cannot be handed a URL this project has undertaken not to fetch. Duplicate
        URLs are collapsed; NHS England lists the same file under several headings.
        """

        slug = (work_area or "").strip().strip("/")
        if not slug:
            raise ValueError("work_area must not be empty")
        page_url = guard_route(f"{self.base_url}/{slug}/")
        client = self._client or httpx.Client(timeout=self.timeout, follow_redirects=True)
        try:
            self._throttle()
            response = client.get(page_url)
            response.raise_for_status()
        finally:
            if self._client is None:
                client.close()

        found: list[PublicationFile] = []
        seen: set[str] = set()
        for match in _HREF.finditer(response.text):
            url = match.group("url")
            if url.startswith("/"):
                url = f"https://{NHSE_HOST}{url}"
            if urlparse(url).netloc.lower() != NHSE_HOST:
                continue
            if declined_route_for(url) is not None or url in seen:
                continue
            seen.add(url)
            filename = urlparse(url).path.rsplit("/", 1)[-1]
            found.append(
                PublicationFile(
                    work_area=slug,
                    url=url,
                    filename=filename,
                    extension=filename.rsplit(".", 1)[-1].lower(),
                    page_url=page_url,
                )
            )
        return tuple(found)
