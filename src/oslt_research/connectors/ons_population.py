from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from oslt_research.governance.mechanism_simulation import ObservedSeries


#: W01 in the workstream register - population denominators and trend decomposition,
#: required by 42 of the 64 propositions and the single most demanded workstream.
#:
#: The ascertainment propositions are claims about RATES. Without a denominator a
#: referral count cannot be distinguished from a referral rate, and every one of them is
#: about exactly that distinction.
SOURCE_ID = "DS014"

#: The ONS mid-year estimates CSV is ~123MB and 2.35M rows. It is streamed and aggregated
#: rather than loaded, and cached locally, because re-downloading it per query would make
#: routine use impractical and hammer ONS for data that does not change.
DEFAULT_CACHE = Path("runtime/ons_population.csv")

#: The CSV contains OVERLAPPING AGGREGATES on two dimensions, and summing naively
#: triples the population. Leeds read as 2.86 million against a true figure near 800,000
#: before this was caught.
#:
#:   sex                 male, female, AND "all"
#:   single-year-of-age  0..89, "90+", AND "total"
#:
#: So the aggregate rows are used deliberately where they exist, and excluded otherwise.
#: A denominator that is wrong by a factor of three corrupts every rate built on it, and
#: nothing downstream would reveal it - the rates would simply look low.
AGGREGATE_SEX = "all"
AGGREGATE_AGE = "total"
OLDEST_BAND = "90+"

#: Columns in the mid-year-pop-est CSV. v4_0 is the observation value.
_VALUE = "v4_0"
_YEAR = "calendar-years"
_GEOGRAPHY_CODE = "administrative-geography"
_GEOGRAPHY_NAME = "Geography"
_SEX = "sex"
_AGE = "single-year-of-age"


@dataclass(frozen=True)
class PopulationSlice:
    """Population totals for one filtered slice, by year."""

    geography: str
    sex: str | None
    age_from: int | None
    age_to: int | None
    by_year: dict[int, int] = field(default_factory=dict)
    rows_read: int = 0
    rows_matched: int = 0

    @property
    def years(self) -> list[int]:
        return sorted(self.by_year)

    def to_observed_series(self) -> ObservedSeries:
        """Convert to a calibration target or a denominator series.

        Requires a contiguous run of years. A gap would be read downstream as a real
        change in population rather than an absence of data, which is the same error as
        letting a failed request become a zero.
        """

        years = self.years
        if len(years) < 3:
            raise ValueError("a population series needs at least three years")
        expected = list(range(years[0], years[-1] + 1))
        if years != expected:
            missing = sorted(set(expected) - set(years))
            raise ValueError(
                f"population series has gaps at {missing}; a missing year is not a "
                "population of zero and must not be interpolated silently"
            )
        return ObservedSeries(
            name=f"ONS population, {self.geography}, {self.sex or 'all sexes'}, "
            f"ages {self.age_from if self.age_from is not None else 'all'}"
            f"-{self.age_to if self.age_to is not None else 'all'}",
            source_id=SOURCE_ID,
            values=tuple(float(self.by_year[year]) for year in years),
            periods=tuple(str(year) for year in years),
        )


class OnsPopulationConnector:
    """Population denominators from ONS mid-year estimates.

    Streams the published CSV and aggregates to a requested slice, so a caller asks for
    "England, female, ages 10-17, by year" rather than handling 2.35 million rows.

    Deliberately does not interpolate, smooth or project. A denominator that has been
    modelled is no longer a denominator, and a rate built on one inherits the model's
    assumptions without recording them.

    Requires no API key.
    """

    source_name = "ONSPopulation"
    connector_version = "1"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        cache_path: Path | str = DEFAULT_CACHE,
        timeout: float = 300.0,
    ):
        self._client = client
        self.cache_path = Path(cache_path)
        self.timeout = timeout

    def download(self, csv_url: str, *, force: bool = False) -> Path:
        """Fetch the CSV once and cache it. Returns the cached path."""

        if self.cache_path.exists() and not force and self.cache_path.stat().st_size > 0:
            return self.cache_path

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        client = self._client or httpx.Client(timeout=self.timeout, follow_redirects=True)
        try:
            response = client.get(csv_url)
            response.raise_for_status()
            self.cache_path.write_bytes(response.content)
        finally:
            if self._client is None:
                client.close()
        return self.cache_path

    def slice_population(
        self,
        source: Path | str | io.StringIO,
        *,
        geography: str = "England",
        sex: str | None = None,
        age_from: int | None = None,
        age_to: int | None = None,
    ) -> PopulationSlice:
        """Aggregate the CSV to one slice, by year.

        Matching on the geography NAME rather than the code, because the code changes
        between editions when boundaries are redrawn while the name is stable. A caller
        asking for England across editions should not silently get nothing because a code
        was retired.
        """

        totals: dict[int, int] = defaultdict(int)
        rows_read = 0
        rows_matched = 0

        # Unfiltered means the published aggregate row, never a sum over the parts.
        # Summing male + female + "all" counts the population twice.
        wanted_sex = (sex or AGGREGATE_SEX).casefold()
        banded = age_from is not None or age_to is not None

        handle = source if isinstance(source, io.StringIO) else open(
            source, "r", encoding="utf-8", errors="replace", newline=""
        )
        try:
            for row in csv.DictReader(handle):
                rows_read += 1
                if row.get(_GEOGRAPHY_NAME, "").strip().casefold() != geography.casefold():
                    continue
                if row.get(_SEX, "").strip().casefold() != wanted_sex:
                    continue

                raw_age = row.get(_AGE, "").strip().casefold()
                if not banded:
                    # No age filter: take the published total, not a sum of single years.
                    if raw_age != AGGREGATE_AGE:
                        continue
                else:
                    if raw_age == AGGREGATE_AGE:
                        continue
                    if raw_age == OLDEST_BAND:
                        # An open-ended band belongs in the slice only when the requested
                        # range actually reaches it; otherwise it would add people the
                        # caller did not ask for.
                        if age_to is not None and age_to < 90:
                            continue
                        if age_from is not None and age_from > 90:
                            continue
                    else:
                        try:
                            age = int(raw_age)
                        except ValueError:
                            continue
                        if age_from is not None and age < age_from:
                            continue
                        if age_to is not None and age > age_to:
                            continue

                try:
                    year = int(row.get(_YEAR, "").strip())
                    value = int(float(row.get(_VALUE, "") or 0))
                except ValueError:
                    continue

                totals[year] += value
                rows_matched += 1
        finally:
            if not isinstance(source, io.StringIO):
                handle.close()

        return PopulationSlice(
            geography=geography,
            sex=sex,
            age_from=age_from,
            age_to=age_to,
            by_year=dict(totals),
            rows_read=rows_read,
            rows_matched=rows_matched,
        )
