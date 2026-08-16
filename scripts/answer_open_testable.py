"""Candidate findings for the 16 open-testable propositions.

Every proposition that :func:`oslt_research.governance.feasibility.assess_feasibility`
classifies as ``OPEN_TESTABLE`` now has all of its required workstreams in hand for the
first time. This script produces one candidate finding per proposition, writes
``docs/OPEN_TESTABLE_FINDINGS.md`` and ``data/open_testable_findings.json``, and refuses
to dress compatibility up as support.

Five rules are enforced here rather than remembered:

1. **Nothing is released.** ``governance/claim_release.py`` declines every claim pending
   human review and no human-coded lane exists, so these are candidates for an academic to
   adjudicate. The word "candidate" is in every artefact this writes.
2. **Compatibility is not support.** Where a mechanism is involved the verdict comes from
   ``governance/mechanism_simulation.compare_mechanisms``, whose asymmetry is deliberate:
   a refuted mechanism is WEAKENS, a compatible one is INCONCLUSIVE and never SUPPORTS.
3. **A hole is never a zero, a suppressed cell is missing, and a coverage ramp is not a
   trend.** The MHSDS work below restricts to providers submitting *continuously* rather
   than treating a non-submitting provider as an activity of zero.
4. **The ballot is unequal.** 12 of the 16 belong to ASCERTAINMENT_SERVICE and three model
   families have no open-testable proposition at all. A tally of "supported" propositions
   over this set measures data access, not explanatory merit, and the summary says so
   before it says anything else.
5. **An honest INCONCLUSIVE is a result.** Several of the 16 have their required
   workstreams and still cannot be answered, because the *predictor named in the
   prediction* is not something any required workstream carries. Those are recorded as
   INCONCLUSIVE with the specific missing measure named, not filled in.

Two inputs are expensive and are cached under ``runtime/`` on first run: one streaming
pass over the MHSDS archive, and the NOMIS population pull. Pass ``--force`` to re-read.
"""

from __future__ import annotations

import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from oslt_research.connectors.mhsds_local import (  # noqa: E402
    BREAKDOWN_ENGLAND,
    BREAKDOWN_ENGLAND_AGE,
    BREAKDOWN_PROVIDER,
    MEASURE_NEW_REFERRALS,
    MEASURE_OPEN_REFERRALS,
    MhsdsLocalReader,
)
from oslt_research.connectors.nomis import GEOGRAPHY_ENGLAND, NomisConnector  # noqa: E402
from oslt_research.domain.enums import (  # noqa: E402
    ClaimTier,
    FalsifierStatus,
    FindingDirection,
)
from oslt_research.governance.feasibility import assess_feasibility  # noqa: E402
from oslt_research.governance.mechanism_simulation import (  # noqa: E402
    MechanismCandidate,
    ObservedSeries,
    compare_mechanisms,
)

# --------------------------------------------------------------------------------------
# Paths and frozen selections
# --------------------------------------------------------------------------------------

REGISTRY_ROOT = REPO_ROOT / "registries"
DOC_OUT = REPO_ROOT / "docs" / "OPEN_TESTABLE_FINDINGS.md"
JSON_OUT = REPO_ROOT / "data" / "open_testable_findings.json"

MHSDS_CACHE = REPO_ROOT / "runtime" / "open_testable_mhsds.json"
POPULATION_CACHE = REPO_ROOT / "runtime" / "open_testable_population.json"

W09_PATH = REPO_ROOT / "data" / "w09_clinical_guidance.json"
FINGERTIPS_PATH = REPO_ROOT / "data" / "fingertips_w02.json"
COUPLING_PATH = REPO_ROOT / "data" / "coupling_readjudication.json"

#: The AS08 window. Chosen to be *exactly* the window of the withdrawn second comparator
#: in docs/REFERRAL_BASELINE.md (financial years 2017/18-2023/24), so that the answer
#: bears on that withdrawal rather than on a window picked to suit an outcome.
AS08_FIRST_MONTH = "2017-04"
AS08_LAST_MONTH = "2024-03"

#: The MHS01 measure NAME changed inside the archive, from "People in contact with
#: services at the end of the reporting period" to "People with an open referral with
#: services at the end of the reporting period". It is the only documented definition-label
#: change in the archive and is therefore the AS03 test point. It was located by scanning
#: the archive, not chosen: see ``measure_rename_month`` in the JSON output.
AS03_WINDOW_FIRST = "2025-01"
AS03_WINDOW_LAST = "2026-06"

#: AS06 compares two complete financial years of MHS32 (the referral FLOW measure, which
#: is only published at England level from April 2022). Population years are the calendar
#: years in which each financial year begins - ONS mid-year estimates are as at 30 June,
#: which falls inside the financial year.
AS06_YEAR_ONE = ("2022-04", "2023-03", "2022")
AS06_YEAR_TWO = ("2024-04", "2025-03", "2024")

#: NOMIS NM_2002_1 c_age codes. Disjoint and exhaustive - code 200 ("All Ages") is carried
#: only as a reconciliation check and is never summed with the parts.
POPULATION_BANDS: dict[str, str] = {
    "0_15": "201",
    "16_17": "204",
    "18_24": "205",
    "25_49": "207",
    "50_64": "208",
    "65_plus": "209",
}
POPULATION_ALL = "200"
POPULATION_YEARS = tuple(str(year) for year in range(2016, 2026))

#: MHSDS ``England; Age`` bands mapped onto the population bands. ``UNKNOWN`` is
#: deliberately absent: it is a missing age, not an age band, and it is reported
#: separately rather than distributed or zeroed.
MHSDS_AGE_TO_BAND: dict[str, tuple[str, ...]] = {
    "0_15": ("0 to 5", "6 to 10", "11 to 15"),
    "16_17": ("16", "17"),
    "18_24": ("18", "19", "20 to 24"),
    "25_49": ("25 to 29", "30 to 34", "35 to 39", "40 to 44", "45 to 49"),
    "50_64": ("50 to 54", "55 to 59", "60 to 64"),
    "65_plus": (
        "65 to 69",
        "70 to 74",
        "75 to 79",
        "80 to 84",
        "85 to 89",
        "90 or over",
    ),
}

#: W09 sources split into the policy layer and the practice layer, for the TH04 ordering
#: test. The split is by institution type and is declared before the counts are seen.
W09_POLICY_SOURCES = frozenset({"GOV.UK", "NHS England", "NICE"})
W09_PRACTICE_SOURCES = frozenset(
    {
        "British Psychological Society",
        "Royal College of Psychiatrists",
        "Royal College of Paediatrics and Child Health",
    }
)
TH04_FIRST_YEAR = 2010
TH04_LAST_YEAR = 2025

#: The AS09 substitution family: four QOF diagnostic categories published on the same
#: instrument over overlapping years. Substitution predicts inverse movement between them.
AS09_INDICATORS = (200, 848, 90581, 90646)

#: AS02: an IAPT capacity proxy (mean wait to enter treatment) against IAPT throughput
#: (people entering treatment as a share of estimated need), same collection, same months.
AS02_CAPACITY_INDICATOR = 92010
AS02_THROUGHPUT_INDICATOR = 90592

#: Declared in advance, per the mechanism_simulation contract: widening either after
#: seeing the outcome converts a falsification into a fitting exercise.
CALIBRATION_TOLERANCE = 0.15

PERMUTATION_DRAWS = 20_000
PERMUTATION_SEED = 20260816

MONTH_ABBREVIATIONS = (
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
)


# --------------------------------------------------------------------------------------
# Small pure helpers - unit tested
# --------------------------------------------------------------------------------------


def month_range(first: str, last: str) -> list[str]:
    """Every ``YYYY-MM`` label from ``first`` to ``last`` inclusive."""

    start = int(first[:4]) * 12 + (int(first[5:7]) - 1)
    end = int(last[:4]) * 12 + (int(last[5:7]) - 1)
    if end < start:
        raise ValueError(f"{last} precedes {first}")
    return [f"{value // 12:04d}-{value % 12 + 1:02d}" for value in range(start, end + 1)]


def financial_year(label: str) -> str:
    """Label a ``YYYY-MM`` month with the English financial year it falls in."""

    year, month = int(label[:4]), int(label[5:7])
    start = year if month >= 4 else year - 1
    return f"{start}/{(start + 1) % 100:02d}"


def log_growth_share(part_ratio: float, whole_ratio: float) -> float:
    """Share of log growth in ``whole_ratio`` attributable to ``part_ratio``.

    Ratios compose multiplicatively, so their logs compose additively and a "share of the
    growth" is only well defined on the log scale. Stating it any other way invites the
    reader to subtract percentages that do not subtract.
    """

    if part_ratio <= 0 or whole_ratio <= 0:
        raise ValueError("ratios must be positive to take a log share")
    denominator = math.log(whole_ratio)
    if denominator == 0:
        raise ValueError("no growth in the whole; a share of zero growth is undefined")
    return math.log(part_ratio) / denominator


def pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("series must be the same length")
    if len(left) < 3:
        raise ValueError("a correlation on fewer than three points is not informative")
    n = len(left)
    mean_left, mean_right = sum(left) / n, sum(right) / n
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    spread = math.sqrt(
        sum((a - mean_left) ** 2 for a in left) * sum((b - mean_right) ** 2 for b in right)
    )
    if spread == 0:
        raise ValueError("a constant series has no correlation; this is usually an index")
    return numerator / spread


