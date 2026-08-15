"""Fingertips (OHID / former PHE) public health profiles.

Workstream W02 needs NHS referral, diagnosis and service-pathway measures, but
individual-level NHS data is access-gated. Fingertips publishes the *aggregate*
counterpart openly and keylessly: dated, area-level indicator series including self-harm
hospital admissions, children and young people's mental health, and the population
denominators those rates are built on. That cannot substitute for individual records, but
it is exactly the rate-level evidence the ascertainment propositions are calibrated
against.

Everything in this module exists to stop four specific ways this data lies to you:

1. Fingertips marks missing values by an *empty* ``Value`` with an explanatory
   ``Value note`` (disclosure-control suppression, trust data-quality exclusions,
   non-calculable values), and some payloads use ``-1``/``null``. None of those is a zero.
   A series with a hole cannot become a calibration target - see :meth:`Series.observed`.
2. Every row set contains **overlapping aggregates**. ``Sex`` carries Persons alongside
   Male and Female; ``Age`` carries "All ages" alongside bands; ``Category Type`` carries
   deprivation deciles that re-partition the same population; and each area is emitted
   twice, once with a blank ``Parent Code`` and once nested under its parent. Summing any
   of these double-counts. This connector therefore never sums - it selects one
   stratum and refuses if the selection is not unique.
3. Time fields do not all mean the same thing. See :class:`TimePeriod`.
4. The API is a public service with no key and no published quota, so requests are
   throttled by default.
"""

from __future__ import annotations

import csv
import io
import re
import time
from dataclasses import dataclass, field

import httpx

from oslt_research.governance.mechanism_simulation import ObservedSeries

#: Not in the source register yet; declared explicitly rather than borrowed from a
#: neighbouring DS number, so a downstream provenance check fails loudly instead of
#: attributing Fingertips data to some other dataset.
SOURCE_ID = "UNREGISTERED:OHID-FINGERTIPS"

BASE_URL = "https://fingertips.phe.org.uk/api"

#: England as a whole. Fingertips area type 15. Kept as a constant because mixing England
#: rows with region or local-authority rows in one series is the overlapping-aggregate
#: mistake in its most tempting form.
ENGLAND_AREA_TYPE_ID = 15
ENGLAND_AREA_CODE = "E92000001"

#: Indicators prioritised for W02. IDs verified live against the Fingertips API.
PRIORITY_INDICATORS: dict[str, int] = {
    "self_harm_admissions_all_ages": 21001,
    "self_harm_admissions_10_to_24": 90813,
    "self_harm_emergency_admissions_isr": 93239,
    "suicide_rate": 41001,
    "suicide_rate_by_age_and_sex": 93972,
    "years_of_life_lost_suicide": 91404,
}

#: Values that Fingertips uses to mean "no number here". ``-1`` is the sentinel seen in
#: the JSON surfaces; an empty string is what the CSV surface emits. Both are MISSING.
_MISSING_SENTINELS = {-1.0}


class FingertipsError(RuntimeError):
    """Raised when the API cannot be trusted to have answered the question asked."""


@dataclass(frozen=True)
class TimePeriod:
    """One Fingertips reporting period, with its basis made explicit.

    Three distinct fields look like dates and are not interchangeable:

    * ``Time period`` - the human label of the period the data *measures*
      ("2020/21", "2001 - 03", "2016/17 - 20/21").
    * ``Time period Sortable`` - an ordering key of the form ``YYYY0000``. It is the
      *start* year of the period, zero-padded; it is a sort key, not a date, and it does
      not encode the period's length.
    * indicator metadata publication/revision dates - when OHID *published* the figure.
      They describe the release, never the measurement window, and are deliberately not
      used to place a point on the time axis.

    ``year_type`` comes from indicator metadata (``Financial`` or ``Calendar``). A label
    like "2020/21" under a Financial year type runs April-March; coercing it to calendar
    2020 or 2021 would silently shift the whole series, so the raw label is preserved and
    :attr:`start_year` is only ever the *start* of the window.

    ``span_years`` > 1 means the point pools several years (rolling three- or five-year
    windows are common for suicide indicators). Consecutive pooled points overlap and are
    therefore not independent observations - :meth:`Series.observed` records this rather
    than hiding it.
    """

    label: str
    sortable: str
    year_type: str = "Unknown"
    span_years: int = 1

    @property
    def start_year(self) -> int | None:
        """First calendar year touched by the window, from the sortable key."""

        match = re.match(r"^(\d{4})", self.sortable or "")
        return int(match.group(1)) if match else None

    @property
    def is_financial(self) -> bool:
        return self.year_type.lower().startswith("financial")

    @property
    def is_pooled(self) -> bool:
        return self.span_years > 1


