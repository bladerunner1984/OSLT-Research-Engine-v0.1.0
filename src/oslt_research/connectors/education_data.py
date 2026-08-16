"""Dated aggregate education series from the DfE Explore Education Statistics API.

Workstream W05 (UK education statutory guidance and school-level data) had two registered
rows, both document corpora:

* DS054 - DfE RSHE statutory guidance corpus
* DS055 - DfE Keeping Children Safe in Education corpus

Both are GOV.UK publications, and both are already reachable through
``oslt_research.connectors.govuk_guidance``: they are ``department-for-education``
documents of type ``statutory_guidance``/``guidance``, which is exactly what that
connector already lists. Rebuilding a GOV.UK search wrapper here would have produced a
second copy of an existing connector and no new evidence, so this module deliberately
does NOT do that.

What it adds instead is the thing W05 had no route to at all: DATED AGGREGATE SERIES.
The DfE publishes its official statistics through an open, key-free JSON API whose base
URL is advertised by the Explore Education Statistics front end as ``PUBLIC_API_BASE_URL``
(the documented-looking ``explore-education-statistics.service.gov.uk/api/`` path is a
404 - it is the web app, not the API). That API exposes publications, the data sets under
them, each data set's metadata (declared time periods, indicators, filters, geographies),
and a POST query endpoint returning one row per (time period x geography x filter
combination) with numeric indicator values. Pupil absence, for instance, is available at
national level for academic years 2006/07 onward.

That is a calibration target in the sense
``oslt_research.governance.mechanism_simulation.ObservedSeries`` means: a published,
consistently defined, dated measure that a candidate mechanism must reproduce. A national
guidance document cannot be calibrated against; a national absence series can.

Three things about this API cost real effort to establish and are enforced in code:

1. **The API tells you when it ignored you - so read it.** ``filters.in`` with an unknown
   id does not error; it returns ``totalResults: 0`` plus a ``warnings`` array containing
   ``FiltersNotFound``. Worse, several filter ids drawn from DIFFERENT filter groups
   inside ONE ``filters.in`` clause are combined as a UNION, not an intersection: asking
   for ``["persistent absence", "state-funded secondary"]`` in a single clause returned
   108 rows spanning every absence type and every school type, while the same two ids as
   two separate ``and`` clauses returned the intended 18. This module always emits one
   clause per filter id, treats any non-empty ``warnings`` array as a hard failure, and
   additionally checks that every returned row's filter assignment actually contains the
   requested ids. A silently widened query is a different measurement.

2. **Every date-looking field here measures something different.** See
   ``DATE_FIELD_SEMANTICS``. In particular ``latestVersion.published`` is when the DfE
   released that version of the file - the 2006/07 absence figures live in a data set
   published in 2026 - and ``timePeriod.period`` of ``"2006/2007"`` with code ``"AY"`` is
   a September-to-August academic year, not calendar 2006 and not calendar 2007. Only
   ``timePeriod`` describes what the number is about.

3. **A missing period is not a zero, and neither is a suppression marker.** The national
   persistent-absence series has no ``2019/2020`` row at all - collection was disrupted -
   and individual cells come back as the string ``"z"`` rather than a number. Carrying
   either through as ``0.0`` would put a fabricated trough into the exact data a mechanism
   is tested against, so ``EducationSeries.to_observed_series`` refuses both.

No API key. Throttled by default.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from oslt_research.governance.mechanism_simulation import ObservedSeries

#: DS069 in the source register (added 2026-08). Deliberately its own row rather than
#: DS054/DS055: those W05 rows describe guidance CORPORA, and labelling a statistical
#: series with a document corpus's id would misattribute its provenance.
SOURCE_ID = "DS069"

#: Registered W05 rows that this connector intentionally does not serve, and where they
#: are already served from.
DOCUMENT_ROWS_COVERED_ELSEWHERE = {
    "DS054": "oslt_research.connectors.govuk_guidance",
    "DS055": "oslt_research.connectors.govuk_guidance",
}

#: What each date-shaped field in this API actually measures. Several connectors in this
#: project have already mis-dated a record by assuming a date field meant coverage.
DATE_FIELD_SEMANTICS = {
    "publication.lastPublished": (
        "release timestamp of the most recent output under the publication; says nothing "
        "about which periods the data covers"
    ),
    "dataSet.latestVersion.published": (
        "release timestamp of that VERSION of the data file; a 2026 timestamp routinely "
        "carries figures back to 2006/07"
    ),
    "dataSet.latestVersion.timePeriods": (
        "declared coverage envelope (start/end labels) of the data set - the only "
        "statement of what the data is about, and an envelope, not proof that every "
        "period inside it is present"
    ),
    "result.timePeriod.period": (
        "the period the observation measures, e.g. '2006/2007'; interpret ONLY together "
        "with result.timePeriod.code"
    ),
    "result.timePeriod.code": (
        "the calendar system of the period: AY academic year (Sep-Aug), CY calendar year, "
        "FY financial year (Apr-Mar), T1..T3 terms, M1..M12 months, W1..W53 weeks. Two "
        "codes in one series are two different measurements"
    ),
}

#: Non-numeric cell values used by DfE statistical releases. None of these is a zero: they
#: mean not applicable, suppressed for disclosure control, unavailable or unreliable. A
#: series containing any of them is incomplete.
SUPPRESSION_MARKERS = frozenset({"z", "c", "x", "k", "u", "low", "~", ":", "-", ""})


class QueryNotHonouredError(RuntimeError):
    """The API accepted the request but did not answer the question that was asked.

    Raised on any warning from the query endpoint and on any returned row whose filter
    assignment does not contain every requested filter id. Both cases silently return
    numbers, which is the dangerous kind of failure: a wider or different population
    reported as if it were the requested one.
    """


@dataclass(frozen=True)
class PublicationSummary:
    publication_id: str
    title: str
    slug: str
    summary: str = ""
    #: Release timestamp - NOT coverage. See DATE_FIELD_SEMANTICS.
    last_published: str | None = None


@dataclass(frozen=True)
class DataSetSummary:
    data_set_id: str
    title: str
    summary: str = ""
    status: str = ""
    version: str = ""
    #: Release timestamp of the version - NOT coverage. See DATE_FIELD_SEMANTICS.
    published: str | None = None
    time_period_start: str | None = None
    time_period_end: str | None = None
    geographic_levels: tuple[str, ...] = ()
    indicators: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataSetMeta:
    """Declared vocabulary of a data set.

    The declared time periods matter beyond lookup: they are the denominator against which
    a returned series is checked for holes. Without them a query that quietly returned
    eighteen of nineteen academic years would look complete.
    """

    data_set_id: str
    #: (code, period, label) in the order the API declares them.
    time_periods: tuple[tuple[str, str, str], ...] = ()
    indicators: dict[str, str] = field(default_factory=dict)
    filter_options: dict[str, str] = field(default_factory=dict)
    filter_group_of_option: dict[str, str] = field(default_factory=dict)
    geographic_levels: dict[str, str] = field(default_factory=dict)

    def periods_for_code(self, code: str) -> tuple[str, ...]:
        return tuple(period for item_code, period, _ in self.time_periods if item_code == code)


@dataclass(frozen=True)
class SeriesPoint:
    period: str
    code: str
    #: None when the cell was a suppression marker rather than a number.
    value: float | None
    marker: str | None = None

    @property
    def usable(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class EducationSeries:
    """One indicator, one filter combination, one geography, across time periods."""

    data_set_id: str
    indicator_id: str
    indicator_label: str
    filter_ids: tuple[str, ...]
    geographic_level: str
    points: tuple[SeriesPoint, ...] = ()
    #: Periods the data set's metadata declares for this code but the query never returned.
    missing_periods: tuple[str, ...] = ()
    time_period_code: str = ""

    @property
    def suppressed_periods(self) -> tuple[str, ...]:
        return tuple(point.period for point in self.points if not point.usable)

    @property
    def complete(self) -> bool:
        """Complete means every declared period came back with a number.

        Holes and suppression markers are both absences of a measurement. Neither is a low
        value, so neither may be smoothed over.
        """

        return bool(self.points) and not self.missing_periods and not self.suppressed_periods

    def to_observed_series(self, *, name: str | None = None) -> ObservedSeries:
        """Convert to a calibration target, or refuse.

        Refusing is the point. If a mechanism is scored against a series in which a
        disrupted collection year appears as zero, the mechanism that best reproduces a
        crash in 2019/20 wins on fabricated evidence.
        """

        if not self.points:
            raise ValueError("series is empty; there is nothing to calibrate against")
        if self.missing_periods:
            raise ValueError(
                f"series is missing declared periods ({', '.join(self.missing_periods)}); a "
                "period the source never reported is not a zero and must not be calibrated "
                "against"
            )
        if self.suppressed_periods:
            raise ValueError(
                f"series has non-numeric cells at ({', '.join(self.suppressed_periods)}); a "
                "suppression marker is not a zero and must not be calibrated against"
            )
        return ObservedSeries(
            name=name or f"{self.indicator_label} ({self.geographic_level})",
            source_id=SOURCE_ID,
            values=tuple(float(point.value) for point in self.points if point.value is not None),
            periods=tuple(point.period for point in self.points),
        )


def parse_cell(raw: Any) -> tuple[float | None, str | None]:
    """Return (value, marker). A suppression marker yields (None, marker), never (0.0, ...)."""

    if raw is None:
        return None, ":"
    if isinstance(raw, bool):
        return None, str(raw)
    if isinstance(raw, (int, float)):
        return float(raw), None
    text = str(raw).strip()
    if text.lower() in SUPPRESSION_MARKERS:
        return None, text or ":"
    try:
        return float(text.replace(",", "")), None
    except ValueError:
        return None, text


class EducationDataConnector:
    """DfE Explore Education Statistics public API.

    Yields dated aggregate series rather than documents, which is why it exists alongside
    the GOV.UK guidance connector rather than instead of it. A series says how many
    enrolments were persistently absent in each academic year; a statutory guidance
    document says what schools were told to do. Only the first can falsify a mechanism.

    What a series measures is what the DfE's own definition says and nothing more.
    Attendance counts are not wellbeing, and the rule that a national statistic is not
    evidence of a school-level causal path applies to every series taken from here.

    Requires no API key.
    """

    source_name = "DfEEducationStatistics"
    connector_version = "1"
    base_url = "https://api.education.gov.uk/statistics"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
        min_interval_seconds: float = 0.35,
    ) -> None:
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    # -- plumbing ---------------------------------------------------------------

    def _throttle(self) -> None:
        """Space out calls.

        The API advertises no rate-limit headers, so there is no signal to back off
        against. An unthrottled harvest elsewhere in this project lost 808 records to a
        limit that was only discovered by hitting it.
        """

        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._throttle()
            response = client.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=json_body,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._client is None:
                client.close()
        if not isinstance(payload, dict):
            raise RuntimeError(f"unexpected non-object response from {path}")
        return payload

    # -- catalogue --------------------------------------------------------------

    def list_publications(
        self, *, search: str | None = None, page: int = 1, page_size: int = 20
    ) -> list[PublicationSummary]:
        """List DfE statistical publications, optionally filtered by ``search``.

        ``search`` is genuinely honoured - verified live by sending two different terms and
        confirming both the totals and the titles differed ("absence" 7 results, "exclusion"
        2, unfiltered 23) rather than assuming, because other connectors in this project
        accepted a term the API had silently discarded.
        """

        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if search:
            params["search"] = search
        payload = self._request("GET", "/v1/publications", params=params)
        return [
            PublicationSummary(
                publication_id=str(item.get("id", "")),
                title=str(item.get("title", "")),
                slug=str(item.get("slug", "")),
                summary=str(item.get("summary", "") or ""),
                last_published=item.get("lastPublished"),
            )
            for item in payload.get("results", [])
        ]

    def list_data_sets(
        self, publication_id: str, *, page: int = 1, page_size: int = 20
    ) -> list[DataSetSummary]:
        payload = self._request(
            "GET",
            f"/v1/publications/{publication_id}/data-sets",
            params={"page": page, "pageSize": page_size},
        )
        results: list[DataSetSummary] = []
        for item in payload.get("results", []):
            version = item.get("latestVersion") or {}
            periods = version.get("timePeriods") or {}
            results.append(
                DataSetSummary(
                    data_set_id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    summary=str(item.get("summary", "") or ""),
                    status=str(item.get("status", "") or ""),
                    version=str(version.get("version", "") or ""),
                    published=version.get("published"),
                    time_period_start=periods.get("start"),
                    time_period_end=periods.get("end"),
                    geographic_levels=tuple(version.get("geographicLevels") or ()),
                    indicators=tuple(version.get("indicators") or ()),
                    filters=tuple(version.get("filters") or ()),
                )
            )
        return results

    def data_set_meta(self, data_set_id: str) -> DataSetMeta:
        payload = self._request("GET", f"/v1/data-sets/{data_set_id}/meta")
        time_periods = tuple(
            (str(item.get("code", "")), str(item.get("period", "")), str(item.get("label", "")))
            for item in payload.get("timePeriods", [])
        )
        indicators = {
            str(item.get("id", "")): str(item.get("label", ""))
            for item in payload.get("indicators", [])
        }
        options: dict[str, str] = {}
        group_of: dict[str, str] = {}
        for group in payload.get("filters", []):
            group_id = str(group.get("id", ""))
            for option in group.get("options", []):
                option_id = str(option.get("id", ""))
                options[option_id] = str(option.get("label", ""))
                group_of[option_id] = group_id
        levels = {
            str(item.get("code", "")): str(item.get("label", ""))
            for item in payload.get("geographicLevels", [])
        }
        return DataSetMeta(
            data_set_id=data_set_id,
            time_periods=time_periods,
            indicators=indicators,
            filter_options=options,
            filter_group_of_option=group_of,
            geographic_levels=levels,
        )

    # -- series -----------------------------------------------------------------

    @staticmethod
    def build_criteria(filter_ids: tuple[str, ...], geographic_level: str) -> dict[str, Any]:
        """Build query criteria with one ``filters.in`` clause PER id.

        Putting several ids from different filter groups into one clause makes the API
        union them, so a request for 'persistent absence AND state-funded secondary'
        silently becomes 'persistent absence OR state-funded secondary' - six times the
        rows, a different population, and no warning at all.
        """

        clauses: list[dict[str, Any]] = [
            {"filters": {"in": [filter_id]}} for filter_id in filter_ids
        ]
        clauses.append({"geographicLevels": {"eq": geographic_level}})
        return {"and": clauses}

    def query_series(
        self,
        data_set_id: str,
        *,
        indicator_id: str,
        filter_ids: tuple[str, ...] = (),
        geographic_level: str = "NAT",
        time_period_code: str = "AY",
        meta: DataSetMeta | None = None,
        page_size: int = 200,
        max_pages: int = 25,
    ) -> EducationSeries:
        """Fetch one indicator for one filter combination as a dated series.

        ``meta`` supplies the declared periods used to detect holes; it is fetched if not
        supplied. Raises :class:`QueryNotHonouredError` rather than returning numbers the
        caller did not ask for.
        """

        resolved_meta = meta or self.data_set_meta(data_set_id)
        criteria = self.build_criteria(tuple(filter_ids), geographic_level)
        rows: list[dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            payload = self._request(
                "POST",
                f"/v1/data-sets/{data_set_id}/query",
                json_body={
                    "criteria": criteria,
                    "indicators": [indicator_id],
                    "page": page,
                    "pageSize": page_size,
                    "sorts": [{"field": "timePeriod", "direction": "Asc"}],
                },
            )
            warnings = payload.get("warnings") or []
            if warnings:
                raise QueryNotHonouredError(
                    f"data set {data_set_id} query returned warnings: {warnings}"
                )
            rows.extend(payload.get("results", []))
            paging = payload.get("paging") or {}
            if page >= int(paging.get("totalPages", 1) or 1):
                break
            page += 1

        wanted = set(filter_ids)
        points: list[SeriesPoint] = []
        seen: set[str] = set()
        for row in rows:
            assigned = set((row.get("filters") or {}).values())
            if not wanted <= assigned:
                raise QueryNotHonouredError(
                    f"data set {data_set_id} returned a row with filters {sorted(assigned)} "
                    f"that does not match the requested {sorted(wanted)}; the query was "
                    "widened, so the population is not the one asked for"
                )
            level = str(row.get("geographicLevel", ""))
            if level and level != geographic_level:
                raise QueryNotHonouredError(
                    f"data set {data_set_id} returned geographic level {level!r}, not "
                    f"{geographic_level!r}"
                )
            period_info = row.get("timePeriod") or {}
            code = str(period_info.get("code", ""))
            if code != time_period_code:
                # Mixing academic years with calendar years would concatenate two
                # differently defined measurements into a single series.
                continue
            period = str(period_info.get("period", ""))
            if period in seen:
                raise QueryNotHonouredError(
                    f"data set {data_set_id} returned duplicate rows for period {period!r}; "
                    "the filter combination does not identify a single series"
                )
            seen.add(period)
            value, marker = parse_cell((row.get("values") or {}).get(indicator_id))
            points.append(SeriesPoint(period=period, code=code, value=value, marker=marker))

        points.sort(key=lambda point: point.period)
        declared = resolved_meta.periods_for_code(time_period_code)
        missing = tuple(period for period in declared if period not in seen)
        return EducationSeries(
            data_set_id=data_set_id,
            indicator_id=indicator_id,
            indicator_label=resolved_meta.indicators.get(indicator_id, indicator_id),
            filter_ids=tuple(filter_ids),
            geographic_level=geographic_level,
            points=tuple(points),
            missing_periods=missing,
            time_period_code=time_period_code,
        )