def ols_slope(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        raise ValueError("a slope needs at least two points")
    xs = list(range(n))
    mean_x, mean_y = sum(xs) / n, sum(values) / n
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / sum(
        (x - mean_x) ** 2 for x in xs
    )


def slope_break(values: Sequence[float], index: int, half_window: int) -> float:
    """Absolute change in fitted slope either side of ``index``."""

    before = values[index - half_window : index]
    after = values[index : index + half_window]
    if len(before) < half_window or len(after) < half_window:
        raise ValueError("not enough points either side of the candidate break")
    return abs(ols_slope(after) - ols_slope(before))


def permutation_p_value(
    statistic_by_key: dict[str, float],
    marked: Sequence[str],
    *,
    draws: int = PERMUTATION_DRAWS,
    seed: int = PERMUTATION_SEED,
) -> float:
    """One-sided p for "the marked keys carry a larger statistic than chance".

    Permutation rather than a parametric test because the statistic is a difference of
    fitted slopes on an autocorrelated monthly series, where a t-distribution would be a
    fiction.
    """

    if not marked:
        raise ValueError("no marked keys; there is nothing to test")
    observed = statistics.mean(statistic_by_key[key] for key in marked)
    keys = list(statistic_by_key)
    rng = random.Random(seed)
    hits = 0
    for _ in range(draws):
        sample = rng.sample(keys, len(marked))
        if statistics.mean(statistic_by_key[key] for key in sample) >= observed:
            hits += 1
    return hits / draws


def direct_standardised_rate(
    counts: dict[str, float],
    populations: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Directly standardised rate: band rates re-weighted to a fixed age structure."""

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("standard population weights must be positive")
    return sum(
        (weights[band] / total_weight) * (counts[band] / populations[band]) for band in weights
    )


# --------------------------------------------------------------------------------------
# Data acquisition (cached)
# --------------------------------------------------------------------------------------


def load_mhsds(*, force: bool = False) -> dict[str, Any]:
    """One streaming pass over the MHSDS archive, cached.

    Provider-level and England-level cells for MHS01, plus England-by-age cells for
    MHS32, in a single pass. A second pass over ~660MB to fetch what one pass could have
    carried is a cost with no epistemic return.
    """

    if MHSDS_CACHE.exists() and not force:
        return json.loads(MHSDS_CACHE.read_text(encoding="utf-8"))

    reader = MhsdsLocalReader()
    provider: dict[str, dict[str, float | None]] = defaultdict(dict)
    england: dict[str, float | None] = {}
    england_names: dict[str, list[str]] = defaultdict(list)
    by_age: dict[str, dict[str, float | None]] = defaultdict(dict)

    for cell in reader.iter_cells(
        measure_ids=[MEASURE_OPEN_REFERRALS],
        breakdowns=[BREAKDOWN_PROVIDER, BREAKDOWN_ENGLAND],
    ):
        if cell.breakdown == BREAKDOWN_PROVIDER:
            if cell.primary_level:
                provider[cell.month.label][cell.primary_level] = cell.value
        elif cell.primary_level == BREAKDOWN_ENGLAND:
            england[cell.month.label] = cell.value
            if cell.measure_name and cell.measure_name not in england_names[cell.month.label]:
                england_names[cell.month.label].append(cell.measure_name)

    for cell in reader.iter_cells(
        measure_ids=[MEASURE_NEW_REFERRALS], breakdowns=[BREAKDOWN_ENGLAND_AGE]
    ):
        if cell.primary_level == BREAKDOWN_ENGLAND and cell.secondary_level:
            by_age[cell.month.label][cell.secondary_level] = cell.value

    payload = {
        "archive": str(reader.archive_path),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "mhs01_provider": {month: dict(values) for month, values in provider.items()},
        "mhs01_england": england,
        "mhs01_england_measure_names": dict(england_names),
        "mhs32_england_by_age": {month: dict(values) for month, values in by_age.items()},
    }
    MHSDS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    MHSDS_CACHE.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def load_population(*, force: bool = False) -> dict[str, Any]:
    """England mid-year population by age band from NOMIS NM_2002_1, cached.

    ``NomisConnector.series`` refuses anything that is not exactly one row per period, so
    a lurking total or a nested geography cannot enter the denominator silently.
    """

    if POPULATION_CACHE.exists() and not force:
        return json.loads(POPULATION_CACHE.read_text(encoding="utf-8"))

    connector = NomisConnector()
    bands: dict[str, dict[str, float]] = {}
    for label, code in {**POPULATION_BANDS, "all": POPULATION_ALL}.items():
        series = connector.series(
            "NM_2002_1",
            geography=GEOGRAPHY_ENGLAND,
            dates=list(POPULATION_YEARS),
            dimensions={"gender": "0", "c_age": code},
        )
        bands[label] = {item.period.code: float(item.value) for item in series.observations}

    # The published "All Ages" cell must equal the sum of the disjoint parts. If it does
    # not, one of the codes is an overlapping aggregate and every rate below is wrong.
    for year in POPULATION_YEARS:
        parts = sum(bands[label][year] for label in POPULATION_BANDS)
        if abs(parts - bands["all"][year]) > 1.0:
            raise ValueError(
                f"population bands for {year} sum to {parts:.0f} against a published total "
                f"of {bands['all'][year]:.0f}; the age codelist is not a partition"
            )

    payload = {
        "dataset": "NM_2002_1",
        "geography": "England (NOMIS 2092957699)",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "bands": bands,
    }
    POPULATION_CACHE.parent.mkdir(parents=True, exist_ok=True)
    POPULATION_CACHE.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return payload


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------
# Provider cohorts
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderCohort:
    """Providers submitting a usable value in EVERY month of a window.

    "Usable" is doing work. A provider absent from a month has not reported zero
    activity, and a provider whose cell is suppressed has not reported zero activity
    either. Both are excluded from the cohort rather than read as a trough.
    """

    months: tuple[str, ...]
    provider_ids: tuple[str, ...]
    series: tuple[float, ...]
    unrestricted: tuple[float, ...]
    providers_present: dict[str, int]
    providers_with_value: dict[str, int]

    @property
    def ratio(self) -> float:
        return self.series[-1] / self.series[0]

    @property
    def unrestricted_ratio(self) -> float:
        return self.unrestricted[-1] / self.unrestricted[0]

    @property
    def coverage_ratio(self) -> float:
        return (
            self.providers_present[self.months[-1]] / self.providers_present[self.months[0]]
        )


def build_cohort(
    provider_cells: dict[str, dict[str, float | None]], first: str, last: str
) -> ProviderCohort:
    months = month_range(first, last)
    absent = [month for month in months if month not in provider_cells]
    if absent:
        raise ValueError(
            f"no provider rows at all for {', '.join(absent)}; a month with no data is not "
            "a month of no activity and the window cannot be closed over it"
        )

    seen: set[str] = set()
    for month in months:
        seen.update(provider_cells[month])
    continuous = tuple(
        sorted(
            provider
            for provider in seen
            if all(provider_cells[month].get(provider) is not None for month in months)
        )
    )
    if not continuous:
        raise ValueError("no provider submitted a usable value in every month of the window")

    series = tuple(
        float(sum(provider_cells[month][provider] for provider in continuous))
        for month in months
    )
    unrestricted = tuple(
        float(sum(value for value in provider_cells[month].values() if value is not None))
        for month in months
    )
    return ProviderCohort(
        months=tuple(months),
        provider_ids=continuous,
        series=series,
        unrestricted=unrestricted,
        providers_present={month: len(provider_cells[month]) for month in months},
        providers_with_value={
            month: sum(1 for value in provider_cells[month].values() if value is not None)
            for month in months
        },
    )


def financial_year_means(
    months: Sequence[str], values: Sequence[float]
) -> dict[str, float]:
    """Mean monthly value per COMPLETE financial year. Partial years are dropped."""

    grouped: dict[str, list[float]] = defaultdict(list)
    for month, value in zip(months, values):
        grouped[financial_year(month)].append(value)
    return {
        year: statistics.mean(items)
        for year, items in sorted(grouped.items())
        if len(items) == 12
    }


# --------------------------------------------------------------------------------------
# Mechanisms (declared before they are run)
# --------------------------------------------------------------------------------------


def _coverage_only(parameters: dict[str, float], length: int) -> list[float]:
    """Activity per continuously-submitting provider is flat; all growth is joiners.

    Under this mechanism a series restricted to a fixed provider cohort is level, up to a
    declared amount of wobble. It makes a falsifiable prediction about the
    cohort-restricted series, which is the whole reason for running it.
    """

    level = parameters["level"]
    wobble = parameters["wobble"]
    return [level * (1.0 + wobble * math.sin(index / 2.0)) for index in range(length)]


def _real_growth(parameters: dict[str, float], length: int) -> list[float]:
    """Activity per continuously-submitting provider grows at a constant rate."""

    level = parameters["level"]
    rate = parameters["rate"]
    return [level * (1.0 + rate) ** index for index in range(length)]


def as08_mechanisms(level_grid: tuple[float, ...]) -> list[MechanismCandidate]:
    return [
        MechanismCandidate(
            mechanism_id="COVERAGE_ONLY",
            description=(
                "All apparent growth in the England headline is providers joining the "
                "collection; a fixed cohort is flat."
            ),
            simulate=_coverage_only,
            parameter_grid={
                "level": level_grid,
                "wobble": (0.0, 0.01, 0.02, 0.03, 0.05),
            },
        ),
        MechanismCandidate(
            mechanism_id="REAL_GROWTH_WITHIN_FIXED_COHORT",
            description=(
                "Activity per continuously-submitting provider grows at a constant "
                "rate; joiners add to a real underlying rise."
            ),
            simulate=_real_growth,
            parameter_grid={
                "level": level_grid,
                "rate": (0.00, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10),
            },
        ),
    ]


# --------------------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------------------


@dataclass
class Finding:
    proposition_id: str
    model_family: str
    domain: str
    statement: str
    prediction: str
    falsifier: str
    finding_direction: FindingDirection
    falsifier_status: FalsifierStatus
    claim_tier: ClaimTier
    headline: str
    basis: str
    evidence_used: list[str] = field(default_factory=list)
    quantities: dict[str, Any] = field(default_factory=dict)
    limits: list[str] = field(default_factory=list)
    what_would_settle_it: str = ""
    released: bool = False

    def to_json(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["finding_direction"] = self.finding_direction.value
        payload["falsifier_status"] = self.falsifier_status.value
        payload["claim_tier"] = self.claim_tier.value
        return payload


def load_registry() -> dict[str, dict[str, str]]:
    path = REGISTRY_ROOT / "hypotheses.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["proposition_id"]: row for row in csv.DictReader(handle)}


def _finding(rows: dict[str, dict[str, str]], proposition_id: str, **kwargs: Any) -> Finding:
    row = rows[proposition_id]
    return Finding(
        proposition_id=proposition_id,
        model_family=row["model_family"],
        domain=row["domain"],
        statement=row["statement"],
        prediction=row["prediction"],
        falsifier=row["falsifier"],
        **kwargs,
    )


#: The recurring reason for an INCONCLUSIVE that is not a data gap in the registry's own
#: sense: the proposition's required workstreams are all present, and none of them carries
#: the quantity its own prediction names. That is a registry finding, not an analysis
#: failure, and it applies to AS04, AS05, AS07, AS12, TH05 and TH08.
PREDICTOR_NOT_IN_ANY_REQUIRED_WORKSTREAM = (
    "feasibility marks this OPEN_TESTABLE on required-workstream availability, but no "
    "required workstream carries the predictor the prediction names"
)


# --------------------------------------------------------------------------------------
# The analyses
# --------------------------------------------------------------------------------------


def analyse_as08(rows: dict[str, dict[str, str]], mhsds: dict[str, Any]) -> Finding:
    """The strongest of the sixteen. Restrict to a fixed provider cohort and look."""

    provider_cells = mhsds["mhs01_provider"]
    cohort = build_cohort(provider_cells, AS08_FIRST_MONTH, AS08_LAST_MONTH)

    cohort_fy = financial_year_means(cohort.months, cohort.series)
    unrestricted_fy = financial_year_means(cohort.months, cohort.unrestricted)
    england_fy = financial_year_means(
        cohort.months, [float(mhsds["mhs01_england"][month]) for month in cohort.months]
    )
    years = sorted(cohort_fy)
    cohort_ratio = cohort_fy[years[-1]] / cohort_fy[years[0]]
    unrestricted_ratio = unrestricted_fy[years[-1]] / unrestricted_fy[years[0]]
    england_ratio = england_fy[years[-1]] / england_fy[years[0]]

    survives = log_growth_share(cohort_ratio, unrestricted_ratio)
    attributable = 1.0 - survives

    level_grid = tuple(
        float(round(cohort_fy[years[0]] * factor))
        for factor in (0.90, 0.95, 1.00, 1.05, 1.10)
    )
    observed = ObservedSeries(
        name="MHSDS MHS01, England, providers submitting continuously 2017/18-2023/24",
        source_id="DS077",
        values=tuple(cohort_fy[year] for year in years),
        periods=tuple(years),
    )
    comparison = compare_mechanisms(
        as08_mechanisms(level_grid), observed, tolerance=CALIBRATION_TOLERANCE
    )
    refuted = list(comparison["refuted"])  # type: ignore[arg-type]
    compatible = list(comparison["compatible"])  # type: ignore[arg-type]

    coverage_only_refuted = "COVERAGE_ONLY" in refuted
    direction = (
        FindingDirection.WEAKENS if coverage_only_refuted else FindingDirection.INCONCLUSIVE
    )
    falsifier_status = (
        FalsifierStatus.TRIGGERED if coverage_only_refuted else FalsifierStatus.NOT_TRIGGERED
    )

    detail: dict[str, Any] = {
        "window": [AS08_FIRST_MONTH, AS08_LAST_MONTH],
        "financial_years": years,
        "providers_seen_in_window": len(
            {p for month in cohort.months for p in provider_cells[month]}
        ),
        "providers_submitting_continuously": len(cohort.provider_ids),
        "providers_present_first_month": cohort.providers_present[cohort.months[0]],
        "providers_present_last_month": cohort.providers_present[cohort.months[-1]],
        "coverage_ratio": cohort.coverage_ratio,
        "continuous_cohort_by_financial_year": cohort_fy,
        "unrestricted_by_financial_year": unrestricted_fy,
        "england_published_by_financial_year": england_fy,
        "continuous_cohort_ratio": cohort_ratio,
        "unrestricted_ratio": unrestricted_ratio,
        "england_published_ratio": england_ratio,
        "monthly_continuous_ratio": cohort.ratio,
        "monthly_unrestricted_ratio": cohort.unrestricted_ratio,
        "log_growth_surviving_coverage_restriction": survives,
        "log_growth_attributable_to_coverage": attributable,
        "cohort_share_of_unrestricted_first_year": cohort_fy[years[0]]
        / unrestricted_fy[years[0]],
        "cohort_share_of_unrestricted_last_year": cohort_fy[years[-1]]
        / unrestricted_fy[years[-1]],
        "mechanism_comparison": {
            "observed_series": comparison["observed_series"],
            "observed_source": comparison["observed_source"],
            "tolerance": comparison["tolerance"],
            "refuted": refuted,
            "compatible": compatible,
            "interpretation_bound": comparison["interpretation_bound"],
            "results": [
                {
                    "mechanism_id": item.mechanism_id,
                    "grid_size": item.grid_size,
                    "accepted": item.accepted,
                    "best_distance": item.best_distance,
                    "best_parameters": item.best_parameters,
                    "finding_direction": item.finding_direction.value,
                    "narrative": item.narrative,
                }
                for item in comparison["results"]  # type: ignore[union-attr]
            ],
        },
    }

    return _finding(
        rows,
        "AS08",
        finding_direction=direction,
        falsifier_status=falsifier_status,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            f"Restricted to the {len(cohort.provider_ids)} providers submitting a usable "
            "MHS01 value in every one of the 84 months, the England open-referral series "
            f"still rises x{cohort_ratio:.3f} across 2017/18-2023/24, against "
            f"x{unrestricted_ratio:.3f} unrestricted, while submitting providers rose "
            f"x{cohort.coverage_ratio:.2f}. The rise is not wholly a coverage artefact."
        ),
        basis=(
            f"{survives:.1%} of the log growth survives restriction to a fixed provider "
            f"cohort; {attributable:.1%} is attributable to changing coverage and "
            "composition. The COVERAGE_ONLY mechanism, which predicts a flat "
            "cohort-restricted series, was refuted by compare_mechanisms - no point in "
            "its declared grid reproduced the observed cohort series. AS08's own "
            "falsifier, 'trends persist in stable-coverage subsets', is triggered."
        ),
        evidence_used=[
            "W02: MHSDS Apr-2016-Jun-2026 time-series archive, MHS01, Provider and "
            "England breakdowns (DS077), read locally, no network",
            "W02: docs/REFERRAL_BASELINE.md second-comparator withdrawal notice",
            "governance/mechanism_simulation.compare_mechanisms",
        ],
        quantities=detail,
        limits=[
            "MHS01 is a STOCK (people with an open referral at period end), not the "
            "referral FLOW the withdrawn comparator measured. MHS32, the flow measure, is "
            "only published at England level from April 2022 and cannot cover this window.",
            "The cohort is defined by continuous submission, which selects for "
            "organisational stability. Providers that merged, split or changed org code "
            "leave the cohort by construction, so the cohort is not a random sample and "
            "its growth need not equal true national growth.",
            f"The cohort carries {detail['cohort_share_of_unrestricted_first_year']:.1%} "
            "of unrestricted activity in 2017/18 and "
            f"{detail['cohort_share_of_unrestricted_last_year']:.1%} in 2023/24 - large, "
            "but a majority-not-all subset.",
            "Counts, not rates. The population correction is AS11's job and is small "
            "(see AS11), but it is not applied here.",
            "Refuting COVERAGE_ONLY disfavours that mechanism on this series. The "
            "surviving mechanism is COMPATIBLE and is not thereby supported.",
        ],
        what_would_settle_it=(
            "The same restriction applied to a gender-service referral series. MHSDS "
            "carries no such measure - a full scan of all 121 England-level measures "
            "found none - so this remains a comparator result about secondary mental "
            "health, and the FOI request under studies/foi_requests/ is still the route "
            "to the target series."
        ),
    )


def analyse_as11(
    rows: dict[str, dict[str, str]], mhsds: dict[str, Any], population: dict[str, Any]
) -> Finding:
    """Decompose raw-count growth into denominator growth and rate growth."""

    cohort = build_cohort(mhsds["mhs01_provider"], AS08_FIRST_MONTH, AS08_LAST_MONTH)
    england_fy = financial_year_means(
        cohort.months, [float(mhsds["mhs01_england"][month]) for month in cohort.months]
    )
    cohort_fy = financial_year_means(cohort.months, cohort.series)
    years = sorted(england_fy)
    first_pop_year, last_pop_year = years[0][:4], years[-1][:4]
    pop_first = population["bands"]["all"][first_pop_year]
    pop_last = population["bands"]["all"][last_pop_year]

    raw_ratio = england_fy[years[-1]] / england_fy[years[0]]
    pop_ratio = pop_last / pop_first
    rate_ratio = raw_ratio / pop_ratio
    denominator_share = log_growth_share(pop_ratio, raw_ratio)

    cohort_raw_ratio = cohort_fy[years[-1]] / cohort_fy[years[0]]

    detail = {
        "window": years,
        "population_years": [first_pop_year, last_pop_year],
        "population_first": pop_first,
        "population_last": pop_last,
        "population_ratio": pop_ratio,
        "raw_count_ratio_england_published": raw_ratio,
        "rate_ratio_england_published": rate_ratio,
        "raw_count_ratio_continuous_cohort": cohort_raw_ratio,
        "rate_ratio_continuous_cohort": cohort_raw_ratio / pop_ratio,
        "share_of_log_growth_from_denominator": denominator_share,
        "share_of_log_growth_from_rate": 1.0 - denominator_share,
        "population_by_year": {
            year: population["bands"]["all"][year] for year in POPULATION_YEARS
        },
    }

    return _finding(
        rows,
        "AS11",
        finding_direction=FindingDirection.SUPPORTS,
        falsifier_status=FalsifierStatus.NOT_TRIGGERED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            f"England's population rose x{pop_ratio:.4f} across 2017/18-2023/24 while the "
            f"MHS01 raw count rose x{raw_ratio:.3f}. The denominator contributes "
            f"{denominator_share:.1%} of the log growth; {1 - denominator_share:.1%} is a "
            "rise in the rate per head."
        ),
        basis=(
            "The proposition's literal claim - that population denominator change "
            "CONTRIBUTES to raw-count growth - is directly measurable arithmetic and the "
            "measured contribution is positive and non-zero. Its prediction, that "
            f"standardisation attenuates raw growth, holds: x{raw_ratio:.3f} raw becomes "
            f"x{rate_ratio:.3f} per head. Its falsifier, read as 'standardisation leaves "
            "the growth unchanged', is not triggered."
        ),
        evidence_used=[
            "W01: NOMIS NM_2002_1 England mid-year population estimates 2016-2025, one "
            "pinned stratum per band, published total reconciled against the sum of the "
            "disjoint parts",
            "W02: MHSDS MHS01 England series (DS077)",
        ],
        quantities=detail,
        limits=[
            "SUPPORTS here attaches ONLY to the literal claim that the denominator "
            f"contributes. It is {denominator_share:.1%} of the growth. Nine parts in ten "
            "of the rise are not population, so this must not be read as ascertainment "
            "explaining the trend - it is closer to the opposite.",
            "All-ages denominator against an all-ages numerator. The age-specific version "
            "is AS06 and returns a similarly small magnitude.",
            "ONS mid-year estimates are as at 30 June and are matched to the financial "
            "year that contains them; no interpolation is performed.",
            "The registry's falsifier wording ('standardised rates remain unchanged') is "
            "ambiguous between 'unchanged from raw' and 'flat over time'. It is read here "
            "as the former, the only reading on which it falsifies rather than confirms "
            "the statement. An adjudicator should fix the wording.",
        ],
        what_would_settle_it=(
            "Nothing further for this series - the decomposition is exact arithmetic. The "
            "open question is whether it holds for a gender-service series, whose relevant "
            "denominator is an age-and-sex band rather than the whole population."
        ),
    )


def analyse_as06(
    rows: dict[str, dict[str, str]], mhsds: dict[str, Any], population: dict[str, Any]
) -> Finding:
    """Age-standardise the MHS32 referral flow and see how much composition explains."""

    by_age = mhsds["mhs32_england_by_age"]

    def gather(first: str, last: str, pop_year: str) -> dict[str, Any]:
        months = month_range(first, last)
        missing = [month for month in months if month not in by_age]
        if missing:
            raise ValueError(f"no MHS32 age rows for {', '.join(missing)}")
        holes = [
            (month, band)
            for month in months
            for bands in MHSDS_AGE_TO_BAND.values()
            for band in bands
            if by_age[month].get(band) is None
        ]
        if holes:
            raise ValueError(
                f"{len(holes)} suppressed or absent age cells in {first}-{last}; a "
                "suppressed cell is missing, never zero, and the standardisation is refused"
            )
        counts = {
            band: float(sum(by_age[month][item] for month in months for item in items))
            for band, items in MHSDS_AGE_TO_BAND.items()
        }
        unknown = float(sum(by_age[month].get("UNKNOWN") or 0.0 for month in months))
        pops = {band: population["bands"][band][pop_year] for band in MHSDS_AGE_TO_BAND}
        return {"counts": counts, "unknown_age": unknown, "populations": pops}

    one = gather(*AS06_YEAR_ONE)
    two = gather(*AS06_YEAR_TWO)

    total_one, total_two = sum(one["counts"].values()), sum(two["counts"].values())
    pop_one, pop_two = sum(one["populations"].values()), sum(two["populations"].values())
    crude_rate_ratio = (total_two / pop_two) / (total_one / pop_one)
    weights = one["populations"]
    std_one = direct_standardised_rate(one["counts"], one["populations"], weights)
    std_two = direct_standardised_rate(two["counts"], two["populations"], weights)
    std_ratio = std_two / std_one
    composition_share = 1.0 - log_growth_share(std_ratio, crude_rate_ratio)
    unknown_ratio = (
        two["unknown_age"] / one["unknown_age"] if one["unknown_age"] else None
    )

    detail = {
        "period_one": list(AS06_YEAR_ONE),
        "period_two": list(AS06_YEAR_TWO),
        "referrals_period_one": total_one,
        "referrals_period_two": total_two,
        "unknown_age_period_one": one["unknown_age"],
        "unknown_age_period_two": two["unknown_age"],
        "unknown_age_ratio": unknown_ratio,
        "crude_rate_ratio": crude_rate_ratio,
        "age_standardised_rate_ratio": std_ratio,
        "share_of_log_growth_from_age_composition": composition_share,
        "band_rates_per_100k": {
            band: {
                "period_one": one["counts"][band] / one["populations"][band] * 100_000,
                "period_two": two["counts"][band] / two["populations"][band] * 100_000,
                "ratio": (two["counts"][band] / two["populations"][band])
                / (one["counts"][band] / one["populations"][band]),
                "referral_share_period_one": one["counts"][band] / total_one,
                "referral_share_period_two": two["counts"][band] / total_two,
            }
            for band in MHSDS_AGE_TO_BAND
        },
    }

    return _finding(
        rows,
        "AS06",
        finding_direction=FindingDirection.WEAKENS,
        falsifier_status=FalsifierStatus.TRIGGERED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            f"Age composition explains {composition_share:.1%} of the log growth in the "
            "MHS32 referral rate between 2022/23 and 2024/25. Directly standardising to "
            f"the 2022 England age structure moves the ratio from x{crude_rate_ratio:.4f} "
            f"to x{std_ratio:.4f}."
        ),
        basis=(
            "AS06's falsifier is 'standardisation/decomposition shows minimal "
            "contribution'. A contribution of this size is minimal on any reading. Every "
            "age band except 16-17 rose in rate; the growth is within bands, not between "
            "them."
        ),
        evidence_used=[
            "W02: MHSDS MHS32 England; Age monthly cells, 2022-04 to 2026-06 (DS077)",
            "W01: NOMIS NM_2002_1 England population by age band, 2022 and 2024",
        ],
        quantities=detail,
        limits=[
            "AGE composition only. AS06 also names psychiatric and neurodevelopmental "
            "composition, and no required workstream carries either at England level. The "
            "verdict is about the one component that could be measured.",
            "Two financial years. MHS32 does not exist at England level before April "
            "2022, so a longer window is not available.",
            "The UNKNOWN age band rose x"
            f"{unknown_ratio:.1f} between the two periods "
            f"({one['unknown_age']:.0f} to {two['unknown_age']:.0f} referrals). It is "
            "excluded from the standardisation because a missing age is not an age band. "
            "That drift is itself a data-quality signal and it points, weakly, AS08's way.",
            "Six coarse bands, set by what the NOMIS codelist offers as a partition.",
        ],
        what_would_settle_it=(
            "MHSDS carries no England-level psychiatric or neurodevelopmental "
            "co-occurrence breakdown. The rest of AS06 needs individual-level records, "
            "which is a different reachability class."
        ),
    )


def analyse_as03(rows: dict[str, dict[str, str]], mhsds: dict[str, Any]) -> Finding:
    """Test the one documented definition-label change inside the archive."""

    names_by_month: dict[str, list[str]] = mhsds["mhs01_england_measure_names"]
    ordered = sorted(names_by_month)
    rename_month: str | None = None
    previous: list[str] | None = None
    changes: list[dict[str, Any]] = []
    for month in ordered:
        current = sorted(names_by_month[month])
        if previous is not None and current != previous:
            changes.append({"month": month, "from": previous, "to": current})
            rename_month = rename_month or month
        previous = current

    cohort = build_cohort(mhsds["mhs01_provider"], AS03_WINDOW_FIRST, AS03_WINDOW_LAST)
    england = [float(mhsds["mhs01_england"][month]) for month in cohort.months]
    if rename_month is None or not cohort.months[0] < rename_month <= cohort.months[-1]:
        raise ValueError("the measure rename does not fall inside the declared AS03 window")

    def step(values: Sequence[float]) -> float:
        before = [v for m, v in zip(cohort.months, values) if m < rename_month]
        after = [v for m, v in zip(cohort.months, values) if m >= rename_month]
        return statistics.mean(after) / statistics.mean(before)

    cohort_step = step(cohort.series)
    england_step = step(england)

    detail = {
        "measure": "MHS01",
        "measure_rename_month": rename_month,
        "measure_name_changes": changes,
        "window": [AS03_WINDOW_FIRST, AS03_WINDOW_LAST],
        "providers_submitting_continuously": len(cohort.provider_ids),
        "step_in_continuous_cohort": cohort_step,
        "step_in_england_published": england_step,
        "months_before": sum(1 for m in cohort.months if m < rename_month),
        "months_after": sum(1 for m in cohort.months if m >= rename_month),
    }

    return _finding(
        rows,
        "AS03",
        finding_direction=FindingDirection.INCONCLUSIVE,
        falsifier_status=FalsifierStatus.PARTIALLY_TRIGGERED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            f"At the only documented definition-label change in the archive ({rename_month}, "
            "MHS01 renamed from 'People in contact with services' to 'People with an open "
            "referral with services'), a coverage-fixed provider cohort steps by "
            f"x{cohort_step:.4f} - no discontinuity - while the England headline steps "
            f"x{england_step:.4f}."
        ),
        basis=(
            "AS03 predicts that trend discontinuities align with coding or definition "
            "changes. At the one change available, the coverage-fixed series shows no step "
            "at all. But this is a single instance, and a change of LABEL is not "
            "demonstrably a change of SPECIFICATION, so the test has little power and the "
            "falsifier is recorded as only partially triggered."
        ),
        evidence_used=[
            "W02: MHSDS MHS01 England and Provider cells with measure names carried per "
            "month (DS077); the rename was located by scanning the archive, not assumed"
        ],
        quantities=detail,
        limits=[
            "n=1. One label change, in one measure, in one collection.",
            "The England headline's step at the same month is NOT evidence of a definition "
            "effect: England and the cohort differ precisely by the providers outside the "
            "cohort, so that step is a joiner effect and is AS08's subject, not AS03's.",
            "Fifteen months either side, of which only three fall after the change; a step "
            "estimated on three months is fragile.",
            "ICD and OPCS coding revisions, which are what AS03 is really about, are not "
            "carried by any workstream in hand.",
        ],
        what_would_settle_it=(
            "A dated register of coding and specification changes - MHSDS technical output "
            "specification versions, ICD-10 to ICD-11 transition dates - tested against "
            "coverage-fixed series. None of the four required workstreams carries one."
        ),
    )


def analyse_as01(
    rows: dict[str, dict[str, str]], mhsds: dict[str, Any], anchors: Sequence[str]
) -> Finding:
    """Do W09 policy anchors sit at slope breaks in a coverage-fixed series?"""

    cohort = build_cohort(mhsds["mhs01_provider"], AS08_FIRST_MONTH, AS08_LAST_MONTH)
    logs = [math.log(value) for value in cohort.series]
    half_window = 12
    statistic = {
        cohort.months[index]: slope_break(logs, index, half_window)
        for index in range(half_window, len(logs) - half_window)
    }
    anchor_months = {anchor[:7] for anchor in anchors}
    marked = [month for month in statistic if month in anchor_months]

    p_value = permutation_p_value(statistic, marked)
    at_anchors = statistics.mean(statistic[month] for month in marked)
    everywhere = statistics.mean(statistic.values())

    detail = {
        "series": "MHS01, England, continuous provider cohort, 2017/18-2023/24",
        "testable_months": len(statistic),
        "months_carrying_a_w09_anchor": len(marked),
        "anchor_density": len(marked) / len(statistic),
        "mean_abs_log_slope_change_at_anchors": at_anchors,
        "mean_abs_log_slope_change_all_months": everywhere,
        "permutation_p_value": p_value,
        "permutation_draws": PERMUTATION_DRAWS,
        "cancer_comparator": {
            "referral_rate_ratio": 2.98,
            "conversion_rate_ratio": 0.55,
            "note": "from docs/REFERRAL_BASELINE.md; the threshold signature in a "
            "different domain, unaffected by the MHSDS coverage ramp",
        },
    }

    return _finding(
        rows,
        "AS01",
        finding_direction=FindingDirection.INCONCLUSIVE,
        falsifier_status=FalsifierStatus.INCONCLUSIVE,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            "W09 anchor months carry no larger a break in the fitted log-slope of the "
            f"coverage-fixed series than any other month (permutation p={p_value:.2f}), "
            f"but {len(marked)} of {len(statistic)} testable months carry an anchor, so "
            "the test has almost no power."
        ),
        basis=(
            "The 121 W09 anchors are undifferentiated: they include every dated NHS "
            "England, GOV.UK, NICE and professional-body document the harvest found, not "
            "the subset that changed a referral threshold. With anchors on "
            f"{len(marked) / len(statistic):.0%} of testable months, 'anchor' and 'month' "
            "are nearly the same variable, so a null here is uninformative rather than "
            "negative. The cancer comparator does show the threshold signature - referrals "
            "x2.98 against conversion x0.55, monotonic - but in a different domain."
        ),
        evidence_used=[
            "W09: data/w09_clinical_guidance.json, 121 distinct anchor dates 2013-2026",
            "W02: MHSDS MHS01 continuous-cohort monthly series (DS077)",
            "W02: docs/REFERRAL_BASELINE.md cancer referral and conversion series",
        ],
        quantities=detail,
        limits=[
            "Anchor density is the binding limit, not sample size.",
            "Selecting the threshold-relevant anchors requires human coding of the 121 "
            "documents. governance/claim_release.py records zero human-coded lanes, so the "
            "selection cannot be made inside this engine without inventing it.",
            "MHS01 is general secondary mental health and is not the target domain.",
        ],
        what_would_settle_it=(
            "Human coding of the W09 anchors into 'changes a referral threshold' and 'does "
            "not', pre-registered before the series is looked at, then the same "
            "permutation test on the coded subset."
        ),
    )


def analyse_as09(rows: dict[str, dict[str, str]], fingertips: dict[str, Any]) -> Finding:
    """Substitution predicts inverse movement between related diagnostic categories."""

    series = {item["indicator_id"]: item for item in fingertips["series"]}
    chosen: dict[int, dict[str, Any]] = {}
    for indicator_id in AS09_INDICATORS:
        item = series[indicator_id]
        chosen[indicator_id] = {
            "name": item["indicator_name"],
            "points": {
                point["period"]: point["value"]
                for point in item["points"]
                if point["value"] is not None
            },
        }
    common = sorted(set.intersection(*(set(v["points"]) for v in chosen.values())))
    if len(common) < 5:
        raise ValueError("fewer than five common periods; the correlation is not informative")

    deltas = {
        indicator_id: [
            math.log(value["points"][b]) - math.log(value["points"][a])
            for a, b in zip(common, common[1:])
        ]
        for indicator_id, value in chosen.items()
    }
    pairs = []
    for index, left in enumerate(AS09_INDICATORS):
        for right in AS09_INDICATORS[index + 1 :]:
            pairs.append(
                {"left": left, "right": right, "r": pearson(deltas[left], deltas[right])}
            )
    negative = [pair for pair in pairs if pair["r"] < 0]
    ratios = {
        str(k): {
            "name": v["name"],
            "first": v["points"][common[0]],
            "last": v["points"][common[-1]],
            "ratio": v["points"][common[-1]] / v["points"][common[0]],
        }
        for k, v in chosen.items()
    }
    smallest = min(item["ratio"] for item in ratios.values())
    largest = max(item["ratio"] for item in ratios.values())

    detail = {
        "common_periods": common,
        "indicators": ratios,
        "pairwise_year_on_year_log_change_correlations": pairs,
        "pairs": len(pairs),
        "negatively_correlated_pairs": len(negative),
    }

    return _finding(
        rows,
        "AS09",
        finding_direction=FindingDirection.WEAKENS,
        falsifier_status=FalsifierStatus.TRIGGERED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            "Across four QOF diagnostic categories on the same instrument over "
            f"{len(common)} common years, all four rose (x{smallest:.2f} to "
            f"x{largest:.2f}) and {len(negative)} of {len(pairs)} pairs of year-on-year "
            "changes are negatively correlated. No compensating pattern appears."
        ),
        basis=(
            "AS09's falsifier is 'no substitution pattern is observed'. Substitution "
            "predicts that a category gains at another's expense; here every category "
            "gains and the year-on-year movements are weakly positively correlated "
            "throughout."
        ),
        evidence_used=[
            "W02: OHID Fingertips indicators 200, 848, 90581, 90646 (QOF prevalence and "
            "incidence), England, data/fingertips_w02.json"
        ],
        quantities=detail,
        limits=[
            "Four QOF categories are not the diagnostic space. Substitution between, say, "
            "an autism code and a gender-related code would appear in none of them.",
            "QOF prevalence is a register count and is itself exposed to recording "
            "incentives; a common recording drift would produce exactly this pattern of "
            "everything rising together, which is an AS08-shaped confound on an AS09 test.",
            "Ten common annual points, so the correlations rest on nine differences.",
        ],
        what_would_settle_it=(
            "Paired series for categories that plausibly substitute for one another, coded "
            "as such in advance. No workstream in hand carries a substitution map."
        ),
    )


def analyse_as02(rows: dict[str, dict[str, str]], fingertips: dict[str, Any]) -> Finding:
    """A capacity proxy against throughput, same collection, same months."""

    series = {item["indicator_id"]: item for item in fingertips["series"]}
    capacity = series[AS02_CAPACITY_INDICATOR]
    throughput = series[AS02_THROUGHPUT_INDICATOR]

    def as_map(item: dict[str, Any]) -> dict[str, float]:
        return {
            point["period"]: point["value"]
            for point in item["points"]
            if point["value"] is not None
        }

    cap, thr = as_map(capacity), as_map(throughput)

    def key(period: str) -> tuple[int, int]:
        name, year = period.split()
        return int(year), MONTH_ABBREVIATIONS.index(name)

    overlap = sorted(set(cap) & set(thr), key=key)
    ordinals = [year * 12 + month for year, month in (key(period) for period in overlap)]
    # The mean-wait series has a real hole. Differences are taken WITHIN contiguous runs
    # only: subtracting across a four-month gap would manufacture a month-on-month change
    # four times the size of any real one.
    gaps = [
        (overlap[index], overlap[index + 1])
        for index in range(len(ordinals) - 1)
        if ordinals[index + 1] - ordinals[index] != 1
    ]
    runs: list[list[str]] = [[overlap[0]]]
    for index in range(1, len(overlap)):
        if ordinals[index] - ordinals[index - 1] == 1:
            runs[-1].append(overlap[index])
        else:
            runs.append([overlap[index]])

    x = [cap[period] for period in overlap]
    y = [thr[period] for period in overlap]
    level_r = pearson(x, y)
    diff_capacity: list[float] = []
    diff_throughput: list[float] = []
    for run in runs:
        if len(run) < 2:
            continue
        diff_capacity.extend(cap[b] - cap[a] for a, b in zip(run, run[1:]))
        diff_throughput.extend(thr[b] - thr[a] for a, b in zip(run, run[1:]))
    diff_r = pearson(diff_capacity, diff_throughput)

    detail = {
        "capacity_indicator": {
            "id": AS02_CAPACITY_INDICATOR,
            "name": capacity["indicator_name"],
        },
        "throughput_indicator": {
            "id": AS02_THROUGHPUT_INDICATOR,
            "name": throughput["indicator_name"],
        },
        "overlapping_months": len(overlap),
        "first_month": overlap[0],
        "last_month": overlap[-1],
        "gaps": [list(gap) for gap in gaps],
        "contiguous_runs": [[run[0], run[-1], len(run)] for run in runs],
        "first_differences_used": len(diff_capacity),
        "mean_wait_days_first": x[0],
        "mean_wait_days_last": x[-1],
        "throughput_first": y[0],
        "throughput_last": y[-1],
        "level_correlation": level_r,
        "first_difference_correlation": diff_r,
    }

    return _finding(
        rows,
        "AS02",
        finding_direction=FindingDirection.INCONCLUSIVE,
        falsifier_status=FalsifierStatus.NOT_TESTED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            f"Over {len(overlap)} overlapping months the IAPT mean wait fell {x[0]:.1f} to "
            f"{x[-1]:.1f} days while access rose {y[0]:.1f}% to {y[-1]:.1f}% of estimated "
            f"need (levels r={level_r:.2f}), but month-to-month changes are unrelated "
            f"(r={diff_r:.2f})."
        ),
        basis=(
            "The level relationship has the sign a capacity account predicts and the "
            "first-difference relationship is null. Compatibility is not support, and no "
            "design here separates capacity causing throughput from throughput causing "
            "waits or from a common trend."
        ),
        evidence_used=[
            "W02: OHID Fingertips 92010 (mean wait to enter IAPT) and 90592 (access to "
            "IAPT), England, monthly"
        ],
        quantities=detail,
        limits=[
            "Waiting time is an OUTCOME of capacity and demand jointly, not a measure of "
            "capacity. Using it as a capacity proxy builds the simultaneity in.",
            "The overlap ends September 2019 and does not reach the period the MHSDS work "
            "covers.",
            f"The mean-wait series has {len(gaps)} hole(s) inside the overlap "
            f"({'; '.join(f'{a} to {b}' for a, b in gaps)}). First differences are taken "
            "within contiguous runs only - a missing month is not a month of no change.",
            "IAPT is a self-referral service; its access dynamics are not those of a "
            "GP-gated specialist pathway.",
        ],
        what_would_settle_it=(
            "A commissioned-capacity series - funded establishment, clinic count, "
            "contracted activity - which no required workstream carries, plus variation in "
            "it that is not itself a response to demand."
        ),
    )


def analyse_as10(rows: dict[str, dict[str, str]]) -> Finding:
    """Does the instrument change the estimate? The census answers this on itself."""

    detail = {
        "source": "ONS Census 2021 gender identity tables via NOMIS, "
        "data/census_2021_gender_identity.json; figures as recorded in "
        "docs/CENSUS_2021_GENDER_IDENTITY.md",
        "response_option_effect": {
            "category": "All other gender identities",
            "eight_category_codelist_TS070": 18_074,
            "seven_category_codelist_TS078_and_RM": 48_331,
            "ratio": 48_331 / 18_074,
            "note": "same census, same respondents, same question; the 7-category list "
            "folds non-binary in and the 8-category list does not",
        },
        "denominator_effect": {
            "share_of_all_16_plus": 262_113 / 48_566_373,
            "share_of_those_who_answered": 262_113 / 45_651_748,
            "non_response": 2_914_625 / 48_566_373,
        },
        "instrument_failure_signature": {
            "white_british_percent_of_answered": 0.362,
            "other_ethnic_group_percent_of_answered": 2.178,
            "spread": 2.178 / 0.362,
            "ons_2025_guidance": {
                "not_proficient_in_english_percent": 2.24,
                "english_speakers_percent": 0.42,
                "ratio": 2.24 / 0.42,
            },
        },
        "regulatory_disposition": {
            "osr_final_report": "2024-09-12",
            "outcome": "accreditation removed; reclassified official statistics in "
            "development",
            "asymmetry": "sexual orientation rode the same form and was NOT downgraded",
        },
    }

    return _finding(
        rows,
        "AS10",
        finding_direction=FindingDirection.SUPPORTS,
        falsifier_status=FalsifierStatus.NOT_TRIGGERED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            "Within a single census, the same category read off a 7-category and an "
            "8-category response list differs by x2.67 (18,074 against 48,331); the "
            "estimate varies 6-fold across ethnic groups in the order of English "
            "proficiency; and the Office for Statistics Regulation removed accreditation "
            "on 2024-09-12 because the question 'did not work as intended'."
        ),
        basis=(
            "AS10's prediction is that wording, mode or harmonisation changes prevalence "
            "estimates materially. Here the response-option set alone changes one category "
            "by 167% with no change of respondent, question or date, and the national "
            "regulator has adjudicated the instrument as having failed. Its falsifier, "
            "'estimates invariant to wording/mode', is decisively not met."
        ),
        evidence_used=[
            "W01: ONS Census 2021 gender identity tables TS070, TS078, RM038, RM163, "
            "RM174, RM175 via NOMIS (517 cells, none missing, none non-normal)",
            "W09/W10: OSR final report 2024-09-12; ONS quality report November 2023; ONS "
            "additional guidance 2025-03-26",
        ],
        quantities=detail,
        limits=[
            "This is a measurement finding about a survey instrument. It says the census "
            "estimate is unreliable; it does NOT say the service-referral series is, and "
            "the two are separate collections.",
            "One cross-section. It cannot show change, so nothing here bears on any trend.",
            "The 6-fold ethnic spread is the ONS-identified signature, but this analysis "
            "did not harvest a language cross-tab (no language table was among the 13 "
            "pulled); the 2.24% / 0.42% figures are ONS's own, quoted.",
            "SUPPORTS attaches to AS10 as written - that survey wording and response "
            "options affect prevalence estimates. It is not support for "
            "ASCERTAINMENT_SERVICE as an account of service referrals.",
        ],
        what_would_settle_it=(
            "A split-ballot or mode experiment on the same population. ONS has not run "
            "one; the 2021 census is a single-instrument enumeration, and the 2031 "
            "question design is the live decision this bears on."
        ),
    )


def analyse_th07(rows: dict[str, dict[str, str]], coupling: dict[str, Any]) -> Finding:
    """Structural coupling was re-adjudicated on the current graph; reuse that verdict."""

    detail = {
        "source": "data/coupling_readjudication.json, docs/COUPLING_READJUDICATION.md",
        "entities": coupling.get("entities"),
        "relations": coupling.get("relations"),
        "resolution_tier": "STRONG_IDENTIFIER (not lowered)",
        "outcome_dates_assessed": len(coupling.get("outcome_dates", [])),
        "dates_reaching_a_substantive_verdict": 10,
        "dates_returning_MX09_ISOLATED_PROCESSES_BETTER": 10,
        "dates_returning_MD15_COUPLING_SUPPORTED": 0,
        "qualifying_connected_components_at_most_permissive_date": 0,
        "components_mixing_more_than_one_relation_type": 0,
    }

    return _finding(
        rows,
        "TH07",
        finding_direction=FindingDirection.WEAKENS,
        falsifier_status=FalsifierStatus.TRIGGERED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            "On an 824-entity, 1,286-relation graph at STRONG_IDENTIFIER, assessed against "
            "29 Parliament-fixed dates, no date returned MD15_COUPLING_SUPPORTED and ten "
            "returned MX09_ISOLATED_PROCESSES_BETTER. Not one connected component mixes "
            "more than one relation type."
        ),
        basis=(
            "TH07's falsifier is 'content/timing is independent and no cross-system "
            "coupling is observed'. That is what the re-adjudication found, on a graph "
            "quadrupled in size, without lowering the resolution tier, against dates fixed "
            "by Parliament rather than chosen."
        ),
        evidence_used=[
            "W07/W09/W10: institutional ontology graph from runtime/oslt.db (360Giving, "
            "UKRI GtR, Contracts Finder, GOV.UK publications, Parliament written evidence)",
            "W10: LegislationConnector outcome dates, live from legislation.gov.uk",
            "docs/COUPLING_READJUDICATION.md",
        ],
        quantities=detail,
        limits=[
            "This is an absence claim about THIS graph, at THIS tier, over FIVE registers. "
            "434 of 824 entities carry no strong identifier and cannot be merged at all, "
            "so a genuine shared body appearing under two spellings is invisible.",
            "647 of 824 entities are domain UNKNOWN and can never widen cross-system "
            "spread, so more than three quarters of the graph is inert for the test.",
            "Company filings, board memberships, personnel overlap, sub-awards and "
            "correspondence are absent. Coupling running through any of those channels is "
            "not measured here.",
            "Enactment dates resolve to 1 January of the enactment year; day-level "
            "precision would be invented.",
            "W11 (media) is a required workstream for TH07 and contributes nothing to this "
            "verdict - the graph carries no media entities.",
        ],
        what_would_settle_it=(
            "Registers carrying strong identifiers for the 52.7% of entities that have "
            "none - Companies House officer appointments in particular - which would let a "
            "bridge appear if one exists. Lowering the tier is barred: every historical "
            "positive here evaporated once name-only merges were disallowed."
        ),
    )


def analyse_th04(
    rows: dict[str, dict[str, str]], w09: dict[str, Any], legislation_years: Sequence[str]
) -> Finding:
    """Does the policy layer lead the practice layer? W09 anchors, no chosen dates."""

    years = list(range(TH04_FIRST_YEAR, TH04_LAST_YEAR + 1))
    policy: dict[int, int] = defaultdict(int)
    practice: dict[int, int] = defaultdict(int)
    by_source_year: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    for document in w09["documents"]:
        published = document.get("published_on")
        if not published:
            continue
        year = int(published[:4])
        source = document["source"]
        by_source_year[source][year] += 1
        if source in W09_POLICY_SOURCES:
            policy[year] += 1
        elif source in W09_PRACTICE_SOURCES:
            practice[year] += 1

    policy_series = [policy[year] for year in years]
    practice_series = [practice[year] for year in years]

    lags: dict[int, dict[str, float]] = {}
    for lag in range(-4, 5):
        if lag >= 0:
            left, right = policy_series[: len(policy_series) - lag], practice_series[lag:]
        else:
            left, right = policy_series[-lag:], practice_series[: len(practice_series) + lag]
        lags[lag] = {"r": pearson(left, right), "n": float(len(left))}
    best_lag = max(lags, key=lambda lag: lags[lag]["r"])

    peak_year = max(years, key=lambda year: policy[year])
    peak_sources = dict(
        sorted(
            ((source, counts[peak_year]) for source, counts in by_source_year.items()),
            key=lambda item: -item[1],
        )
    )
    peak_concentration = max(peak_sources.values()) / policy[peak_year]

    detail = {
        "years": years,
        "policy_layer_sources": sorted(W09_POLICY_SOURCES),
        "practice_layer_sources": sorted(W09_PRACTICE_SOURCES),
        "policy_counts": dict(zip(years, policy_series)),
        "practice_counts": dict(zip(years, practice_series)),
        "cross_correlation_by_lag": {str(lag): value for lag, value in sorted(lags.items())},
        "best_lag": best_lag,
        "best_lag_meaning": "positive = policy leads practice; negative = practice leads policy",
        "policy_peak_year": peak_year,
        "policy_peak_source_mix": peak_sources,
        "policy_peak_single_source_concentration": peak_concentration,
        "legislation_enactment_years_available": list(legislation_years),
    }

    return _finding(
        rows,
        "TH04",
        finding_direction=FindingDirection.INCONCLUSIVE,
        falsifier_status=FalsifierStatus.INCONCLUSIVE,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=(
            f"Annual W09 document counts cross-correlate best at lag {best_lag:+d} "
            f"(r={lags[best_lag]['r']:.2f}), which is the practice layer leading the "
            f"policy layer - but {peak_concentration:.0%} of the policy peak in "
            f"{peak_year} comes from one source's API, so the series measures archival "
            "depth as much as policy activity."
        ),
        basis=(
            "TH04 predicts a policy to infrastructure to practice sequence, and its "
            "falsifier is 'practice precedes policy'. The ordering statistic points at the "
            "falsifier, but the input is a count of documents that six heterogeneous "
            "websites still serve, harvested through four different routes with different "
            "archival depth. A recency-weighted publication count is not policy adoption, "
            "and a finding either way would be an artefact of the harvest."
        ),
        evidence_used=[
            "W09: data/w09_clinical_guidance.json, 152 dated documents, 121 distinct "
            "anchor dates, six publishers",
            "W10: legislation.gov.uk enactment years via LegislationConnector",
        ],
        quantities=detail,
        limits=[
            "Document COUNT is not adoption. One guideline can change practice nationally "
            "and a hundred blog posts can change nothing.",
            "The harvest routes differ by source: a WordPress REST API returns recent "
            "posts far more completely than a sitemap scrape returns old ones, which "
            "manufactures an upward trend in the policy layer specifically.",
            "Sixteen annual points, and the correlation is driven by two spikes.",
            "Legislation dates resolve to 1 January of the enactment year and cannot order "
            "events within a year.",
            "W05 (education) is a required workstream for TH04 and supplies nothing here; "
            "no education series was found that measures institutional implementation.",
        ],
        what_would_settle_it=(
            "A dated register of implementation events - service specifications issued, "
            "commissioning policies adopted, clinics opened - rather than publications. "
            "None of W05, W09 or W10 carries one, so TH04 is not answerable from a "
            "publication corpus however many anchors it holds."
        ),
    )


def _inconclusive(
    rows: dict[str, dict[str, str]],
    proposition_id: str,
    *,
    headline: str,
    basis: str,
    missing: Sequence[str],
    evidence_used: Sequence[str],
    what_would_settle_it: str,
) -> Finding:
    return _finding(
        rows,
        proposition_id,
        finding_direction=FindingDirection.INCONCLUSIVE,
        falsifier_status=FalsifierStatus.NOT_TESTED,
        claim_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        headline=headline,
        basis=basis,
        evidence_used=list(evidence_used),
        quantities={"missing_measures": list(missing)},
        limits=[PREDICTOR_NOT_IN_ANY_REQUIRED_WORKSTREAM],
        what_would_settle_it=what_would_settle_it,
    )


def analyse_remaining(rows: dict[str, dict[str, str]]) -> list[Finding]:
    """The propositions whose workstreams are present and which still cannot be answered.

    Each of these has all of its required workstreams in hand. None of those workstreams
    carries the quantity the proposition's own prediction names. That is a defect in the
    required-workstream mapping, and recording it is more useful than filling the table.
    """

    return [
        _inconclusive(
            rows,
            "AS04",
            headline=(
                "No disclosure or help-seeking indicator exists in any workstream in hand, "
                "so the prediction - that disclosure changes before referral without a "
                "corresponding shift in objective onset - has neither of its two terms."
            ),
            basis=(
                "AS04 needs a disclosure measure and an onset measure, separately timed. "
                "W01, W02, W09 and W10 carry population, service activity, policy dates "
                "and parliamentary material. None is a disclosure indicator, and no onset "
                "measure exists outside individual-level records."
            ),
            missing=[
                "a dated disclosure or help-seeking indicator",
                "an objective symptom-onset measure independent of presentation",
            ],
            evidence_used=[
                "W01, W02, W09, W10 enumerated and searched; see data/feasibility_census.json"
            ],
            what_would_settle_it=(
                "A repeated population survey carrying both disclosure and onset items - "
                "primary collection, which is a different reachability class."
            ),
        ),
        _inconclusive(
            rows,
            "AS05",
            headline=(
                "The awareness predictor AS05 names - search volume, media attention, "
                "professional awareness - sits in W11, which is not one of AS05's required "
                "workstreams and has not been harvested."
            ),
            basis=(
                "AS05 requires W01, W02, W09 and W10, and predicts that search, media or "
                "clinical awareness predicts presentation after service controls. No "
                "required workstream carries an awareness measure. The GDELT connector "
                "(media_discourse.py) exists and is unharvested; even harvested it would "
                "supply an association, not the ordering AS05 needs."
            ),
            missing=[
                "a dated awareness series (search volume or media attention)",
                "service controls at the same granularity",
            ],
            evidence_used=[
                "registries/hypotheses.csv AS05 required_workstreams = W01;W02;W09;W10",
                "connectors/media_discourse.py present, no harvested output under data/",
            ],
            what_would_settle_it=(
                "Correcting the registry so AS05 requires W11, harvesting GDELT, and "
                "pre-registering the direction test - because a correlation between media "
                "attention and presentation is equally predicted by the rival families."
            ),
        ),
        _inconclusive(
            rows,
            "AS07",
            headline=(
                "MHSDS carries ICB and provider geography, but no workstream in hand "
                "carries distance-to-service or a need proxy, so an access gradient cannot "
                "be distinguished from a need gradient."
            ),
            basis=(
                "AS07 predicts that natural variation in access predicts referral AFTER "
                "need proxies. The geography exists; the need proxy does not. A raw "
                "between-area referral gradient computed without one would measure "
                "deprivation and case mix and be reported as access."
            ),
            missing=[
                "a distance or provider-distribution measure by area",
                "an area-level need proxy independent of service use",
            ],
            evidence_used=[
                "W02: MHSDS Provider, ICB and Sub-ICB breakdowns present in the archive",
                "W02: the Fingertips harvest is England-level only; no sub-national "
                "cross-section was retrieved",
            ],
            what_would_settle_it=(
                "Sub-national Fingertips extraction plus IMD and an independent need "
                "measure, with the access variation shown not to be itself a response to "
                "need."
            ),
        ),
        _inconclusive(
            rows,
            "AS12",
            headline=(
                "Persistence and detransition rates require follow-up of individuals. No "
                "workstream in hand carries a cohort, so there is no estimate for a "
                "missingness model to move."
            ),
            basis=(
                "AS12 predicts that inverse-probability weighting or an MNAR sensitivity "
                "analysis materially changes an estimate. Every input to that sentence - "
                "the cohort, the follow-up, the attrition pattern - is individual-level, "
                "and aggregate published statistics supply none of them."
            ),
            missing=[
                "a longitudinal cohort with follow-up status per person",
                "an attrition or missingness indicator",
            ],
            evidence_used=["W01, W02, W09 and W10 are aggregate collections throughout"],
            what_would_settle_it=(
                "Individual-level linked records under a TRE, which the feasibility census "
                "classifies as NEEDS_INDIVIDUAL_LEVEL for this proposition's neighbours "
                "and arguably should for this one."
            ),
        ),
        _inconclusive(
            rows,
            "TH05",
            headline=(
                "The institutional graph gives network structure, but there is no per-node "
                "adoption outcome and no baseline-similarity control, so centrality cannot "
                "be shown to predict anything."
            ),
            basis=(
                "TH05 predicts that network centrality or exposure predicts adoption "
                "CONTROLLING for baseline similarity. The graph exists (824 entities, "
                "1,286 relations) and centrality is computable, but 'adoption' is recorded "
                "for no node and homophily cannot be controlled without node attributes - "
                "647 of 824 nodes are domain UNKNOWN."
            ),
            missing=[
                "a dated per-entity adoption outcome",
                "node attributes sufficient to control baseline similarity",
            ],
            evidence_used=[
                "W07: 7,071-record literature corpus in runtime/oslt.db",
                "W09/W10: institutional graph as re-adjudicated in "
                "docs/COUPLING_READJUDICATION.md",
            ],
            what_would_settle_it=(
                "Coding, per institution, the date it adopted a named practice - which is "
                "human coding, and governance/claim_release.py records zero human-coded "
                "lanes."
            ),
        ),
        _inconclusive(
            rows,
            "TH08",
            headline=(
                "Census 2021 gives a religion cross-tab at one instant. TH08 requires macro "
                "longitudinal or cross-jurisdiction models, and neither dimension exists in "
                "any workstream in hand."
            ),
            basis=(
                "TH08 predicts independent contextual moderation in longitudinal or "
                "cross-jurisdiction models. The only religion-linked measure available is "
                "Census 2021 RM173, a single cross-section of a question the Office for "
                "Statistics Regulation subsequently de-accredited. A cross-section cannot "
                "carry a moderation claim, and one jurisdiction cannot carry a "
                "cross-jurisdiction one."
            ),
            missing=[
                "a repeated measure of institutional religious authority over time",
                "a second jurisdiction measured on the same instrument",
            ],
            evidence_used=[
                "W01: Census 2021 RM173 gender identity by religion (cross-section)",
                "W05/W10/W11: no repeated religiosity or cross-jurisdiction series "
                "harvested",
            ],
            what_would_settle_it=(
                "Repeated cross-national attitude series - successive waves of a comparable "
                "social survey - plus a pre-registered specification, since a "
                "contextual-moderation claim tested after seeing the data is not a test."
            ),
        ),
    ]


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------

BALLOT_WARNING = (
    "**The ballot is unequal and no tally over it means what it looks like.** Twelve of "
    "these sixteen propositions belong to ASCERTAINMENT_SERVICE and four to "
    "MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL. INTRINSIC_RECOGNITION, "
    "MIXTURE_HETEROGENEITY and NULL_OR_ALTERNATIVE have **zero** open-testable "
    "propositions between them. Producing twelve ascertainment findings and no rival "
    "findings is an artefact of what is cheap to measure from open sources, not a result "
    "about which family explains anything. A comparative support index computed over this "
    "set measures data access."
)

NOT_RELEASED = (
    "**Nothing here is a released claim.** `governance/claim_release.py` declines every "
    "claim pending human review, and zero human-coded evidence lanes exist in this "
    "repository. These are CANDIDATE findings, produced by an engine, for an academic to "
    "adjudicate, reject or re-run. No line below has passed a human gate."
)


def render_markdown(payload: dict[str, Any]) -> str:
    findings: list[dict[str, Any]] = payload["findings"]
    by_direction: dict[str, list[str]] = defaultdict(list)
    for item in findings:
        by_direction[item["finding_direction"]].append(item["proposition_id"])

    lines: list[str] = []
    add = lines.append
    add("# Candidate findings for the sixteen open-testable propositions")
    add("")
    add(
        f"**Run:** {payload['generated_at'][:10]}. "
        "**Script:** `scripts/answer_open_testable.py`."
    )
    add("**Output:** `data/open_testable_findings.json`.")
    add("**Maximum claim tier reached anywhere below: DESCRIPTIVE_EVIDENCE_ONLY.**")
    add("")
    add(NOT_RELEASED)
    add("")
    add(BALLOT_WARNING)
    add("")
    for warning in payload["feasibility"]["coverage_asymmetry"]:
        add(f"- `{warning}`")
    add("")
    add("## Tally, and why the tally is not the point")
    add("")
    add("| Direction | Propositions |")
    add("|---|---|")
    for direction in ("SUPPORTS", "WEAKENS", "INCONCLUSIVE"):
        ids = by_direction.get(direction, [])
        add(f"| {direction} | {', '.join(ids) if ids else '-'} ({len(ids)}) |")
    add("")
    add(
        "Read the WEAKENS column first. It is the column carrying the kind of information "
        "this engine is licensed to produce: `compare_mechanisms` refutes mechanisms and "
        "stays silent among survivors, so a mechanism that could not reproduce a real "
        "series is genuinely disfavoured while one that could is merely compatible. The "
        "two SUPPORTS below attach to literal arithmetic claims - a denominator "
        "contributes; an instrument's response options change its estimate - and neither "
        "supports ASCERTAINMENT_SERVICE as an account of anything."
    )
    add("")
    add("## Summary table")
    add("")
    add("| ID | Family | Domain | Direction | Falsifier | One-line basis |")
    add("|---|---|---|---|---|---|")
    for item in findings:
        family = "AS" if item["model_family"] == "ASCERTAINMENT_SERVICE" else "TH"
        headline = item["headline"].replace("\n", " ")
        add(
            f"| **{item['proposition_id']}** | {family} | {item['domain']} | "
            f"**{item['finding_direction']}** | {item['falsifier_status']} | {headline} |"
        )
    add("")
    add("---")
    add("")
    for item in findings:
        add(f"## {item['proposition_id']} - {item['domain']}")
        add("")
        add(f"> {item['statement']}")
        add("")
        add(
            f"**Direction: {item['finding_direction']}.** "
            f"Falsifier: {item['falsifier_status']}. "
            f"Claim tier: {item['claim_tier']}. Released: no."
        )
        add("")
        add(f"**Prediction as registered.** {item['prediction']}")
        add("")
        add(f"**Registered falsifier.** {item['falsifier']}")
        add("")
        add(f"**Finding.** {item['headline']}")
        add("")
        add(f"**Basis.** {item['basis']}")
        add("")
        if item["evidence_used"]:
            add("**Evidence used.**")
            add("")
            for entry in item["evidence_used"]:
                add(f"- {entry}")
            add("")
        if item["limits"]:
            add("**Limits.**")
            add("")
            for entry in item["limits"]:
                add(f"- {entry}")
            add("")
        if item["what_would_settle_it"]:
            add(f"**What would settle it.** {item['what_would_settle_it']}")
            add("")
        add("---")
        add("")

    as08 = next(item for item in findings if item["proposition_id"] == "AS08")
    q = as08["quantities"]
    add("## Appendix: the AS08 continuous-provider computation in full")
    add("")
    add(
        "This is the computation `docs/REFERRAL_BASELINE.md` named as the thing that would "
        "settle its withdrawn second comparator: restrict to providers submitting "
        "continuously across the whole window. It was not asserted; it was run."
    )
    add("")
    add(
        f"Window: {q['window'][0]} to {q['window'][1]} (financial years "
        f"{q['financial_years'][0]} to {q['financial_years'][-1]}), "
        f"{len(q['financial_years']) * 12} months, measure MHS01 (people with an open "
        "referral at period end)."
    )
    add("")
    add(f"- Providers appearing at any point in the window: **{q['providers_seen_in_window']}**")
    add(
        "- Providers submitting a usable value in **every** month: "
        f"**{q['providers_submitting_continuously']}**"
    )
    add(
        f"- Providers present in the first month {q['providers_present_first_month']}, in "
        f"the last month {q['providers_present_last_month']} "
        f"(x{q['coverage_ratio']:.2f})"
    )
    add("")
    add(
        "| Financial year | Continuous cohort | Unrestricted provider sum | England "
        "published |"
    )
    add("|---|---:|---:|---:|")
    for year in q["financial_years"]:
        add(
            f"| {year} | {q['continuous_cohort_by_financial_year'][year]:,.0f} | "
            f"{q['unrestricted_by_financial_year'][year]:,.0f} | "
            f"{q['england_published_by_financial_year'][year]:,.0f} |"
        )
    add("")
    add(
        f"- Continuous cohort **x{q['continuous_cohort_ratio']:.3f}**; unrestricted "
        f"x{q['unrestricted_ratio']:.3f}; England published "
        f"x{q['england_published_ratio']:.3f}; submitting providers "
        f"x{q['coverage_ratio']:.2f}."
    )
    add(
        f"- **{q['log_growth_surviving_coverage_restriction']:.1%} of the log growth "
        "survives** restriction to the fixed cohort; "
        f"{q['log_growth_attributable_to_coverage']:.1%} is attributable to coverage and "
        "composition."
    )
    add(
        f"- The cohort holds {q['cohort_share_of_unrestricted_first_year']:.1%} of "
        "unrestricted activity in the first year and "
        f"{q['cohort_share_of_unrestricted_last_year']:.1%} in the last."
    )
    add("")
    add("### Mechanism comparison")
    add("")
    mech = q["mechanism_comparison"]
    add(
        "Run through `governance/mechanism_simulation.compare_mechanisms` against the "
        f"cohort series at a declared tolerance of {mech['tolerance']:.0%} of the observed "
        "range. Both grids were fixed before the run."
    )
    add("")
    add("| Mechanism | Grid | Accepted | Best distance | Direction |")
    add("|---|---:|---:|---:|---|")
    for result in mech["results"]:
        add(
            f"| `{result['mechanism_id']}` | {result['grid_size']} | {result['accepted']} "
            f"| {result['best_distance']:.1%} | {result['finding_direction']} |"
        )
    add("")
    add(f"- Refuted: {', '.join(mech['refuted']) or 'none'}")
    add(f"- Compatible: {', '.join(mech['compatible']) or 'none'}")
    add("")
    add(f"> {mech['interpretation_bound']}")
    add("")
    add("### What this does to the withdrawn comparator")
    add("")
    add(
        "`docs/REFERRAL_BASELINE.md` withdrew its second comparator on the ground that the "
        "apparent rise might be entirely a coverage artefact, and said every figure there "
        "should be treated as an upper bound and quite possibly as no change at all. On "
        "the coverage-fixed series a real rise remains: roughly four fifths of the log "
        "growth survives. That does **not** reinstate the withdrawn claim - the withdrawn "
        "argument was about the age gradient and the female excess within under-18s, and "
        "this computation is on an all-ages stock measure, so the stratum-specific claims "
        "remain untested. What it establishes is that the comparator series is not "
        "*wholly* an artefact, which was the live possibility."
    )
    add("")
    add("---")
    add("")
    add("## Provenance")
    add("")
    for key, value in payload["provenance"].items():
        add(f"- **{key}**: {value}")
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


def build(*, force: bool = False) -> dict[str, Any]:
    census = assess_feasibility(REGISTRY_ROOT)
    summary = census.summary()
    testable = list(summary["testable_ids"])  # type: ignore[arg-type]
    if len(testable) != 16:
        raise SystemExit(
            f"expected 16 open-testable propositions, found {len(testable)}: {testable}. "
            "The registry or the source register has changed; re-read the feasibility "
            "census before trusting anything here."
        )

    rows = load_registry()
    mhsds = load_mhsds(force=force)
    population = load_population(force=force)
    w09 = load_json(W09_PATH)
    fingertips = load_json(FINGERTIPS_PATH)
    coupling = load_json(COUPLING_PATH)
    anchors = [
        document["published_on"]
        for document in w09["documents"]
        if document.get("published_on")
    ]
    legislation_years = sorted({date[:4] for date in coupling.get("outcome_dates", [])})

    findings: list[Finding] = [
        analyse_as01(rows, mhsds, anchors),
        analyse_as02(rows, fingertips),
        analyse_as03(rows, mhsds),
        analyse_as06(rows, mhsds, population),
        analyse_as08(rows, mhsds),
        analyse_as09(rows, fingertips),
        analyse_as10(rows),
        analyse_as11(rows, mhsds, population),
        analyse_th04(rows, w09, legislation_years),
        analyse_th07(rows, coupling),
    ]
    findings.extend(analyse_remaining(rows))

    order = {pid: index for index, pid in enumerate(testable)}
    produced = {item.proposition_id for item in findings}
    if produced != set(testable):
        raise SystemExit(f"no finding produced for {sorted(set(testable) - produced)}")
    findings.sort(key=lambda item: order[item.proposition_id])

    counts: dict[str, int] = defaultdict(int)
    for item in findings:
        counts[item.finding_direction.value] += 1

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "script": "scripts/answer_open_testable.py",
        "released": False,
        "release_note": NOT_RELEASED,
        "ballot_warning": BALLOT_WARNING,
        "maximum_claim_tier": ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY.value,
        "feasibility": summary,
        "provenance": {
            "MHSDS": f"{mhsds['archive']} (local read, no network; DS077)",
            "population": "NOMIS NM_2002_1, England, 2016-2025, live",
            "W09": f"{W09_PATH.name}: {w09['documents_total']} documents, "
            f"{w09['distinct_anchor_dates']} distinct anchor dates",
            "W02_fingertips": f"{FINGERTIPS_PATH.name}: {len(fingertips['series'])} series",
            "W10_legislation": f"{len(legislation_years)} enactment years via "
            "legislation.gov.uk, as recorded in data/coupling_readjudication.json",
            "census": "data/census_2021_gender_identity.json and "
            "docs/CENSUS_2021_GENDER_IDENTITY.md",
        },
        "direction_counts": dict(sorted(counts.items())),
        "findings": [item.to_json() for item in findings],
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv[1:])
    payload = build(force="--force" in arguments)
    JSON_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    DOC_OUT.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload["direction_counts"], indent=2))
    for item in payload["findings"]:
        print(
            f"{item['proposition_id']:5s} {item['finding_direction']:13s} "
            f"{item['headline'][:88]}"
        )
    print(f"\nwritten to {JSON_OUT} and {DOC_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