@dataclass(frozen=True)
class Observation:
    """A single Fingertips cell, with missingness kept as missingness."""

    indicator_id: int
    indicator_name: str
    area_code: str
    area_name: str
    area_type: str
    sex: str
    age: str
    category_type: str
    category: str
    period: TimePeriod
    value: float | None
    count: float | None
    denominator: float | None
    value_note: str

    @property
    def missing(self) -> bool:
        return self.value is None


@dataclass(frozen=True)
class Series:
    """An ordered, single-stratum series for one indicator in one area."""

    indicator_id: int
    indicator_name: str
    area_code: str
    area_name: str
    sex: str
    age: str
    year_type: str
    observations: tuple[Observation, ...] = field(default_factory=tuple)

    @property
    def missing_periods(self) -> tuple[str, ...]:
        return tuple(item.period.label for item in self.observations if item.missing)

    @property
    def complete(self) -> bool:
        """A suppressed or excluded cell is a hole, and a hole is not a zero."""

        return bool(self.observations) and not self.missing_periods

    @property
    def pooled(self) -> bool:
        return any(item.period.is_pooled for item in self.observations)

    def observed(self, *, allow_pooled: bool = False) -> ObservedSeries:
        """Convert to a calibration target, or refuse.

        Refusal is the point. A disclosure-suppressed local authority coerced to 0.0 puts
        a fabricated trough into the very series a mechanism is being tested against, and
        the mechanism that best reproduces a fabricated trough is the wrong mechanism.
        """

        if not self.observations:
            raise FingertipsError("series is empty; nothing to calibrate against")
        if not self.complete:
            raise FingertipsError(
                f"series has missing periods ({', '.join(self.missing_periods)}); a "
                "suppressed or excluded value is not a zero and must not be calibrated "
                "against"
            )
        if self.pooled and not allow_pooled:
            raise FingertipsError(
                "series uses pooled multi-year periods, so consecutive points share "
                "underlying years and are not independent observations; pass "
                "allow_pooled=True only if the calibration accounts for that overlap"
            )
        return ObservedSeries(
            name=f"{self.indicator_name} - {self.area_name} ({self.sex}, {self.age})",
            source_id=SOURCE_ID,
            values=tuple(float(item.value) for item in self.observations),  # type: ignore[arg-type]
            periods=tuple(item.period.label for item in self.observations),
        )


def _parse_number(raw: str | float | int | None) -> float | None:
    """Return a float, or None for anything that means "no value here"."""

    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not text or text in {"-", "*", "n/a", "NA"}:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
    else:
        value = float(raw)
    return None if value in _MISSING_SENTINELS else value


