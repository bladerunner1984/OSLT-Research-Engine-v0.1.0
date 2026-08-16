"""NOMIS - ONS official labour market statistics and Census 2021, via query API.

Workstream W01 (population denominators and trend decomposition) is required by 42 of the
64 propositions. :mod:`oslt_research.connectors.ons_population` already serves mid-year
estimates, but only by streaming a 123MB, 2.35-million-row CSV. NOMIS publishes the *same*
ONS population data - plus Census 2021 and the labour market tables - behind a query API,
so a caller can ask for one slice and receive one slice.

It also reaches something the CSV route cannot. Census 2021 asked a voluntary gender
identity question of usual residents aged 16 and over, and NOMIS serves it: TS078
("Gender identity"), TS070 ("Gender identity (detailed)") and the RM035-RM191 cross
tabulations. That is the only national-level enumeration of the population the
propositions concern, and it is reachable keylessly. Verified live - see
:data:`CENSUS_GENDER_IDENTITY_DATASETS`.

Everything defensive in this module exists because of a specific way NOMIS misleads:

1. **Unpinned dimensions default to EVERY code, and every dimension contains its own
   total.** A bare ``?geography=<England>&date=2021`` on the population dataset returns
   726 rows for one country in one year, because ``c_age`` carries "All Ages" *and*
   "Aged 0 to 15" *and* "Aged 16+" *and* "Aged 16 to 64" *and* every single year of age,
   and ``gender`` carries Total alongside Male and Female. Summing those rows would report
   England's 2021 population as some multiple of the true 56,554,891. Geography nests the
   same way: ``TYPE499`` countries contains United Kingdom, Great Britain, England and
   Wales, England, Wales, Scotland and Northern Ireland *in one codelist*, and the twelve
   ``TYPE480`` regions sum to 66,977,988 - the UK, not England. This connector therefore
   never sums. It requires every dimension to be pinned and refuses a series that is not
   exactly one row per period - the same discipline as
   :mod:`oslt_research.connectors.fingertips`.

2. **The query key is not the display name.** The population dataset's age dimension is
   *displayed* as "Age" but must be queried as ``c_age``; ``?age=200`` is silently
   accepted and returns zero rows, which is indistinguishable from "no such data".
   :meth:`NomisConnector.dimension_keys` reads the real keys from the SDMX definition so
   nothing is guessed.

3. **Large responses are silently capped.** ``header.truncated`` came back ``"true"`` on a
   26MB district-level pull, with 23,958 rows returned, the rest dropped and no error.
   A truncated response is a mutilated one; :meth:`NomisConnector.observations` raises.

4. **Date codes are not dates.** See :class:`DatePeriod`. ``2021`` on a census dataset is
   a census reference date; ``2021`` on mid-year estimates is 30 June 2021; and ``2025-06``
   on the Annual Population Survey means "Jul 2024-Jun 2025", a rolling twelve-month
   window that overlaps its neighbours by nine months. Coercing any of those to a calendar
   year silently shifts or duplicates the series.

5. **A hole is not a zero.** A missing, suppressed or non-normal cell stays missing, and a
   series containing one refuses to become a calibration target.

Requests are throttled from the first call. NOMIS asks for one well-formed query rather
than many small ones, so the discovery calls are cheap and the data call is single.
No API key is needed at these volumes.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import httpx

from oslt_research.governance.mechanism_simulation import ObservedSeries

#: DS067 in the source register (added 2026-08). Distinct from DS014, which is the ONS
#: Census 2021 gender identity publication: the NOMIS tables OVERLAP it and inherit its
#: validity problem, recorded on both rows - OSR removed the accreditation of the Census
#: 2021 gender identity statistics on 12 September 2024 and they are now "official
#: statistics in development".
SOURCE_ID = "DS067"

BASE_URL = "https://www.nomisweb.co.uk/api/v01"

#: NOMIS dataset ids verified live. The population one is the query-API counterpart of the
#: CSV that :mod:`ons_population` streams; England 2021 reads 56,554,891 by both routes.
POPULATION_SINGLE_YEAR = "NM_2002_1"
POPULATION_FIVE_YEAR = "NM_31_1"

#: Census 2021 gender identity tables, confirmed reachable and keyless on 2026-08-16.
#: TS070 for England and Wales returned 48,566,373 usual residents aged 16+, of whom
#: 47,572 trans women, 48,435 trans men and 30,257 non-binary - the published figures.
CENSUS_GENDER_IDENTITY_DATASETS: dict[str, str] = {
    "TS078": "NM_2061_1",  # Gender identity (4 categories)
    "TS070": "NM_2087_1",  # Gender identity (detailed, 8 categories)
    "RM035": "NM_2135_1",  # by age
    "RM163": "NM_2263_1",  # by age by sex
    "RM174": "NM_2274_1",  # by sex
    "RM175": "NM_2275_1",  # by sexual orientation
    "RM038": "NM_2138_1",  # by ethnic group
    "RM039": "NM_2139_1",  # by general health
    "RM036": "NM_2136_1",  # by disability
}

#: The TS070 category dimension. Code 0 is a TOTAL sitting in the same codelist as its own
#: parts - the overlapping-aggregate trap in its purest form. Never sum this dimension.
TS070_DIMENSION = "c2021_genderid_8"
TS070_TOTAL_CODE = 0

#: ``MEASURES`` distinguishes a count from a percentage of some unstated base. Mixing them
#: in one series produces numbers differing by orders of magnitude and no error at all.
MEASURE_VALUE = 20100
MEASURE_PERCENT = 20301

#: Geography codes for whole countries, from the ``TYPE499`` codelist. They are listed
#: here together precisely because they OVERLAP: UK contains GB contains England and Wales
#: contains England. Pick exactly one.
GEOGRAPHY_UK = 2092957697
GEOGRAPHY_GREAT_BRITAIN = 2092957698
GEOGRAPHY_ENGLAND = 2092957699
GEOGRAPHY_WALES = 2092957700
GEOGRAPHY_SCOTLAND = 2092957701
GEOGRAPHY_NORTHERN_IRELAND = 2092957702
GEOGRAPHY_ENGLAND_AND_WALES = 2092957703

#: Geography *type* selectors. Passing one of these returns every area at that level, which
#: is the right way to get a cross-section and the wrong way to get a total.
GEOGRAPHY_TYPE_COUNTRIES = "TYPE499"
GEOGRAPHY_TYPE_REGIONS = "TYPE480"

#: ``obs_status`` values other than "A" mean the cell is not a normal published value.
_NORMAL_STATUS = "A"


class NomisError(RuntimeError):
    """Raised when the API cannot be trusted to have answered the question asked."""


@dataclass(frozen=True)
class DatasetSummary:
    """One NOMIS dataset as advertised by the dataset list."""

    dataset_id: str
    name: str

    @property
    def census_table(self) -> str | None:
        """The ONS table code (TS070, RM163, ...) if the name carries one.

        The ONS table code is the stable public identifier; the ``NM_nnnn_n`` id is a NOMIS
        internal that has been re-issued across census rounds.
        """

        match = re.match(r"^\s*([A-Z]{2}\d{3}[A-Z]?)\b", self.name)
        return match.group(1) if match else None


@dataclass(frozen=True)
class CodeValue:
    """One valid value of one dimension, with its nesting kept visible."""

    value: str
    description: str
    parent_code: str | None = None

    @property
    def is_nested(self) -> bool:
        """True when this area sits inside another area in the same codelist.

        Geography codelists are hierarchical. The twelve ``TYPE480`` regions summed to
        66,977,988 in 2021 - the UK, not England - because three of them are Wales,
        Scotland and Northern Ireland. Knowing an area has a parent is what stops a caller
        treating a level as a partition of the thing they meant.
        """

        return self.parent_code is not None


@dataclass(frozen=True)
class DatePeriod:
    """A NOMIS ``date`` code, with what it actually measures made explicit.

    Three different things wear the same clothes:

    * ``2021`` on a **census** dataset is the census reference date (21 March 2021). It is
      not a calendar year and there is no 2020 or 2022 to put beside it.
    * ``2021`` on **mid-year estimates** is 30 June 2021, a stock at an instant. Two
      consecutive codes are one year apart and do not overlap.
    * ``2025-06`` on the **Annual Population Survey** is *not* June 2025. It is
      "Jul 2024-Jun 2025", a rolling twelve-month window labelled by its end. The codes
      step quarterly, so consecutive points share nine months of the same respondents and
      are not independent observations.

    The raw code and the label NOMIS gives it are both preserved. :attr:`end_year` is only
    ever the year the window *ends*, and nothing here converts a code into a calendar year.
    """

    code: str
    label: str = ""
    #: Length of the measurement window in months. NOMIS annual frequencies are all twelve
    #: months wide; what differs is where the window sits, which is why this is not enough
    #: on its own and :attr:`overlaps_neighbours` exists.
    span_months: int = 12

    @property
    def is_rolling(self) -> bool:
        """True for the ``YYYY-MM`` rolling-window form."""

        return bool(re.fullmatch(r"\d{4}-\d{2}", self.code.strip()))

    @property
    def end_year(self) -> int | None:
        """The year the window ENDS. Never assume it is the year measured."""

        match = re.match(r"^(\d{4})", self.code.strip())
        return int(match.group(1)) if match else None

    @property
    def overlaps_neighbours(self) -> bool:
        """True when consecutive published codes share underlying months.

        The APS steps its twelve-month window every quarter. Treating those as independent
        annual points inflates the apparent evidence roughly fourfold.
        """

        return self.is_rolling


def _date_period(code: object, label: object = "") -> DatePeriod:
    """Build a :class:`DatePeriod` without guessing at a calendar year."""

    text = str(code).strip()
    return DatePeriod(code=text, label=str(label or text).strip(), span_months=12)


@dataclass(frozen=True)
class Observation:
    """One NOMIS cell, with missingness kept as missingness."""

    dataset_id: str
    geography_code: str
    geography_name: str
    period: DatePeriod
    measure: str
    dimensions: dict[str, str] = field(default_factory=dict)
    value: float | None = None
    status: str = ""

    @property
    def missing(self) -> bool:
        """A suppressed, withheld or non-normal cell is a hole, not a zero."""

        return self.value is None


@dataclass(frozen=True)
class Series:
    """An ordered single-stratum series: exactly one observation per period."""

    dataset_id: str
    name: str
    geography_name: str
    observations: tuple[Observation, ...] = field(default_factory=tuple)

    @property
    def missing_periods(self) -> tuple[str, ...]:
        return tuple(item.period.code for item in self.observations if item.missing)

    @property
    def complete(self) -> bool:
        return bool(self.observations) and not self.missing_periods

    @property
    def overlapping(self) -> bool:
        return any(item.period.overlaps_neighbours for item in self.observations)

    def observed(self, *, allow_overlapping_periods: bool = False) -> ObservedSeries:
        """Convert to a calibration target, or refuse.

        Refusal is the point. A suppressed local authority coerced to 0.0 puts a fabricated
        trough into the series a mechanism is tested against, and the mechanism that best
        reproduces a fabricated trough is the wrong mechanism. The same applies to rolling
        windows: nine overlapping APS points look like nine years of evidence and carry
        roughly the information of three.
        """

        if not self.observations:
            raise NomisError("series is empty; nothing to calibrate against")
        if not self.complete:
            raise NomisError(
                f"series has missing periods ({', '.join(self.missing_periods)}); a "
                "suppressed or unavailable cell is not a zero and must not be "
                "interpolated or calibrated against"
            )
        if self.overlapping and not allow_overlapping_periods:
            raise NomisError(
                "series uses rolling twelve-month periods that step quarterly, so "
                "consecutive points share underlying months and are not independent "
                "observations; pass allow_overlapping_periods=True only if the "
                "calibration accounts for that overlap"
            )
        return ObservedSeries(
            name=self.name,
            source_id=SOURCE_ID,
            values=tuple(float(item.value) for item in self.observations),  # type: ignore[arg-type]
            periods=tuple(item.period.code for item in self.observations),
        )


def _parse_number(raw: object) -> float | None:
    """Return a float, or None for anything meaning "no number here"."""

    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        text = raw.strip()
        if not text or text in {"-", "*", ":", "n/a", "NA"}:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


class NomisConnector:
    """Keyless client for ONS population, Census 2021 and labour market tables.

    Deliberately narrow. It discovers datasets, enumerates a dataset's real dimension keys
    and their valid values, then retrieves exactly one fully-pinned stratum. It never sums
    across ages, sexes, gender identity categories, measures or geographic levels, because
    every one of those axes in NOMIS carries a total inside the same codelist as its parts.
    """

    source_name = "NOMIS (ONS)"
    connector_version = "1"
    base_url = BASE_URL

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 180.0,
        min_interval_seconds: float = 1.0,
    ):
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    # -- plumbing ---------------------------------------------------------------

    def _throttle(self) -> None:
        """Throttled from the first request, not after the first complaint.

        NOMIS is a free public service with no key. Its guidance is to make one large
        well-formed query rather than many small ones, so the cost of a pause between the
        handful of calls this connector makes is negligible against the cost of losing
        access to the source for a day.
        """

        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _get(self, path: str, params: dict[str, str | int] | None = None) -> dict:
        client = self._client or httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "oslt-research-engine/1 (research)"},
        )
        try:
            self._throttle()
            response = client.get(f"{self.base_url}{path}", params=params or {})
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._client is None:
                client.close()
        if not isinstance(payload, dict):
            raise NomisError(f"{path} did not return a JSON object")
        return payload

    @staticmethod
    def _codelist(payload: dict) -> list[dict]:
        lists = payload.get("structure", {}).get("codelists", {}).get("codelist", [])
        if not lists:
            raise NomisError("response carried no codelist; the dimension may not exist")
        codes = lists[0].get("code", [])
        return list(codes) if isinstance(codes, list) else [codes]

    @staticmethod
    def _code_value(code: dict) -> CodeValue:
        parent = code.get("parentcode")
        return CodeValue(
            value=str(code.get("value")),
            description=str((code.get("description") or {}).get("value", "")),
            parent_code=None if parent is None else str(parent),
        )

    # -- discovery --------------------------------------------------------------

    def list_datasets(self, search: str | None = None) -> tuple[DatasetSummary, ...]:
        """Enumerate datasets, optionally filtered by a wildcard search term.

        Verified live that NOMIS honours ``search`` rather than discarding it: no term
        returns 1,617 datasets, ``*gender identity*`` returns 24 and ``*TS070*`` returns
        exactly 1. Two connectors in this project have already shipped a parameter their
        API silently ignored, producing "scoped" runs that were nothing of the kind, so
        this was checked with genuinely different queries before being relied on.
        """

        params: dict[str, str | int] = {}
        if search is not None:
            if not search.strip():
                raise ValueError("search must not be blank; a blank term is not a query")
            params["search"] = search
        payload = self._get("/dataset/def.sdmx.json", params)
        families = payload.get("structure", {}).get("keyfamilies", {}).get("keyfamily", [])
        return tuple(
            DatasetSummary(
                dataset_id=str(item.get("id", "")),
                name=str((item.get("name") or {}).get("value", "")),
            )
            for item in families
            if item.get("id")
        )

    def dimension_keys(self, dataset_id: str) -> tuple[str, ...]:
        """The dimension names that must be used as QUERY KEYS, in order.

        Read from the SDMX definition's ``conceptref``s and lower-cased, because the
        display name and the query key differ. The population dataset shows "Age" and
        requires ``c_age``; ``?age=200`` returns zero rows with a 200 status and no
        warning, which reads exactly like "there is no such data".
        """

        payload = self._get(f"/dataset/{dataset_id}.def.sdmx.json")
        families = payload.get("structure", {}).get("keyfamilies", {}).get("keyfamily", [])
        if not families:
            raise NomisError(f"no such dataset: {dataset_id}")
        dimensions = families[0].get("components", {}).get("dimension", [])
        return tuple(
            str(item["conceptref"]).lower()
            for item in dimensions
            if item.get("conceptref") and not item.get("isfrequencydimension")
        )

    def selectable_dimensions(self, dataset_id: str) -> tuple[str, ...]:
        """Dimension keys a caller must pin, excluding the ones handled separately.

        ``geography``, ``measures`` and the time axis are passed as their own arguments, so
        what remains is exactly the set that would otherwise silently default to "all".
        """

        return tuple(
            key
            for key in self.dimension_keys(dataset_id)
            if key not in {"geography", "measures", "time", "date"}
        )

    def dimension_values(self, dataset_id: str, dimension: str) -> tuple[CodeValue, ...]:
        """Valid values of one non-geography dimension.

        Enumerating before querying is the only way to discover that TS070's category
        dimension holds a Total in code 0 alongside the seven categories that make it up,
        or that the population dataset's ``c_age`` holds "All Ages", four overlapping
        bands and 91 single years in one flat list.
        """

        codelist = f"CL_{dataset_id.removeprefix('NM_')}_{dimension.upper()}"
        payload = self._get(f"/codelist/{codelist}.def.sdmx.json")
        return tuple(self._code_value(code) for code in self._codelist(payload))

    def geographies(self, dataset_id: str, geography_type: str) -> tuple[CodeValue, ...]:
        """Areas available at one geographic level, with their parents.

        Levels NEST. ``TYPE499`` returns United Kingdom, Great Britain, England and Wales,
        England, Wales, Scotland and Northern Ireland in a single flat list; four of those
        contain others. The parent code is carried through so a caller can see that the
        twelve regions include Wales, Scotland and Northern Ireland and therefore do not
        partition England.
        """

        payload = self._get(
            f"/dataset/{dataset_id}/geography/{geography_type}.def.sdmx.json"
        )
        return tuple(self._code_value(code) for code in self._codelist(payload))

    def date_codes(self, dataset_id: str) -> tuple[DatePeriod, ...]:
        """Every ``date`` code the dataset publishes, with its NOMIS label.

        The label is what disambiguates the code. ``2025-06`` labelled "Jul 2024-Jun 2025"
        is a rolling window; ``2021`` labelled "2021" on a census table is a reference
        date. Neither is safe to coerce, so both are kept verbatim.
        """

        payload = self._get(f"/dataset/{dataset_id}.overview.json")
        dimensions = payload.get("overview", {}).get("dimensions", {}).get("dimension", [])
        for dimension in dimensions:
            if str(dimension.get("name", "")).lower() != "date":
                continue
            codes = (dimension.get("codes") or {}).get("code", [])
            if isinstance(codes, dict):
                codes = [codes]
            return tuple(
                _date_period(item.get("value", ""), item.get("name", "")) for item in codes
            )
        return ()

    # -- data -------------------------------------------------------------------

    def observations(
        self,
        dataset_id: str,
        *,
        geography: str | int,
        dates: list[str] | tuple[str, ...],
        dimensions: dict[str, str | int],
        measure: int = MEASURE_VALUE,
        require_all_dimensions_pinned: bool = True,
    ) -> tuple[Observation, ...]:
        """Fetch one fully-pinned selection as a single query.

        Every dimension must be pinned. NOMIS defaults an omitted dimension to ALL of its
        codes, and each dimension contains its own total, so an omission does not merely
        widen the answer - it mixes totals with the parts that make them up. One bare call
        on the population dataset for England in 2021 returned 726 rows for what the
        caller believed was one number.

        Raises if the response is truncated. A district-level pull came back 26MB with
        ``header.truncated == "true"``, 23,958 rows and no error; a capped response is a
        mutilated one and must not be treated as the answer.
        """

        if not dates:
            raise ValueError(
                "dates must not be empty; an unpinned date returns every published period"
            )

        required = set(self.selectable_dimensions(dataset_id))
        pinned = {key.lower() for key in dimensions}
        if require_all_dimensions_pinned and (missing := sorted(required - pinned)):
            raise NomisError(
                f"unpinned dimensions {missing} for {dataset_id}; NOMIS defaults these to "
                "every code, and each one carries a total alongside its own parts, so the "
                "result would mix aggregates with the rows that make them up"
            )
        if unknown := sorted(pinned - required):
            raise NomisError(
                f"dimensions {unknown} are not part of {dataset_id}; NOMIS accepts unknown "
                "query keys silently and returns no rows, which is indistinguishable from "
                "'no such data'"
            )

        params: dict[str, str | int] = {
            "geography": geography,
            "date": ",".join(str(item) for item in dates),
            "measures": measure,
        }
        for key, value in dimensions.items():
            params[key.lower()] = value

        payload = self._get(f"/dataset/{dataset_id}.data.json", params)
        header = payload.get("header", {})
        if str(header.get("truncated", "false")).lower() == "true":
            raise NomisError(
                f"NOMIS truncated the response for {dataset_id}; the rows returned are an "
                "arbitrary prefix of the selection, not the answer to it. Narrow the "
                "geography or date selection and query again."
            )

        rows = payload.get("obs") or []
        parsed: list[Observation] = []
        for row in rows:
            geo = row.get("geography") or {}
            time_field = row.get("time") or {}
            status_field = row.get("obs_status") or {}
            status_code = str(status_field.get("value", ""))
            value = _parse_number((row.get("obs_value") or {}).get("value"))
            parsed.append(
                Observation(
                    dataset_id=dataset_id,
                    geography_code=str(geo.get("geogcode") or geo.get("value") or ""),
                    geography_name=str(geo.get("description", "")),
                    period=_date_period(
                        time_field.get("value", ""), time_field.get("description", "")
                    ),
                    measure=str((row.get("measures") or {}).get("description", "")),
                    dimensions={
                        key: str((row[key] or {}).get("description", ""))
                        for key in sorted(required)
                        if isinstance(row.get(key), dict)
                    },
                    # A non-normal status means the cell is not a published figure. It is
                    # recorded as MISSING rather than carried through as a usable number,
                    # because a disclosure-controlled cell coerced to its printed value is
                    # a fabrication.
                    value=value if status_code == _NORMAL_STATUS else None,
                    status=str(status_field.get("description", "")),
                )
            )
        return tuple(parsed)

    def series(
        self,
        dataset_id: str,
        *,
        geography: str | int,
        dates: list[str] | tuple[str, ...],
        dimensions: dict[str, str | int],
        measure: int = MEASURE_VALUE,
        name: str | None = None,
    ) -> Series:
        """One stratum over time, or a refusal.

        Refuses unless the selection yields exactly one row per requested period. More than
        one row means something was not actually pinned - which is how a nested geography
        or a lurking total gets into a series - and fewer means a period is absent, which
        is a hole and not a zero.
        """

        observations = self.observations(
            dataset_id,
            geography=geography,
            dates=dates,
            dimensions=dimensions,
            measure=measure,
        )
        by_period: dict[str, list[Observation]] = {}
        for item in observations:
            by_period.setdefault(item.period.code, []).append(item)

        if duplicated := sorted(key for key, rows in by_period.items() if len(rows) > 1):
            raise NomisError(
                f"selection is not a single stratum: periods {duplicated} returned more "
                "than one row. Either a dimension is unpinned or the geography selector "
                "covers several nested areas; summing them would double-count."
            )
        wanted = [str(item) for item in dates]
        if absent := [code for code in wanted if code not in by_period]:
            raise NomisError(
                f"no rows for periods {absent}; an absent period is missing data, not a "
                "value of zero, and must not be filled in"
            )

        ordered = tuple(by_period[code][0] for code in wanted)
        first = ordered[0]
        stratum = ", ".join(value for _, value in sorted(first.dimensions.items()) if value)
        return Series(
            dataset_id=dataset_id,
            name=name
            or f"NOMIS {dataset_id} - {first.geography_name}"
            + (f" ({stratum})" if stratum else ""),
            geography_name=first.geography_name,
            observations=ordered,
        )
