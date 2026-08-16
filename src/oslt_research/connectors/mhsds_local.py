"""Local-file reader for the MHSDS monthly statistics time series.

Workstream W02 (NHS referrals, diagnoses and service pathways) needs a long, England-level
monthly count of referrals and service access. The Mental Health Services Data Set monthly
statistics publish exactly that, back to April 2016, and this module reads it.

Why this module never touches the network
-----------------------------------------

Every MHSDS data file is served from ``files.digital.nhs.uk``, whose ``robots.txt`` has read
``User-agent: * / Disallow: /`` since 2018. :mod:`oslt_research.connectors.nhs_statistics`
declines that host in code (:func:`~oslt_research.connectors.nhs_statistics.guard_route`)
and that refusal stands: **nothing here fetches anything.** The founder authorised one
bounded, non-crawling retrieval of three NAMED files on 2026-08-16; the reasoning, the
bounds and the digests are recorded in ``docs/SOURCE_ACCESS_NOTES.md`` and
``data/mhsds_manifest.json``. Downloading is a deliberate, human-directed act that happens
once; reading is what this module does, from disk, every time. Keeping the two apart is the
point - a reader that could re-fetch would turn a one-off authorisation into a standing one.

The archive is ~29MB compressed and ~660MB across five CSVs, so it is streamed member by
member and row by row, following the ``ons_population`` precedent, never loaded.

The five traps this file's shape is a response to
-------------------------------------------------

1. **A suppressed cell is MISSING, never zero.** MHSDS writes ``*`` (and the wider NHS
   marker zoo) where a count is too small to publish - which is precisely the region the
   ascertainment propositions live in. Read as ``0`` it does not lose a point, it
   *manufactures a trough*. Parsing goes through
   :func:`~oslt_research.connectors.nhs_statistics.parse_cell`, and
   :meth:`MhsdsSeries.to_observed_series` refuses a series containing one.

2. **Nothing sums across nesting levels.** One file carries ``England`` beside
   ``Commissioning Region``, ``ICB``, ``Sub ICB`` and ``Provider`` rows, and ``England``
   beside ``England; Age`` and ``England; Gender``. A selection is pinned to one
   ``(measure, breakdown, primary level, secondary level)`` stratum and raises if it is
   not exactly one row per month. It never adds two rows together.

3. **Two different windows share one measure id and one end date.** ``MHS32`` appears as
   "Referrals starting in RP" over a single month *and* as "New referrals" over a rolling
   three-month window ending in the same month. Selecting on the end date alone silently
   mixes a monthly count with a quarterly one - roughly a threefold step. Only rows whose
   start falls inside the same calendar month as their end are treated as monthly; see
   :func:`monthly_window`.

4. **``REPORTING_PERIOD_START`` is not consistently formatted.** Rows from the 2016-2023
   file write April 2016 as ``04/01/2016`` (month first) while the end date on the same row
   is ``30/04/2016`` (day first); later files write ``01/04/2026`` (day first). The end date
   is always a month end, so its day is always greater than 12 and it is unambiguous - it is
   the field this module trusts. The start is parsed under both readings only to classify
   the window, never to date the observation.

5. **MHSDS coverage more than quadrupled over the series.** Provider participation was
   voluntary and incomplete in the early years: about 91 providers submitted in 2016
   against about 420 in 2026, while the England headline roughly doubled. **A rise here can
   be a coverage artefact rather than a real rise, and the coverage ramp is larger than the
   trend.** :class:`MhsdsSeries` therefore carries provider coverage per month alongside the
   values, and :attr:`MhsdsSeries.coverage_warning` states the ratio, so a successor reading
   only the numbers cannot avoid seeing it.

What this data is not
---------------------

MHSDS covers NHS-funded secondary mental health, learning disability and autism services.
**It carries no gender-service, gender-dysphoria or gender-identity-clinic referral
measure** - a full scan of all 121 England-level measures in the June 2026 archive found
none. Gender services are commissioned separately and are not in scope of this collection.
There *is* an ``England; Gender`` breakdown, but that is the patient's recorded gender
(male / female / non-binary / other / indeterminate / unknown) applied to general mental
health activity. It is a demographic split of mental health contacts, not a count of people
referred to gender services, and it must never be presented as one. MHSDS is a strong
**comparator** for W02 - a general-population service-access denominator against which a
specific referral series can be read - and nothing more.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from oslt_research.connectors.nhs_statistics import SUPPRESSION_MARKERS, parse_cell
from oslt_research.governance.mechanism_simulation import ObservedSeries

#: DS077 in the source register. The row records the two limits that decide how this may be
#: used: MHSDS carries NO gender-service measure, and its provider coverage ramps ~4.6x
#: across the series so an early-year rise may be ascertainment rather than incidence.
SOURCE_ID = "DS077"

#: Where the founder-authorised download is placed. Gitignored: the files are large and
#: freely re-downloadable, and ``data/mhsds_manifest.json`` records the digests instead.
DEFAULT_DATA_DIR = Path("runtime/mhsds")

#: The single highest-value artefact: Apr 2016 to Jun 2026 monthly, five CSVs in one zip.
DEFAULT_ARCHIVE = DEFAULT_DATA_DIR / "MHSDS Time_Series_data_Apr_2016_Jun_2026_Perf.zip"

#: Breakdown labels. ``England`` is the pinned stratum for a national series; the others
#: are its own parts and are listed so that a caller can see what must NOT be added to it.
BREAKDOWN_ENGLAND = "England"
BREAKDOWN_ENGLAND_AGE = "England; Age"
BREAKDOWN_ENGLAND_GENDER = "England; Gender"
BREAKDOWN_PROVIDER = "Provider"

#: Measures W02 actually asked for.
#:
#: ``MHS01`` runs the full Apr-2016-to-date span and is the service-ACCESS measure (a stock:
#: people with an open referral at the period end). ``MHS32`` is the referral FLOW (new
#: referrals starting in the period) but is only published at England level from April 2022,
#: so it is the shorter and the more directly comparable of the two. They are different
#: quantities and must not be spliced.
MEASURE_OPEN_REFERRALS = "MHS01"
MEASURE_NEW_REFERRALS = "MHS32"
MEASURE_CONTACTS = "MHS29"

#: Column names in the time-series CSVs.
_COL_START = "REPORTING_PERIOD_START"
_COL_END = "REPORTING_PERIOD_END"
_COL_STATUS = "STATUS"
_COL_BREAKDOWN = "BREAKDOWN"
_COL_PRIMARY = "PRIMARY_LEVEL"
_COL_PRIMARY_DESC = "PRIMARY_LEVEL_DESCRIPTION"
_COL_SECONDARY = "SECONDARY_LEVEL"
_COL_SECONDARY_DESC = "SECONDARY_LEVEL_DESCRIPTION"
_COL_MEASURE_ID = "MEASURE_ID"
_COL_MEASURE_NAME = "MEASURE_NAME"
_COL_VALUE = "MEASURE_VALUE"

REQUIRED_COLUMNS = frozenset(
    {_COL_START, _COL_END, _COL_BREAKDOWN, _COL_PRIMARY, _COL_MEASURE_ID, _COL_VALUE}
)

#: The English financial year starts in April. Used only to LABEL a month with the
#: financial year it falls in - never to collapse twelve months into one number.
_FINANCIAL_YEAR_START_MONTH = 4

_MONTH_ABBR = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


class MhsdsDataError(RuntimeError):
    """Raised when MHSDS data cannot be trusted to mean what it appears to mean."""


# --------------------------------------------------------------------------------------
# Periods
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MhsdsMonth:
    """One reporting month, with the published date strings kept verbatim beside it.

    ``label`` is ``YYYY-MM`` because it must sort correctly on a time axis and because a
    month is what MHSDS actually measures. :attr:`financial_year` is offered separately, as
    a label, so that a caller can group by financial year deliberately. Nothing here turns
    "2023/24" into 2023: an English financial year runs April to March and is not a calendar
    year, and coercing one into the other shifts a series by up to nine months without
    anything looking wrong.
    """

    year: int
    month: int
    period_start_raw: str = ""
    period_end_raw: str = ""
    basis: str = "reporting_month"

    @property
    def label(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def display(self) -> str:
        return f"{_MONTH_ABBR[self.month - 1]} {self.year}"

    @property
    def financial_year(self) -> str:
        """The English financial year this month falls in, e.g. ``2016/17``."""

        start = self.year if self.month >= _FINANCIAL_YEAR_START_MONTH else self.year - 1
        return f"{start:04d}/{(start + 1) % 100:02d}"

    @property
    def ordinal(self) -> int:
        """Months since year zero. Only used to test contiguity, never exposed as a date."""

        return self.year * 12 + (self.month - 1)

    def __lt__(self, other: MhsdsMonth) -> bool:
        return self.ordinal < other.ordinal


def _parse_end(value: str) -> datetime:
    """Parse ``REPORTING_PERIOD_END``, which is always a month end and so unambiguous.

    Every end date in the published series is the last day of a month, so its day component
    is 28 or greater and cannot be mistaken for a month. That is the only reason this field
    can be parsed with confidence while the start field cannot.
    """

    text = (value or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if parsed.day < 13:
            raise MhsdsDataError(
                f"reporting period end {text!r} has a day of {parsed.day}, which is also a "
                "valid month; a published MHSDS period always ends on a month end, so this "
                "row cannot be dated without guessing"
            )
        return parsed
    raise MhsdsDataError(f"cannot parse reporting period end {text!r}")


def monthly_window(start: str, end: str) -> MhsdsMonth | None:
    """Return the month a row covers, or ``None`` if the row is not a single month.

    MHSDS publishes ``MHS32`` twice for the same end date: once over the month, and once
    over the rolling three months ending in it. The rolling figure is roughly three times
    the monthly one, so mixing them produces a step change that looks like a real event.

    The end date is authoritative. The start is parsed under BOTH day-first and month-first
    readings, because the archive genuinely contains both conventions, and the row counts as
    monthly if *either* reading lands in the same calendar month as the end. A rolling
    window lands in neither, so the test separates them cleanly without having to decide
    which convention a given file used.
    """

    end_dt = _parse_end(end)
    text = (start or "").strip()
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            start_dt = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if (start_dt.year, start_dt.month) == (end_dt.year, end_dt.month):
            return MhsdsMonth(
                year=end_dt.year,
                month=end_dt.month,
                period_start_raw=text,
                period_end_raw=(end or "").strip(),
            )
    return None


# --------------------------------------------------------------------------------------
# Cells
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MhsdsCell:
    """One published MHSDS figure with its stratum carried alongside it.

    :attr:`stratum` deliberately keys on ``measure_id`` and NOT on ``measure_name``. NHS
    England renamed ``MHS01`` from "People in contact with services at the end of the
    reporting period" to "People with an open referral with services at the end of the
    reporting period" partway through the series. Keying on the name would split one series
    into two strata; ignoring the rename entirely would hide a definition change. So the id
    pins the stratum and every name seen is retained on the series
    (:attr:`MhsdsSeries.measure_names_observed`) for the reader to judge.
    """

    measure_id: str
    measure_name: str
    breakdown: str
    primary_level: str
    primary_level_description: str
    secondary_level: str
    secondary_level_description: str
    status: str
    month: MhsdsMonth
    value: float | None
    raw_value: str

    @property
    def missing(self) -> bool:
        return self.value is None

    @property
    def suppressed(self) -> bool:
        """True when the publisher wrote a suppression marker rather than left it blank."""

        return self.raw_value.strip().lower() in SUPPRESSION_MARKERS

    @property
    def stratum(self) -> tuple[str, str, str, str]:
        return (self.measure_id, self.breakdown, self.primary_level, self.secondary_level)


# --------------------------------------------------------------------------------------
# Series
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MhsdsSeries:
    """A pinned, single-stratum monthly series with its coverage carried beside it.

    The coverage mapping is not decoration. MHSDS provider participation grew from about 91
    submitting providers in 2016 to about 420 in 2026 - a larger multiple than the growth in
    the headline counts over the same span. Any conclusion drawn from the level or the slope
    of this series that does not account for that is an artefact. Coverage travels with the
    numbers so that it cannot be dropped by accident.
    """

    measure_id: str
    breakdown: str
    primary_level: str
    secondary_level: str
    cells: tuple[MhsdsCell, ...]
    coverage_by_month: dict[str, int | None] = field(default_factory=dict)

    @property
    def months(self) -> tuple[MhsdsMonth, ...]:
        return tuple(cell.month for cell in self.cells)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(cell.month.label for cell in self.cells)

    @property
    def financial_years(self) -> tuple[str, ...]:
        return tuple(cell.month.financial_year for cell in self.cells)

    @property
    def measure_names_observed(self) -> tuple[str, ...]:
        return tuple(sorted({cell.measure_name for cell in self.cells if cell.measure_name}))

    @property
    def statuses_observed(self) -> tuple[str, ...]:
        return tuple(sorted({cell.status for cell in self.cells if cell.status}))

    @property
    def missing_months(self) -> tuple[str, ...]:
        return tuple(cell.month.label for cell in self.cells if cell.missing)

    @property
    def coverage_warning(self) -> str | None:
        """A one-line statement of the coverage ramp, or ``None`` if it cannot be measured.

        Returned as text rather than a flag because the number is the argument: a reader who
        sees "coverage rose 4.6x while the series rose 2.0x" does not need to be told what to
        conclude, and a reader who sees only a boolean will ignore it.
        """

        # Months whose coverage is unknown are dropped rather than treated as zero, so the
        # span quoted is the span coverage was actually measured over, not the whole series.
        measured = [
            (label, self.coverage_by_month[label])
            for label in self.labels
            if self.coverage_by_month.get(label) is not None
        ]
        if len(measured) < 2 or not measured[0][1]:
            return None
        counts = [count for _label, count in measured]
        ratio = counts[-1] / counts[0]  # type: ignore[operator]
        span = {measured[0][0], measured[-1][0]}
        values = [cell.value for cell in self.cells if cell.value and cell.month.label in span]
        trend = (
            f"; the series itself changed {values[-1] / values[0]:.2f}x over the same span"
            if len(values) == 2 and values[0]
            else ""
        )
        return (
            f"submitting providers went from {counts[0]} to {counts[-1]} ({ratio:.2f}x) "
            f"across {measured[0][0]}-{measured[-1][0]}{trend}. MHSDS provider "
            "participation was incomplete in the early years, so part or all of any rise "
            "here may be ascertainment rather than incidence."
        )

    def to_observed_series(self, *, name: str | None = None) -> ObservedSeries:
        """Build a calibration target, or refuse and say why.

        Four refusals, each from a way this project has already been burned:

        1. **Mixed strata.** England beside its own regions, or "All ages" beside an age
           band, cannot be combined without double counting.
        2. **More than one row per month.** A duplicate month means the selection is not
           what the caller thinks - a revision beside an original, or a rolling window
           beside a monthly one.
        3. **A gap in the months.** A month with no row is a month with no data, and
           bridging it invents a trend segment.
        4. **Any hole.** A suppressed cell is MISSING, never zero. It is better to have no
           W02 series than a W02 series with an invented dip.
        """

        if not self.cells:
            raise MhsdsDataError("no cells selected; there is nothing to calibrate against")

        strata = {cell.stratum for cell in self.cells}
        if len(strata) > 1:
            rendered = "; ".join(" / ".join(item) for item in sorted(strata))
            raise MhsdsDataError(
                f"selection spans {len(strata)} strata ({rendered}); MHSDS carries England "
                "beside its own regions, ICBs and providers, and 'all' beside age bands, so "
                "these must never be combined - pin one stratum"
            )

        seen: dict[str, int] = defaultdict(int)
        for cell in self.cells:
            seen[cell.month.label] += 1
        duplicated = sorted(label for label, count in seen.items() if count > 1)
        if duplicated:
            raise MhsdsDataError(
                f"more than one row for month(s) {', '.join(duplicated)}; MHSDS publishes a "
                "monthly and a rolling-quarter figure under the same measure id and end "
                "date, so collapsing this would mix two different windows"
            )

        ordered = sorted(self.cells, key=lambda cell: cell.month.ordinal)
        expected = ordered[-1].month.ordinal - ordered[0].month.ordinal + 1
        if len(ordered) != expected:
            present = {cell.month.ordinal for cell in ordered}
            gaps = [
                MhsdsMonth(year=value // 12, month=value % 12 + 1).label
                for value in range(ordered[0].month.ordinal, ordered[-1].month.ordinal + 1)
                if value not in present
            ]
            raise MhsdsDataError(
                f"series has no row for month(s) {', '.join(gaps)}; a missing month is not "
                "an activity of zero and must not be interpolated or dropped silently"
            )

        missing = [cell.month.label for cell in ordered if cell.missing]
        if missing:
            raise MhsdsDataError(
                f"series has no value for {', '.join(missing)}; MHSDS suppresses small "
                "numbers and a suppressed cell is MISSING, never 0 - refusing to build a "
                "series with holes"
            )

        first = ordered[0]
        stratum_label = first.primary_level_description or first.primary_level
        if first.secondary_level and first.secondary_level.upper() != "NONE":
            stratum_label += f", {first.secondary_level_description or first.secondary_level}"
        return ObservedSeries(
            name=name or f"MHSDS {self.measure_id} - {stratum_label}",
            source_id=SOURCE_ID,
            values=tuple(float(cell.value) for cell in ordered),  # type: ignore[arg-type]
            periods=tuple(cell.month.label for cell in ordered),
        )


# --------------------------------------------------------------------------------------
# Reader
# --------------------------------------------------------------------------------------


class MhsdsLocalReader:
    """Streaming reader over a locally held MHSDS time-series archive.

    Performs **no network access of any kind**. The archive must already exist on disk,
    placed there by the founder-authorised retrieval recorded in
    ``data/mhsds_manifest.json``. If it is absent this raises rather than fetching, because
    a reader that could fill its own gap would convert a one-off authorisation into a
    standing one.

    Accepts either a ``.zip`` (streamed member by member) or a bare ``.csv``, so a test can
    exercise it without a fixture the size of the real thing.
    """

    source_name = "NHS England MHSDS monthly statistics (local files)"
    connector_version = "1"

    def __init__(self, archive_path: Path | str = DEFAULT_ARCHIVE) -> None:
        self.archive_path = Path(archive_path)

    # -- raw iteration ------------------------------------------------------------------

    def _members(self) -> Iterator[tuple[str, Iterator[dict[str, str]]]]:
        path = self.archive_path
        if not path.exists():
            raise MhsdsDataError(
                f"{path} is not present. This connector never downloads: the MHSDS files "
                "are obtained by the separate, founder-authorised retrieval recorded in "
                "data/mhsds_manifest.json and docs/SOURCE_ACCESS_NOTES.md, and placed under "
                f"{DEFAULT_DATA_DIR}."
            )
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".csv"):
                        continue
                    with archive.open(info) as handle:
                        text = io.TextIOWrapper(handle, encoding="utf-8-sig", newline="")
                        yield info.filename, csv.DictReader(text)
        else:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                yield path.name, csv.DictReader(handle)

    def iter_rows(self) -> Iterator[tuple[str, dict[str, str]]]:
        """Yield ``(member name, row)`` for every row in the archive, streaming.

        The archive is ~660MB uncompressed across five CSVs. Materialising it would make
        routine use impractical and would put a research laptop into swap, so nothing here
        builds a list.
        """

        for member, reader in self._members():
            checked = False
            for row in reader:
                if not checked:
                    missing = REQUIRED_COLUMNS - set(row)
                    if missing:
                        raise MhsdsDataError(
                            f"{member} is missing column(s) {', '.join(sorted(missing))}; "
                            "the published schema has changed and the selection logic here "
                            "can no longer be assumed to select the same thing"
                        )
                    checked = True
                yield member, row

    # -- cell selection -----------------------------------------------------------------

    def iter_cells(
        self,
        *,
        measure_ids: Iterable[str] | None = None,
        breakdowns: Iterable[str] | None = None,
        primary_level: str | None = None,
        secondary_level: str | None = None,
    ) -> Iterator[MhsdsCell]:
        """Yield monthly cells matching a filter. Non-monthly windows are dropped.

        Filters are applied on stripped values because the archive contains ``"Performance "``
        with a trailing space beside ``"Performance"``, and an exact-match filter would
        silently return a partial series.
        """

        wanted_measures = {item.strip() for item in measure_ids} if measure_ids else None
        wanted_breakdowns = {item.strip() for item in breakdowns} if breakdowns else None

        for _member, row in self.iter_rows():
            measure_id = (row.get(_COL_MEASURE_ID) or "").strip()
            if wanted_measures is not None and measure_id not in wanted_measures:
                continue
            breakdown = (row.get(_COL_BREAKDOWN) or "").strip()
            if wanted_breakdowns is not None and breakdown not in wanted_breakdowns:
                continue
            primary = (row.get(_COL_PRIMARY) or "").strip()
            if primary_level is not None and primary != primary_level:
                continue
            secondary = (row.get(_COL_SECONDARY) or "").strip()
            if secondary_level is not None and secondary != secondary_level:
                continue

            month = monthly_window(row.get(_COL_START, ""), row.get(_COL_END, ""))
            if month is None:
                # A rolling-quarter row. Dropped rather than raised, because the archive is
                # meant to carry both; mixing them is the error, not publishing them.
                continue

            raw = row.get(_COL_VALUE) or ""
            yield MhsdsCell(
                measure_id=measure_id,
                measure_name=(row.get(_COL_MEASURE_NAME) or "").strip(),
                breakdown=breakdown,
                primary_level=primary,
                primary_level_description=(row.get(_COL_PRIMARY_DESC) or "").strip(),
                secondary_level=secondary,
                secondary_level_description=(row.get(_COL_SECONDARY_DESC) or "").strip(),
                status=(row.get(_COL_STATUS) or "").strip(),
                month=month,
                value=parse_cell(raw),
                raw_value=str(raw),
            )

    # -- the W02 series -----------------------------------------------------------------

    def england_series(
        self,
        measure_id: str = MEASURE_NEW_REFERRALS,
        *,
        age_band: str | None = None,
        with_coverage: bool = True,
    ) -> MhsdsSeries:
        """England-level monthly series for one measure, optionally for one age band.

        One pass over the archive gathers both the series and the per-month count of
        submitting providers, because a second pass over 660MB to fetch the coverage would
        cost more than it is worth and the coverage must not be optional.

        ``age_band`` selects the ``England; Age`` breakdown - which is a DIFFERENT stratum
        from ``England``, not a subset that can be added back to it.
        """

        breakdown = BREAKDOWN_ENGLAND_AGE if age_band is not None else BREAKDOWN_ENGLAND
        wanted = {breakdown} | ({BREAKDOWN_PROVIDER} if with_coverage else set())

        cells: list[MhsdsCell] = []
        providers: dict[str, set[str]] = defaultdict(set)
        for cell in self.iter_cells(measure_ids=[measure_id], breakdowns=wanted):
            if cell.breakdown == BREAKDOWN_PROVIDER:
                if cell.primary_level:
                    providers[cell.month.label].add(cell.primary_level)
                continue
            if cell.primary_level != BREAKDOWN_ENGLAND:
                continue
            if age_band is not None and cell.secondary_level != age_band:
                continue
            cells.append(cell)

        ordered = sorted(cells, key=lambda cell: cell.month.ordinal)
        coverage: dict[str, int | None] = {}
        if with_coverage:
            # A month with no provider rows has UNKNOWN coverage, not zero coverage.
            coverage = {
                cell.month.label: (
                    len(providers[cell.month.label])
                    if cell.month.label in providers
                    else None
                )
                for cell in ordered
            }

        return MhsdsSeries(
            measure_id=measure_id,
            breakdown=breakdown,
            primary_level=BREAKDOWN_ENGLAND,
            secondary_level=age_band or "NONE",
            cells=tuple(ordered),
            coverage_by_month=coverage,
        )

    # -- discovery ----------------------------------------------------------------------

    def available_measures(self, *, breakdown: str = BREAKDOWN_ENGLAND) -> dict[str, set[str]]:
        """Map measure id to every measure NAME seen for it, at one breakdown level.

        Returns a set of names per id rather than one name, because a renamed measure is a
        definition-drift signal that a caller should see rather than have resolved for them.
        """

        found: dict[str, set[str]] = defaultdict(set)
        for cell in self.iter_cells(breakdowns=[breakdown]):
            found[cell.measure_id].add(cell.measure_name)
        return dict(found)

    def available_age_bands(self, measure_id: str = MEASURE_NEW_REFERRALS) -> set[str]:
        """Published ``England; Age`` bands for a measure. ``UNKNOWN`` is one of them."""

        return {
            cell.secondary_level
            for cell in self.iter_cells(
                measure_ids=[measure_id], breakdowns=[BREAKDOWN_ENGLAND_AGE]
            )
            if cell.secondary_level and cell.secondary_level.upper() != "NONE"
        }