def _span_years(label: str) -> int:
    """Infer how many years a period label pools.

    "2020/21" is one financial year. "2001 - 03" and "2016/17 - 20/21" pool three and five
    years respectively. Getting this wrong makes overlapping windows look like independent
    annual points.
    """

    text = (label or "").strip()
    match = re.match(r"^\s*(\d{4})(?:/\d{2})?\s*-\s*(\d{2,4})", text)
    if not match:
        return 1
    start = int(match.group(1))
    tail = match.group(2)
    end = int(tail) if len(tail) == 4 else (start // 100) * 100 + int(tail)
    if end < start:
        end += 100
    return max(1, end - start + 1)


class FingertipsConnector:
    """Keyless client for dated aggregate public health indicator series.

    Deliberately narrow: it retrieves one indicator at one area type, then lets the caller
    pull out exactly one stratum as a series. It never aggregates across sexes, ages,
    category types or geographic levels, because every one of those axes in Fingertips
    contains a total sitting alongside its own parts.
    """

    source_name = "Fingertips (OHID)"
    connector_version = "1"
    base_url = BASE_URL

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 120.0,
        min_interval_seconds: float = 1.0,
    ):
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    # -- plumbing ---------------------------------------------------------------

    def _throttle(self) -> None:
        """A public service with no key still has finite capacity."""

        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _get(self, path: str, params: dict[str, str | int]) -> httpx.Response:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._throttle()
            response = client.get(f"{self.base_url}{path}", params=params)
            response.raise_for_status()
            return response
        finally:
            if self._client is None:
                client.close()

    # -- discovery --------------------------------------------------------------

    def search_indicators(self, search_text: str) -> dict[int, tuple[int, ...]]:
        """Return {area_type_id: indicator_ids} for a free-text search.

        Verified live that the API honours the term rather than discarding it: "mental
        health" and "self-harm" return different, differently sized id sets.
        """

        if not search_text.strip():
            raise ValueError("search_text must not be empty; a blank term is not a query")
        payload = self._get("/indicator_search", {"search_text": search_text}).json()
        if not isinstance(payload, dict):
            raise FingertipsError("indicator_search did not return the expected mapping")
        return {
            int(area_type): tuple(int(i) for i in ids)
            for area_type, ids in payload.items()
            if isinstance(ids, list)
        }

    def indicator_metadata(self, indicator_ids: list[int]) -> dict[int, dict]:
        """Metadata per indicator; the only trustworthy source of the year basis."""

        if not indicator_ids:
            raise ValueError("indicator_ids must not be empty")
        payload = self._get(
            "/indicator_metadata/by_indicator_id",
            {"indicator_ids": ",".join(str(i) for i in indicator_ids)},
        ).json()
        return {int(key): value for key, value in payload.items()}

    def year_type(self, indicator_id: int) -> str:
        meta = self.indicator_metadata([indicator_id]).get(indicator_id, {})
        year_type = meta.get("YearType") or {}
        return str(year_type.get("Name") or "Unknown")

    def available_area_types(self, indicator_id: int) -> tuple[int, ...]:
        """Area types this indicator is actually published at.

        Asking for a level the indicator is not published at returns an empty CSV, which
        is indistinguishable from "no data" unless you check first.
        """

        payload = self._get("/available_data", {"indicator_id": indicator_id}).json()
        return tuple(
            int(row["AreaTypeId"])
            for row in payload
            if isinstance(row, dict) and "AreaTypeId" in row
        )

    # -- data -------------------------------------------------------------------

    def observations(
        self,
        *,
        indicator_id: int,
        child_area_type_id: int = ENGLAND_AREA_TYPE_ID,
        parent_area_type_id: int = ENGLAND_AREA_TYPE_ID,
        year_type: str | None = None,
    ) -> tuple[Observation, ...]:
        """All published cells for one indicator at one geographic level.

        Fingertips emits each area twice - once with a blank ``Parent Code`` and once
        nested under its parent - so identical rows are de-duplicated here. Anything that
        summed the raw rows would double every figure.
        """

        response = self._get(
            "/all_data/csv/by_indicator_id",
            {
                "indicator_ids": indicator_id,
                "child_area_type_id": child_area_type_id,
                "parent_area_type_id": parent_area_type_id,
            },
        )
        basis = year_type if year_type is not None else "Unknown"
        rows = csv.DictReader(io.StringIO(response.text))
        seen: set[tuple] = set()
        parsed: list[Observation] = []
        for row in rows:
            label = (row.get("Time period") or "").strip()
            observation = Observation(
                indicator_id=int(row.get("Indicator ID") or indicator_id),
                indicator_name=(row.get("Indicator Name") or "").strip(),
                area_code=(row.get("Area Code") or "").strip(),
                area_name=(row.get("Area Name") or "").strip(),
                area_type=(row.get("Area Type") or "").strip(),
                sex=(row.get("Sex") or "").strip(),
                age=(row.get("Age") or "").strip(),
                category_type=(row.get("Category Type") or "").strip(),
                category=(row.get("Category") or "").strip(),
                period=TimePeriod(
                    label=label,
                    sortable=(row.get("Time period Sortable") or "").strip(),
                    year_type=basis,
                    span_years=_span_years(label),
                ),
                value=_parse_number(row.get("Value")),
                count=_parse_number(row.get("Count")),
                denominator=_parse_number(row.get("Denominator")),
                value_note=(row.get("Value note") or "").strip(),
            )
            key = (
                observation.area_code,
                observation.sex,
                observation.age,
                observation.category_type,
                observation.category,
                observation.period.sortable,
                observation.period.label,
                observation.value,
            )
            if key in seen:
                continue
            seen.add(key)
            parsed.append(observation)
        return tuple(parsed)

    def series(
        self,
        *,
        indicator_id: int,
        area_code: str = ENGLAND_AREA_CODE,
        child_area_type_id: int = ENGLAND_AREA_TYPE_ID,
        parent_area_type_id: int = ENGLAND_AREA_TYPE_ID,
        sex: str = "Persons",
        age: str | None = None,
        year_type: str | None = None,
        observations: tuple[Observation, ...] | None = None,
    ) -> Series:
        """One indicator, one area, one sex, one age band, ordered in time.

        The stratum is pinned explicitly and the result must be one row per period. If it
        is not, the selection straddles overlapping aggregates (a deprivation-decile
        breakdown, an extra age band) and the method raises rather than picking one
        arbitrarily or - far worse - averaging them.
        """

        basis = year_type if year_type is not None else self.year_type(indicator_id)
        rows = (
            observations
            if observations is not None
            else self.observations(
                indicator_id=indicator_id,
                child_area_type_id=child_area_type_id,
                parent_area_type_id=parent_area_type_id,
                year_type=basis,
            )
        )
        # Category Type must be blank: non-blank rows are deprivation-decile partitions of
        # the same people, so keeping them alongside the headline row duplicates it.
        candidates = [
            row
            for row in rows
            if row.area_code == area_code and row.sex == sex and not row.category_type
        ]
        if age is not None:
            candidates = [row for row in candidates if row.age == age]
        else:
            ages = {row.age for row in candidates}
            if len(ages) > 1:
                raise FingertipsError(
                    f"indicator {indicator_id} is published for several age bands "
                    f"({', '.join(sorted(ages))}); pass age= to pick one rather than "
                    "mixing overlapping populations"
                )
        if not candidates:
            raise FingertipsError(
                f"no rows for indicator {indicator_id} at area {area_code} "
                f"(sex={sex}, age={age}); check available_area_types first"
            )

        by_period: dict[str, list[Observation]] = {}
        for row in candidates:
            by_period.setdefault(row.period.sortable or row.period.label, []).append(row)
        duplicated = [key for key, group in by_period.items() if len(group) > 1]
        if duplicated:
            raise FingertipsError(
                f"more than one row per period ({', '.join(sorted(duplicated))}); the "
                "selected stratum is not unique and summing or averaging it would "
                "double-count overlapping aggregates"
            )

        ordered = tuple(
            group[0] for _, group in sorted(by_period.items(), key=lambda item: item[0])
        )
        first = ordered[0]
        return Series(
            indicator_id=first.indicator_id,
            indicator_name=first.indicator_name,
            area_code=first.area_code,
            area_name=first.area_name,
            sex=first.sex,
            age=first.age,
            year_type=basis,
            observations=ordered,
        )
