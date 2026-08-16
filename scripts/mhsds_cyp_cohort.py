"""Were the providers that joined MHSDS later disproportionately CYP services?

``docs/PROJECT_V2_SPECIFICATION.md`` §4 item 1 names this as the question that "directly
determines whether adolescent-specific trends are artefactual", and the warning box in
``docs/REFERRAL_BASELINE.md`` names it as "plausible and has not been checked". AS08 showed
that 82.6% of the log growth in the **all-ages** MHS01 series survives restriction to the 71
providers submitting in every one of 84 months. The withdrawn comparator claim was not about
all ages: it was about the **under-18** band and an emerging **female excess** within it. An
all-ages result does not settle an age-specific one, and this script does not pretend it does.

Three structural facts, established by enumeration before any statistic was computed
-------------------------------------------------------------------------------------

They are established rather than assumed, and they bound everything below. The enumeration
that establishes them is written into the JSON output under ``structural_limits``.

1. **There is no provider-by-age breakdown anywhere in the archive.** Age is published as
   ``England; Age`` only. Nothing crosses provider with age.
2. **Every provider-level age split begins 2023-04.** The only ones that exist are the
   ``a``/``b`` sibling pairs (aged 18 and over / aged under 18) on the crisis-care ``CCR*``
   and liaison-psychiatry ``PLS*`` families. ``England; Age`` itself begins 2022-04. The
   comparator window closes 2024-03.
3. **There is no age-by-sex cross-tab at any level.** ``England; Age`` and ``England;
   Gender`` are two separate breakdowns of the same England total.

Fact 1 and 2 together mean the brief's decisive step - "repeat the AS08 fixed-cohort
computation restricted to the under-18 band" over 2017/18-2023/24 - **cannot be computed from
this archive at all.** Not underpowered: absent. Fact 3 means the "emerging female excess
within the adolescent band" half of the withdrawn claim has no MHSDS test at any cohort size,
ever. NON-NEGOTIABLE 4 is why those are reported as the headline rather than buried under a
substitute window presented as the answer.

What could still be asked, and what happened when it was
---------------------------------------------------------

Each provider's join date comes from ``MHS01`` at ``Provider`` level (2016-05 onwards). Two
independent classifiers of how CYP-focused a provider is were then built **from the data,
never from provider names** - a name-matching heuristic on "CAMHS" or "children" would be
exactly the naming-coincidence error that killed three earlier findings here.

* **CYP intensity index** = ``MHS110`` (closed referrals for CYP aged 0-17 with at least two
  contacts) over the provider's own ``MHS01``. Broad: ~190 providers, 54 distinct join
  months, well powered.
* **Under-18 share** = a published under-18 sibling over its **own published parent**, within
  one measure family. Unconfounded by construction - numerator and denominator are the same
  measure, published by the same organisation for the same month - but published only by the
  minority of providers that run crisis-care or A&E-liaison teams.

The intensity index gave a large, highly significant association: later joiners looked far
more CYP-focused. **It is an artefact and this script says so.** Later joiners are much
smaller, the index is mechanically inflated for small providers (a CYP flow over an all-ages
stock), and controlling for provider size collapses the association to nothing. The
size-stratified contrast is worse than uninformative: the smallest size stratum contains
**no** continuous-cohort providers at all, so over most of the joiners' size range there is
no common support and no reweighting can manufacture one.

The unconfounded classifier is left holding the question, and it can only see three or four
joiners. Their under-18 shares are near 1.0 against a cohort median near 0.14, which points
toward the withdrawal box being right - but the significance flips on the inclusion of one
provider. Three joiners is not an answer, and NON-NEGOTIABLE 4 says to state the size and
stop rather than dress it up.

Other traps this shape is a response to
----------------------------------------

* **A suppressed under-18 cell beside a published parent is MISSING, never zero.** Read as
  zero it would classify small CYP-active providers as adult-only, and small under-18 counts
  are precisely what MHSDS suppresses. Such provider-months are dropped.
* **Nothing is summed across nesting levels and no age bands are merged.** ``England; Age``
  publishes single years 16 and 17 beside "11 to 15"; adding them into an "under 18"
  aggregate is the merge that is forbidden here, so band trends are reported per band.
* **Measure families are never pooled into one share.** ``CCR70b`` and ``CCR71b`` count
  referrals to the same teams under different urgency categories and are not disjoint parts
  of a common whole. Each family yields its own share.
* **The classifiers are measured 2023-04 onwards and applied to joins dated from 2016.** A
  provider's case mix is assumed stable enough to carry backwards. The assumption is stated
  and the within-provider stability of the share is measured, so a reader can price it.

No mechanism is calibrated here, so ``compare_mechanisms`` is not invoked and nothing
inherits its refutation asymmetry in either direction. Maximum tier is
``DESCRIPTIVE_EVIDENCE_ONLY``. Nothing is released.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
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
    monthly_window,
)
from oslt_research.connectors.nhs_statistics import parse_cell  # noqa: E402

# --------------------------------------------------------------------------------------
# Paths and frozen selections
# --------------------------------------------------------------------------------------

JSON_OUT = REPO_ROOT / "data" / "mhsds_cyp_cohort.json"
DOC_OUT = REPO_ROOT / "docs" / "MHSDS_CYP_ANALYSIS.md"
CACHE = REPO_ROOT / "runtime" / "mhsds_cyp_cells.json"

#: Exactly the AS08 window, which is exactly the withdrawn comparator's window (financial
#: years 2017/18-2023/24). Reused rather than re-chosen so that this answer bears on that
#: withdrawal and not on a window selected to suit an outcome.
WINDOW_FIRST = "2017-04"
WINDOW_LAST = "2024-03"

#: The window over which any provider-level under-18 figure is observable. Set by the data,
#: not by preference: every provider-level age split in the archive starts here.
CYP_FIRST = "2023-04"
CYP_LAST = "2026-06"

#: Age-split sibling families: ``(parent, under-18 child, what it counts)``.
#:
#: The share is child/parent within ONE family, so the parent is published and nothing is
#: added. Families stay apart because they are not disjoint parts of a common whole - a
#: crisis referral can be urgent and also reach a face-to-face contact, so CCR71 and CCR73
#: overlap by construction and summing them would double count.
CYP_FAMILIES: tuple[tuple[str, str, str], ...] = (
    ("CCR70", "CCR70b", "New emergency referrals to crisis care teams"),
    ("CCR71", "CCR71b", "New urgent referrals to crisis care teams"),
    ("CCR73", "CCR73b", "New urgent crisis referrals reaching a face-to-face contact"),
    ("CCR117", "CCR117b", "New very urgent referrals to crisis care teams"),
    ("CCR118", "CCR118b", "New very urgent crisis referrals reaching a face-to-face contact"),
    ("CCR119", "CCR119b", "New very urgent crisis referrals seen within 4 hours"),
    ("CCR120", "CCR120b", "New urgent crisis referrals seen within 24 hours"),
    ("PLS121", "PLS121b", "New referrals to liaison psychiatry teams from A&E"),
    ("PLS122", "PLS122b", "A&E liaison referrals reaching a face-to-face contact"),
    ("PLS123", "PLS123b", "A&E liaison referrals seen within 1 hour"),
)

#: The broad CYP-orientation numerator. Chosen because it is the only CYP-specific provider
#: measure published monthly by a large fraction of providers.
MEASURE_CYP_CLOSED_REFERRALS = "MHS110"

#: Provider-months needed in a family before it yields a share. Below this the share is an
#: estimate off a handful of small counts and puts noise into the correlation.
MIN_MONTHS_FOR_SHARE = 12

#: Provider-months of a usable MHS110 AND MHS01 needed before the intensity index is formed.
MIN_MONTHS_FOR_INDEX = 12

#: A parent of zero gives 0/0: no referrals of any age happened, which says nothing about
#: case mix. Such months are dropped rather than scored as a zero share.
MIN_PARENT_FOR_SHARE = 1.0

#: The floor for calling a classifier's association with join date genuine rather than a
#: size artefact. Chosen before the numbers were seen; the raw association turned out to be
#: +0.59 and the size-controlled one +0.04, so nothing hinges on where between them it sits.
PARTIAL_RHO_FLOOR = 0.20

#: A group contrast needs at least this many members on the smaller side before it is
#: reported as a result rather than as an observation about too few providers.
MIN_GROUP_FOR_A_VERDICT = 10

PERMUTATION_DRAWS = 20000
PERMUTATION_SEED = 20260816


# --------------------------------------------------------------------------------------
# Periods
# --------------------------------------------------------------------------------------


def month_ordinal(label: str) -> int:
    """Months since year zero, for arithmetic only. Never rendered back as a date."""

    year, month = label.split("-")
    return int(year) * 12 + (int(month) - 1)


def month_label(ordinal: int) -> str:
    return f"{ordinal // 12:04d}-{ordinal % 12 + 1:02d}"


def month_range(first: str, last: str) -> list[str]:
    start, end = month_ordinal(first), month_ordinal(last)
    if end < start:
        raise ValueError(f"window {first}..{last} runs backwards")
    return [month_label(value) for value in range(start, end + 1)]


def financial_year(label: str) -> str:
    """The English financial year a month falls in. April-March, never coerced to a year."""

    year, month = (int(part) for part in label.split("-"))
    start = year if month >= 4 else year - 1
    return f"{start:04d}/{(start + 1) % 100:02d}"


# --------------------------------------------------------------------------------------
# Statistics (stdlib only; scipy is not a dependency of this project)
# --------------------------------------------------------------------------------------


def rank(values: Sequence[float]) -> list[float]:
    """Average ranks with ties shared. Ties matter: many providers share a join month."""

    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        shared = (position + end) / 2.0 + 1.0
        for index in order[position : end + 1]:
            ranks[index] = shared
        position = end + 1
    return ranks


def pearson(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 3:
        raise ValueError("need at least three paired observations")
    mean_left, mean_right = statistics.mean(left), statistics.mean(right)
    numerator = sum(
        (a - mean_left) * (b - mean_right) for a, b in zip(left, right, strict=True)
    )
    denominator = math.sqrt(
        sum((a - mean_left) ** 2 for a in left) * sum((b - mean_right) ** 2 for b in right)
    )
    if denominator == 0:
        raise ValueError("a constant series has no correlation")
    return numerator / denominator


def spearman(left: Sequence[float], right: Sequence[float]) -> float:
    """Rank correlation.

    A Pearson correlation on a bounded proportion against a date with mass points at the
    collection's onboarding waves would report the shape of the distribution as much as the
    association.
    """

    return pearson(rank(left), rank(right))


def partial_spearman(
    left: Sequence[float], right: Sequence[float], control: Sequence[float]
) -> float:
    """Spearman between ``left`` and ``right`` with ``control`` partialled out.

    This is the single most load-bearing function in the file. Provider size is correlated
    with join date (later joiners are smaller) and with any ratio whose numerator and
    denominator have different time bases, so a raw correlation between join date and a
    CYP index can be produced entirely by size. Partialling it out is what turns a striking
    number into a tested one.
    """

    r_lr = spearman(left, right)
    r_lc = spearman(left, control)
    r_rc = spearman(right, control)
    denominator = math.sqrt((1 - r_lc**2) * (1 - r_rc**2))
    if denominator == 0:
        raise ValueError("the control is perfectly rank-correlated with a variable")
    return (r_lr - r_lc * r_rc) / denominator


def permutation_p_two_sided(
    left: Sequence[float], right: Sequence[float], *, draws: int = PERMUTATION_DRAWS
) -> float:
    """Two-sided p for Spearman by shuffling the pairing.

    Permutation rather than the asymptotic t because the values are bounded, skewed and
    tie-heavy. The null is exactly "the pairing carries nothing", which shuffling realises
    without assuming a distribution.
    """

    observed = abs(spearman(left, right))
    pool = list(right)
    rng = random.Random(PERMUTATION_SEED)
    hits = 0
    for _ in range(draws):
        rng.shuffle(pool)
        if abs(spearman(left, pool)) >= observed:
            hits += 1
    return (hits + 1) / (draws + 1)


def minimum_detectable_rho(n: int, *, alpha: float = 0.05, power: float = 0.80) -> float:
    """Smallest |rho| a two-sided test on ``n`` pairs detects with ``power``.

    Reported beside every correlation because a null is only informative if the test could
    have seen something. Fisher z; for a rank correlation it is an approximation and is
    quoted as one.
    """

    if n < 10:
        raise ValueError("the Fisher approximation is not usable below about ten pairs")
    if not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("alpha and power must lie strictly between 0 and 1")
    z_alpha = 1.959963985  # two-sided 0.05
    z_beta = 0.8416212336  # 0.80
    return math.tanh((z_alpha + z_beta) / math.sqrt(n - 3))


def mann_whitney_u(left: Sequence[float], right: Sequence[float]) -> tuple[float, float]:
    """``(U for left, tie-corrected normal-approximation two-sided p)``.

    Used for the cohort-versus-joiners contrast, where the groups are of very unequal size
    and the values are bounded proportions rather than anything normal. Shares of exactly
    0.0 are common among adult providers, hence the tie correction.
    """

    if not left or not right:
        raise ValueError("both groups must be non-empty")
    combined = list(left) + list(right)
    ranks = rank(combined)
    n1, n2 = len(left), len(right)
    u_left = sum(ranks[:n1]) - n1 * (n1 + 1) / 2.0
    counts: Counter[float] = Counter(combined)
    n = n1 + n2
    tie_term = sum(count**3 - count for count in counts.values())
    variance = (n1 * n2 / 12.0) * ((n + 1) - tie_term / (n * (n - 1)))
    if variance <= 0:
        return u_left, 1.0
    z = (u_left - n1 * n2 / 2.0) / math.sqrt(variance)
    return u_left, math.erfc(abs(z) / math.sqrt(2.0))


def log_growth_share(part: float, whole: float) -> float:
    """Share of log growth in ``whole`` reproduced by ``part``. AS08's decomposition."""

    if whole <= 0 or part <= 0:
        raise ValueError("ratios must be positive to take a log")
    if math.isclose(math.log(whole), 0.0):
        raise ValueError("the unrestricted series did not grow; there is no share to take")
    return math.log(part) / math.log(whole)


# --------------------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------------------


def cyp_measure_ids() -> set[str]:
    ids: set[str] = {MEASURE_CYP_CLOSED_REFERRALS}
    for parent, child, _label in CYP_FAMILIES:
        ids.update({parent, child})
    return ids


def extract(*, force: bool = False, archive: Path | None = None) -> dict[str, Any]:
    """One streaming pass over the ~660MB archive, cached under ``runtime/``.

    A second pass would cost minutes for nothing, and a second pass is exactly where a
    selection silently drifts from the first. Everything needed is taken at once, including
    the per-measure provider spans that establish the structural limits - those are
    evidence, not diagnostics, and are written to the output.
    """

    if CACHE.exists() and not force:
        return json.loads(CACHE.read_text(encoding="utf-8"))

    reader = MhsdsLocalReader(archive) if archive else MhsdsLocalReader()
    wanted_cyp = cyp_measure_ids()

    mhs01_provider: dict[str, dict[str, float | None]] = defaultdict(dict)
    mhs01_england: dict[str, float | None] = {}
    cyp_provider: dict[str, dict[str, dict[str, float | None]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    england_age: dict[str, dict[str, dict[str, float | None]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    provider_spans: dict[str, set[str]] = defaultdict(set)
    breakdowns_seen: set[str] = set()

    for _member, row in reader.iter_rows():
        breakdown = (row.get("BREAKDOWN") or "").strip()
        breakdowns_seen.add(breakdown)
        measure_id = (row.get("MEASURE_ID") or "").strip()
        month = monthly_window(
            row.get("REPORTING_PERIOD_START", ""), row.get("REPORTING_PERIOD_END", "")
        )
        if month is None:
            # A rolling-window row published under the same id and end date as a monthly
            # one. Mixing the two is the error the connector exists to prevent.
            continue
        label = month.label
        value = parse_cell(row.get("MEASURE_VALUE") or "")

        if breakdown == BREAKDOWN_PROVIDER:
            provider = (row.get("PRIMARY_LEVEL") or "").strip()
            if not provider:
                continue
            provider_spans[measure_id].add(label)
            if measure_id == MEASURE_OPEN_REFERRALS:
                mhs01_provider[label][provider] = value
            elif measure_id in wanted_cyp:
                cyp_provider[measure_id][label][provider] = value
        elif breakdown == BREAKDOWN_ENGLAND and measure_id == MEASURE_OPEN_REFERRALS:
            if (row.get("PRIMARY_LEVEL") or "").strip() == BREAKDOWN_ENGLAND:
                mhs01_england[label] = value
        elif breakdown == BREAKDOWN_ENGLAND_AGE and measure_id in {
            MEASURE_OPEN_REFERRALS,
            MEASURE_NEW_REFERRALS,
        }:
            band = (row.get("SECONDARY_LEVEL") or "").strip()
            if (row.get("PRIMARY_LEVEL") or "").strip() == BREAKDOWN_ENGLAND and band:
                england_age[measure_id][label][band] = value

    payload = {
        "archive": str(reader.archive_path),
        "extracted_at": datetime.now(UTC).isoformat(),
        "breakdowns_in_archive": sorted(breakdowns_seen),
        "provider_measure_spans": {
            measure_id: {
                "months": len(labels),
                "first": min(labels),
                "last": max(labels),
            }
            for measure_id, labels in sorted(provider_spans.items())
        },
        "mhs01_provider": {month: dict(v) for month, v in mhs01_provider.items()},
        "mhs01_england": mhs01_england,
        "cyp_provider": {
            measure: {month: dict(v) for month, v in months.items()}
            for measure, months in cyp_provider.items()
        },
        "england_age": {
            measure: {month: dict(v) for month, v in months.items()}
            for measure, months in england_age.items()
        },
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(payload), encoding="utf-8")
    return payload


# --------------------------------------------------------------------------------------
# Provider join dates and cohorts
# --------------------------------------------------------------------------------------


def first_reporting_month(
    provider_cells: dict[str, dict[str, float | None]],
) -> dict[str, str]:
    """First month in which a provider published a USABLE MHS01 value.

    "Usable" excludes both absence and suppression. A provider whose first appearance is a
    suppressed cell has not yet shown it is submitting a countable figure, and dating the
    join there would date it earlier than the evidence supports.
    """

    first: dict[str, str] = {}
    for label in sorted(provider_cells):
        for provider, value in provider_cells[label].items():
            if value is None:
                continue
            if provider not in first or month_ordinal(label) < month_ordinal(first[provider]):
                first[provider] = label
    return first


@dataclass(frozen=True)
class Cohort:
    """AS08's continuous cohort and the complementary joiner set."""

    months: tuple[str, ...]
    continuous: tuple[str, ...]
    joiners: tuple[str, ...]
    series: tuple[float, ...]
    unrestricted: tuple[float, ...]
    providers_present: dict[str, int]


def build_cohort(
    provider_cells: dict[str, dict[str, float | None]], first: str, last: str
) -> Cohort:
    """A usable value in EVERY month, plus the providers present at the end but not the start.

    ``joiners`` is the set the withdrawal box hypothesises are disproportionately CYP: present
    in the window's last month, absent or unusable in its first. A provider absent from a
    month has not reported zero activity and a suppressed cell is not zero either; both keep
    a provider out of the cohort rather than pushing its series into a trough.
    """

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

    first_month, last_month = months[0], months[-1]
    joiners = tuple(
        sorted(
            provider
            for provider, value in provider_cells[last_month].items()
            if value is not None and provider_cells[first_month].get(provider) is None
        )
    )
    return Cohort(
        months=tuple(months),
        continuous=continuous,
        joiners=joiners,
        series=tuple(
            float(sum(provider_cells[month][provider] for provider in continuous))
            for month in months
        ),
        unrestricted=tuple(
            float(sum(value for value in provider_cells[month].values() if value is not None))
            for month in months
        ),
        providers_present={month: len(provider_cells[month]) for month in months},
    )


def financial_year_means(months: Sequence[str], values: Sequence[float]) -> dict[str, float]:
    """Mean monthly value per COMPLETE financial year. Partial years are dropped."""

    grouped: dict[str, list[float]] = defaultdict(list)
    for month, value in zip(months, values, strict=True):
        grouped[financial_year(month)].append(value)
    return {
        year: statistics.mean(items)
        for year, items in sorted(grouped.items())
        if len(items) == 12
    }


# --------------------------------------------------------------------------------------
# Classifier 1: the CYP intensity index (broad, and size-confounded)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Intensity:
    """One provider's CYP-closed-referral count relative to its own all-ages activity.

    ``size`` travels with the index because the index cannot be interpreted without it: a
    CYP flow over an all-ages stock is mechanically larger for a small provider whose
    referrals turn over quickly, whatever its case mix.
    """

    months_used: int
    cyp_total: float
    activity_total: float
    index: float
    size: float


def cyp_intensity(
    cyp_cells: dict[str, dict[str, dict[str, float | None]]],
    provider_cells: dict[str, dict[str, float | None]],
    months: Sequence[str],
) -> dict[str, Intensity]:
    """MHS110 over MHS01 per provider, over months where BOTH are usable.

    Months where either side is missing or suppressed are dropped from both numerator and
    denominator together, so the ratio is always taken over the same set of months. Pairing
    a numerator month against a denominator month that is not there would be arithmetic on
    a hole.
    """

    cyp = cyp_cells.get(MEASURE_CYP_CLOSED_REFERRALS, {})
    numerator: dict[str, float] = defaultdict(float)
    denominator: dict[str, float] = defaultdict(float)
    used: Counter[str] = Counter()
    for label in months:
        for provider, value in cyp.get(label, {}).items():
            activity = provider_cells.get(label, {}).get(provider)
            if value is None or activity is None or activity <= 0:
                continue
            numerator[provider] += value
            denominator[provider] += activity
            used[provider] += 1
    return {
        provider: Intensity(
            months_used=used[provider],
            cyp_total=numerator[provider],
            activity_total=denominator[provider],
            index=numerator[provider] / denominator[provider],
            size=denominator[provider] / used[provider],
        )
        for provider in numerator
        if used[provider] >= MIN_MONTHS_FOR_INDEX and denominator[provider] > 0
    }


# --------------------------------------------------------------------------------------
# Classifier 2: the under-18 share (unconfounded, and sparse)
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FamilyShare:
    """One provider's under-18 share of one published measure family."""

    parent: str
    child: str
    months_used: int
    under_18: float
    total: float
    share: float
    monthly_shares: tuple[float, ...]

    @property
    def share_stdev(self) -> float | None:
        """Within-provider month-to-month spread of the share.

        Reported because the classification rests on case mix being a stable trait. A
        provider whose under-18 share swings between 0.05 and 0.8 across the observation
        window is not a service type, it is noise.
        """

        if len(self.monthly_shares) < 2:
            return None
        return statistics.stdev(self.monthly_shares)


def family_shares(
    cyp_cells: dict[str, dict[str, dict[str, float | None]]],
    parent: str,
    child: str,
    months: Sequence[str],
    *,
    min_months: int = MIN_MONTHS_FOR_SHARE,
) -> dict[str, FamilyShare]:
    """Per-provider under-18 share of ``parent``, from its own published ``child`` sibling.

    Three exclusions, each of which would otherwise manufacture a spuriously low share:

    1. A **suppressed under-18 cell** beside a published parent is missing, not zero. Small
       under-18 counts are precisely what MHSDS suppresses, so reading them as zero would
       systematically classify small CYP-active providers as adult-only.
    2. A **missing parent** leaves the child with no denominator. The month is dropped
       rather than given a denominator borrowed from another month or another measure.
    3. A **parent of zero** gives 0/0. No referrals of any age happened, which says nothing
       about case mix.
    """

    parent_cells = cyp_cells.get(parent, {})
    child_cells = cyp_cells.get(child, {})
    accumulated: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for label in months:
        children = child_cells.get(label, {})
        for provider, parent_value in parent_cells.get(label, {}).items():
            child_value = children.get(provider)
            if parent_value is None or child_value is None:
                continue
            if parent_value < MIN_PARENT_FOR_SHARE:
                continue
            if child_value > parent_value:
                # A child larger than its own parent means these are not the sibling and
                # whole this code believes them to be. Refuse rather than clamp.
                raise ValueError(
                    f"{child} exceeds {parent} for provider {provider} in {label} "
                    f"({child_value} > {parent_value}); the assumed part/whole relation "
                    "between these two measures does not hold and the share is meaningless"
                )
            accumulated[provider].append((child_value, parent_value))

    shares: dict[str, FamilyShare] = {}
    for provider, pairs in accumulated.items():
        if len(pairs) < min_months:
            continue
        under = sum(pair[0] for pair in pairs)
        total = sum(pair[1] for pair in pairs)
        if total <= 0:
            continue
        shares[provider] = FamilyShare(
            parent=parent,
            child=child,
            months_used=len(pairs),
            under_18=under,
            total=total,
            share=under / total,
            monthly_shares=tuple(pair[0] / pair[1] for pair in pairs),
        )
    return shares


def pooled_share(
    cyp_cells: dict[str, dict[str, dict[str, float | None]]],
    months: Sequence[str],
    *,
    min_months: int = MIN_MONTHS_FOR_SHARE,
) -> dict[str, float]:
    """One under-18 share per provider: the MEDIAN of its per-family shares.

    The median rather than a pooled ratio, because pooling would sum overlapping families
    (an urgent referral also appears among those reaching a face-to-face contact) and double
    count. Taking the median across families keeps every family a separate estimate of the
    same provider trait and lets them disagree visibly.
    """

    per_provider: dict[str, list[float]] = defaultdict(list)
    for parent, child, _label in CYP_FAMILIES:
        for provider, item in family_shares(
            cyp_cells, parent, child, months, min_months=min_months
        ).items():
            per_provider[provider].append(item.share)
    return {
        provider: statistics.median(values) for provider, values in per_provider.items()
    }


# --------------------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------------------


def analyse(cells: dict[str, Any]) -> dict[str, Any]:
    provider_cells: dict[str, dict[str, float | None]] = cells["mhs01_provider"]
    joined = first_reporting_month(provider_cells)
    cohort = build_cohort(provider_cells, WINDOW_FIRST, WINDOW_LAST)
    cyp_months = month_range(CYP_FIRST, CYP_LAST)
    cyp_cells = cells["cyp_provider"]

    intensity = cyp_intensity(cyp_cells, provider_cells, cyp_months)
    shares = pooled_share(cyp_cells, cyp_months)
    per_family = {
        parent: family_shares(cyp_cells, parent, child, cyp_months)
        for parent, child, _label in CYP_FAMILIES
    }

    result: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_tier": "DESCRIPTIVE_EVIDENCE_ONLY",
        "released": False,
        "archive": cells["archive"],
        "window": {"first": WINDOW_FIRST, "last": WINDOW_LAST},
        "cyp_observation_window": {"first": CYP_FIRST, "last": CYP_LAST},
        "structural_limits": structural_limits(cells),
        "cohort": {
            "providers_ever_present": len(
                {p for month in cohort.months for p in provider_cells[month]}
            ),
            "continuous_cohort_size": len(cohort.continuous),
            "joiner_set_size": len(cohort.joiners),
            "providers_present_first_month": cohort.providers_present[cohort.months[0]],
            "providers_present_last_month": cohort.providers_present[cohort.months[-1]],
            "all_ages_continuous_ratio": _fy_ratio(cohort.months, cohort.series),
            "all_ages_unrestricted_ratio": _fy_ratio(cohort.months, cohort.unrestricted),
        },
        "join_dates": {
            "providers_with_a_join_month": len(joined),
            "earliest": min(joined.values()),
            "latest": max(joined.values()),
            "by_financial_year": _joins_by_year(joined),
        },
        "classifier_intensity": _analyse_intensity(intensity, joined, cohort),
        "classifier_share": _analyse_share(shares, per_family, joined, cohort, cyp_cells),
        "all_ages_decomposition": _all_ages_decomposition(cohort, provider_cells),
        "under_18_fixed_cohort": _under_18_fixed_cohort(cyp_cells),
        "england_age_bands": _england_age_bands(cells),
        "sex_within_under_18": {
            "testable": False,
            "reason": (
                "MHSDS publishes 'England; Age' and 'England; Gender' as two separate "
                "breakdowns of the same England total. No breakdown in the archive crosses "
                "age with sex at any geography, and constructing one would require summing "
                "across nesting levels. The 'emerging female excess within the adolescent "
                "band' half of the withdrawn claim has no MHSDS test at any cohort size."
            ),
        },
    }
    result["verdict"] = verdict(result)
    return result


def structural_limits(cells: dict[str, Any]) -> dict[str, Any]:
    """What the archive's own shape rules out, established by enumeration."""

    spans = cells["provider_measure_spans"]
    age_split = {child: spans[child] for _p, child, _l in CYP_FAMILIES if child in spans}
    england_age_months = sorted(cells["england_age"].get(MEASURE_OPEN_REFERRALS, {}))
    return {
        "provider_by_age_breakdown_exists": any(
            "Provider" in breakdown and "Age" in breakdown
            for breakdown in cells["breakdowns_in_archive"]
        ),
        "breakdowns_in_archive": cells["breakdowns_in_archive"],
        "earliest_provider_level_age_split_month": (
            min(span["first"] for span in age_split.values()) if age_split else None
        ),
        "provider_age_split_spans": age_split,
        "england_age_first_month": england_age_months[0] if england_age_months else None,
        "under_18_cohort_over_comparator_window_possible": False,
        "why": (
            "Every provider-level age split in the archive begins 2023-04 and the "
            "comparator window closes 2024-03; England; Age begins 2022-04. There is no "
            "under-18 provider-level series over 2017/18-2023/24 to restrict, so the "
            "fixed-cohort computation AS08 ran on all ages cannot be run on the under-18 "
            "band at all."
        ),
    }


def _fy_ratio(months: Sequence[str], values: Sequence[float]) -> dict[str, Any]:
    fy = financial_year_means(months, values)
    years = sorted(fy)
    return {
        "by_financial_year": fy,
        "first_year": years[0],
        "last_year": years[-1],
        "ratio": fy[years[-1]] / fy[years[0]],
    }


def _joins_by_year(joined: dict[str, str]) -> dict[str, int]:
    counts: Counter[str] = Counter(financial_year(label) for label in joined.values())
    return dict(sorted(counts.items()))


def _analyse_intensity(
    intensity: dict[str, Intensity], joined: dict[str, str], cohort: Cohort
) -> dict[str, Any]:
    """The broad classifier, and the size test that decides whether to believe it."""

    providers = sorted(p for p in intensity if p in joined)
    out: dict[str, Any] = {
        "definition": (
            "MHS110 (closed referrals for CYP aged 0-17 with at least two contacts) over the "
            "same provider's MHS01, over months where both are usable"
        ),
        "n": len(providers),
        "median_index": (
            statistics.median(intensity[p].index for p in providers) if providers else None
        ),
    }
    if len(providers) < MIN_GROUP_FOR_A_VERDICT:
        out["test"] = "NOT_RUN"
        out["reason"] = "fewer than ten providers carry both an index and a join month"
        return out

    join_values = [float(month_ordinal(joined[p])) for p in providers]
    index_values = [intensity[p].index for p in providers]
    size_values = [math.log(intensity[p].size) for p in providers]

    raw = spearman(join_values, index_values)
    controlled = partial_spearman(join_values, index_values, size_values)
    out.update(
        {
            "test": "Spearman rank correlation, join month against CYP intensity index",
            "distinct_join_months": len(set(join_values)),
            "spearman_rho_raw": raw,
            "permutation_p_two_sided": permutation_p_two_sided(join_values, index_values),
            "minimum_detectable_rho_at_80_percent_power": minimum_detectable_rho(
                len(providers)
            ),
            "spearman_rho_join_against_log_size": spearman(join_values, size_values),
            "spearman_rho_index_against_log_size": spearman(index_values, size_values),
            "partial_spearman_controlling_for_log_size": controlled,
            "size_confounded": abs(controlled) < PARTIAL_RHO_FLOOR < abs(raw),
        }
    )
    out["by_size_tertile"] = _tertiles(providers, intensity, joined, cohort)
    out["common_support"] = _common_support(providers, intensity, cohort)
    out["interpretation"] = (
        "The raw association is large and would, taken alone, say later joiners were far "
        "more CYP-focused. Controlling for provider size removes it. The index is a CYP flow "
        "over an all-ages stock and is mechanically larger for small providers; later joiners "
        "are much smaller. This classifier therefore cannot answer the question."
        if out["size_confounded"]
        else "The association survives adjustment for provider size."
    )
    return out


def _tertiles(
    providers: Sequence[str],
    intensity: dict[str, Intensity],
    joined: dict[str, str],
    cohort: Cohort,
) -> list[dict[str, Any]]:
    """Repeat the correlation and the group contrast inside size tertiles.

    A partial correlation assumes the confounding is monotone and linear in ranks.
    Stratifying makes no such assumption, so if both agree the conclusion does not rest on
    the form of the adjustment.
    """

    ordered = sorted(providers, key=lambda p: intensity[p].size)
    third = len(ordered) // 3
    groups = [ordered[:third], ordered[third : 2 * third], ordered[2 * third :]]
    cohort_set, joiner_set = set(cohort.continuous), set(cohort.joiners)
    out: list[dict[str, Any]] = []
    for name, group in zip(("small", "mid", "large"), groups, strict=True):
        entry: dict[str, Any] = {
            "tertile": name,
            "n": len(group),
            "median_index": statistics.median(intensity[p].index for p in group),
            "median_size": statistics.median(intensity[p].size for p in group),
        }
        if len(group) >= MIN_GROUP_FOR_A_VERDICT:
            entry["spearman_rho_join_against_index"] = spearman(
                [float(month_ordinal(joined[p])) for p in group],
                [intensity[p].index for p in group],
            )
        in_cohort = [intensity[p].index for p in group if p in cohort_set]
        in_joiners = [intensity[p].index for p in group if p in joiner_set]
        entry["continuous_cohort_n"] = len(in_cohort)
        entry["joiners_n"] = len(in_joiners)
        if in_cohort and in_joiners:
            _u, p = mann_whitney_u(in_joiners, in_cohort)
            entry["continuous_cohort_median"] = statistics.median(in_cohort)
            entry["joiners_median"] = statistics.median(in_joiners)
            entry["mann_whitney_p_two_sided"] = p
        else:
            entry["comparable"] = False
            entry["reason"] = (
                "one of the two groups has no member in this size tertile, so there is no "
                "common support and no adjustment can compare them here"
            )
        out.append(entry)
    return out


def _common_support(
    providers: Sequence[str], intensity: dict[str, Intensity], cohort: Cohort
) -> dict[str, Any]:
    """Do the cohort and the joiners overlap in size at all?

    If they do not, every adjusted comparison between them is extrapolation dressed as
    adjustment. This is reported before any adjusted contrast so the reader can discount it.
    """

    cohort_set, joiner_set = set(cohort.continuous), set(cohort.joiners)
    cohort_sizes = [intensity[p].size for p in providers if p in cohort_set]
    joiner_sizes = [intensity[p].size for p in providers if p in joiner_set]
    if not cohort_sizes or not joiner_sizes:
        return {"overlap_computable": False}
    low, high = max(min(cohort_sizes), min(joiner_sizes)), min(
        max(cohort_sizes), max(joiner_sizes)
    )
    return {
        "overlap_computable": True,
        "continuous_cohort_size_range": [min(cohort_sizes), max(cohort_sizes)],
        "joiner_size_range": [min(joiner_sizes), max(joiner_sizes)],
        "joiners_inside_cohort_size_range": sum(
            1 for size in joiner_sizes if low <= size <= high
        ),
        "joiners_total": len(joiner_sizes),
        "cohort_inside_joiner_size_range": sum(
            1 for size in cohort_sizes if low <= size <= high
        ),
        "cohort_total": len(cohort_sizes),
    }


def _analyse_share(
    shares: dict[str, float],
    per_family: dict[str, dict[str, FamilyShare]],
    joined: dict[str, str],
    cohort: Cohort,
    cyp_cells: dict[str, dict[str, dict[str, float | None]]],
) -> dict[str, Any]:
    """The unconfounded classifier: a published under-18 sibling over its own parent."""

    cohort_set, joiner_set = set(cohort.continuous), set(cohort.joiners)
    in_cohort = sorted(shares[p] for p in shares if p in cohort_set)
    in_joiners = sorted(shares[p] for p in shares if p in joiner_set)
    paired = [(float(month_ordinal(joined[p])), shares[p]) for p in sorted(shares) if p in joined]

    out: dict[str, Any] = {
        "definition": (
            "median across measure families of (published under-18 sibling / its own "
            "published parent), per provider"
        ),
        "families": {
            parent: {
                "measure": label,
                "providers_with_a_share": len(per_family[parent]),
                "median_share": (
                    statistics.median(i.share for i in per_family[parent].values())
                    if per_family[parent]
                    else None
                ),
                "mean_within_provider_share_stdev": _mean_stdev(per_family[parent]),
            }
            for parent, _child, label in CYP_FAMILIES
        },
        "providers_with_a_share": len(shares),
        "continuous_cohort_n": len(in_cohort),
        "joiners_n": len(in_joiners),
        "why_so_few": (
            "The parent measures are crisis-care and A&E-liaison referral counts, run by a "
            "minority of providers: across the observation window the parent is missing in "
            "roughly 93% of provider-months. The joiners are also small, so their cells are "
            "the ones most often suppressed - and a suppressed cell is excluded, never read "
            "as zero."
        ),
    }
    if in_cohort and in_joiners:
        _u, p = mann_whitney_u(in_joiners, in_cohort)
        out["continuous_cohort_median_share"] = statistics.median(in_cohort)
        out["joiners_median_share"] = statistics.median(in_joiners)
        out["joiner_shares"] = in_joiners
        out["mann_whitney_p_two_sided"] = p
    if len(paired) >= MIN_GROUP_FOR_A_VERDICT:
        out["n_paired"] = len(paired)
        out["distinct_join_months"] = len({pair[0] for pair in paired})
        out["spearman_rho"] = spearman(
            [pair[0] for pair in paired], [pair[1] for pair in paired]
        )
        out["permutation_p_two_sided"] = permutation_p_two_sided(
            [pair[0] for pair in paired], [pair[1] for pair in paired]
        )
        out["minimum_detectable_rho_at_80_percent_power"] = minimum_detectable_rho(len(paired))

    out["sensitivity_to_the_month_threshold"] = _share_sensitivity(
        cyp_cells, joiner_set, cohort_set
    )
    out["powered"] = min(len(in_cohort), len(in_joiners)) >= MIN_GROUP_FOR_A_VERDICT
    return out


def _share_sensitivity(
    cyp_cells: dict[str, dict[str, dict[str, float | None]]],
    joiner_set: set[str],
    cohort_set: set[str],
) -> list[dict[str, Any]]:
    """Re-run the group contrast at looser month thresholds.

    With three joiners, whether the contrast is significant can turn on whether a fourth
    provider clears the threshold. Showing that instability is the point: a result that
    flips on one organisation is not a result.
    """

    months = month_range(CYP_FIRST, CYP_LAST)
    out: list[dict[str, Any]] = []
    for threshold in (12, 6, 3):
        shares = pooled_share(cyp_cells, months, min_months=threshold)
        in_cohort = [shares[p] for p in shares if p in cohort_set]
        in_joiners = sorted(shares[p] for p in shares if p in joiner_set)
        entry: dict[str, Any] = {
            "min_months": threshold,
            "providers_with_a_share": len(shares),
            "continuous_cohort_n": len(in_cohort),
            "joiners_n": len(in_joiners),
            "joiner_shares": in_joiners,
        }
        if in_cohort and in_joiners:
            _u, p = mann_whitney_u(in_joiners, in_cohort)
            entry["continuous_cohort_median_share"] = statistics.median(in_cohort)
            entry["joiners_median_share"] = statistics.median(in_joiners)
            entry["mann_whitney_p_two_sided"] = p
        out.append(entry)
    return out


def _mean_stdev(shares: dict[str, FamilyShare]) -> float | None:
    spreads = [i.share_stdev for i in shares.values() if i.share_stdev is not None]
    return statistics.mean(spreads) if spreads else None


def _all_ages_decomposition(
    cohort: Cohort, provider_cells: dict[str, dict[str, float | None]]
) -> dict[str, Any]:
    """AS08's all-ages decomposition, recomputed here so this file stands alone."""

    cohort_ratio = _fy_ratio(cohort.months, cohort.series)["ratio"]
    unrestricted_ratio = _fy_ratio(cohort.months, cohort.unrestricted)["ratio"]
    last_month = cohort.months[-1]
    last_cells = provider_cells[last_month]
    cohort_set, joiner_set = set(cohort.continuous), set(cohort.joiners)
    cohort_activity = sum(
        v for p, v in last_cells.items() if p in cohort_set and v is not None
    )
    joiner_activity = sum(
        v for p, v in last_cells.items() if p in joiner_set and v is not None
    )
    total = cohort_activity + joiner_activity
    return {
        "continuous_cohort_ratio": cohort_ratio,
        "unrestricted_ratio": unrestricted_ratio,
        "log_growth_share_surviving_cohort_restriction": log_growth_share(
            cohort_ratio, unrestricted_ratio
        ),
        "log_growth_share_attributable_to_coverage": 1.0
        - log_growth_share(cohort_ratio, unrestricted_ratio),
        "final_month": last_month,
        "cohort_share_of_final_month_activity": cohort_activity / total if total else None,
        "joiner_share_of_final_month_activity": joiner_activity / total if total else None,
        "note": (
            "This is all ages. It is reproduced here only so the age-specific question has "
            "its all-ages context on the same page; it does not answer it."
        ),
    }


def _under_18_fixed_cohort(
    cyp_cells: dict[str, dict[str, dict[str, float | None]]],
) -> dict[str, Any]:
    """The under-18 fixed-cohort computation, on the only window where it can be run.

    Reported with its cohort size FIRST and with an explicit statement that the window does
    not reach the comparator's. NON-NEGOTIABLE 4 requires the size before the trend and
    requires saying when a trend cannot bear the weight put on it.
    """

    months = month_range(CYP_FIRST, CYP_LAST)
    out: dict[str, Any] = {
        "window": {"first": CYP_FIRST, "last": CYP_LAST},
        "bears_on_the_comparator_window": False,
        "why": (
            "The comparator window is 2017/18-2023/24. This one opens 2023-04, inside its "
            "final year, and runs past it. Provider participation is also nearly flat here "
            "(381 to 417 against 4.32x over the comparator window), so there is no coverage "
            "ramp for a cohort restriction to remove and the test has nothing to bite on."
        ),
        "by_family": {},
    }
    for parent, child, label in CYP_FAMILIES:
        child_cells = cyp_cells.get(child, {})
        if not all(month in child_cells for month in months):
            continue
        seen: set[str] = set()
        for month in months:
            seen.update(child_cells[month])
        continuous = sorted(
            provider
            for provider in seen
            if all(child_cells[month].get(provider) is not None for month in months)
        )
        entry: dict[str, Any] = {
            "measure": label,
            "under_18_measure": child,
            "parent_measure": parent,
            "continuous_cohort_size": len(continuous),
            "providers_present_first_month": len(child_cells[months[0]]),
            "providers_present_last_month": len(child_cells[months[-1]]),
            "months_in_window": len(months),
        }
        if not continuous:
            entry["trend"] = "NOT_COMPUTED"
            entry["reason"] = (
                "no provider published a usable under-18 value in every month of the window"
            )
            out["by_family"][parent] = entry
            continue
        cohort_series = [float(sum(child_cells[m][p] for p in continuous)) for m in months]
        unrestricted = [
            float(sum(v for v in child_cells[m].values() if v is not None)) for m in months
        ]
        cohort_fy = financial_year_means(months, cohort_series)
        unrestricted_fy = financial_year_means(months, unrestricted)
        complete = sorted(set(cohort_fy) & set(unrestricted_fy))
        if len(complete) < 2:
            entry["trend"] = "NOT_COMPUTED"
            entry["reason"] = (
                f"only {len(complete)} complete financial year(s) in the window; a ratio "
                "between fewer than two complete years is not a trend"
            )
        else:
            entry["complete_financial_years"] = complete
            entry["continuous_cohort_by_financial_year"] = cohort_fy
            entry["unrestricted_by_financial_year"] = unrestricted_fy
            entry["continuous_cohort_ratio"] = cohort_fy[complete[-1]] / cohort_fy[complete[0]]
            entry["unrestricted_ratio"] = (
                unrestricted_fy[complete[-1]] / unrestricted_fy[complete[0]]
            )
        out["by_family"][parent] = entry
    return out


def _england_age_bands(cells: dict[str, Any]) -> dict[str, Any]:
    """Per-published-band England trends. Bands are NEVER merged into an 'under 18'.

    ``England; Age`` publishes single years 16 and 17 beside "11 to 15" and "6 to 10".
    Adding them together to make an under-18 aggregate is exactly the merge this project
    forbids, so each band is reported on its own and the reader compares them.
    """

    out: dict[str, Any] = {}
    for measure in (MEASURE_OPEN_REFERRALS, MEASURE_NEW_REFERRALS):
        by_month = cells["england_age"].get(measure, {})
        if not by_month:
            continue
        months = sorted(by_month)
        bands = sorted({band for values in by_month.values() for band in values})
        per_band: dict[str, Any] = {}
        for band in bands:
            usable = [
                (m, by_month[m][band]) for m in months if by_month[m].get(band) is not None
            ]
            if len(usable) < 24:
                continue
            fy = financial_year_means([m for m, _v in usable], [float(v) for _m, v in usable])
            years = sorted(fy)
            if len(years) < 2:
                continue
            per_band[band] = {
                "complete_financial_years": years,
                "by_financial_year": fy,
                "ratio": fy[years[-1]] / fy[years[0]],
                "months_with_a_usable_value": len(usable),
                "months_missing_or_suppressed": len(months) - len(usable),
            }
        out[measure] = {
            "first_month": months[0],
            "last_month": months[-1],
            "bands": per_band,
            "note": (
                "Bands are reported separately. They are not summed into an 'under 18' "
                "aggregate; merging published age bands is forbidden here. These are also "
                "England totals with no provider dimension, so no cohort restriction is "
                "possible on them."
            ),
        }
    return out


# --------------------------------------------------------------------------------------
# Verdict
# --------------------------------------------------------------------------------------


def verdict(result: dict[str, Any]) -> dict[str, Any]:
    """The three-way call, read off the evidence by a rule fixed in advance.

    The rule, in order:

    1. If the **unconfounded** classifier is powered (at least ten providers on each side),
       it decides: joiners materially more CYP-focused -> ``STAY_WITHDRAWN``; not ->
       ``PARTLY_REINSTATE``, because the specific confounder the withdrawal box named would
       then be refuted.
    2. Otherwise the broad classifier decides, but **only if it survives the size control**.
    3. If neither is available, the answer is ``UNRESOLVED`` and the withdrawal stands by
       default - not because the confounder was shown, but because it was not excluded. A
       claim withdrawn for an unchecked reason cannot be reinstated by a check that failed
       to run.

    Step 3 is not a tie-break dressed as a principle. Reinstating a claim requires positive
    evidence that its stated defeater is absent, and "we could not tell" is not that.
    """

    share = result["classifier_share"]
    intensity = result["classifier_intensity"]

    if share.get("powered"):
        cohort_median = share.get("continuous_cohort_median_share")
        joiner_median = share.get("joiners_median_share")
        p = share.get("mann_whitney_p_two_sided", 1.0)
        cyp_heavy = (
            joiner_median is not None
            and cohort_median is not None
            and joiner_median > cohort_median
            and p < 0.05
        )
        return {
            "call": "STAY_WITHDRAWN" if cyp_heavy else "PARTLY_REINSTATE",
            "decided_by": "under-18 share (unconfounded classifier)",
            "basis": (
                f"joiner median under-18 share {joiner_median:.3f} against cohort "
                f"{cohort_median:.3f}, Mann-Whitney p={p:.4f}"
            ),
        }

    if intensity.get("test") not in (None, "NOT_RUN") and not intensity.get("size_confounded"):
        rho = intensity["spearman_rho_raw"]
        return {
            "call": "STAY_WITHDRAWN" if rho > 0 else "PARTLY_REINSTATE",
            "decided_by": "CYP intensity index (size control passed)",
            "basis": (
                f"raw rho {rho:+.3f}, partial rho controlling for size "
                f"{intensity['partial_spearman_controlling_for_log_size']:+.3f}"
            ),
        }

    reasons = []
    if intensity.get("size_confounded"):
        reasons.append(
            f"the broad classifier's association with join date "
            f"({intensity['spearman_rho_raw']:+.3f}, n={intensity['n']}, "
            f"p={intensity['permutation_p_two_sided']:.4f}) collapses to "
            f"{intensity['partial_spearman_controlling_for_log_size']:+.3f} once provider "
            "size is controlled, and the smallest size stratum contains no continuous-cohort "
            "provider at all, so there is no common support to adjust across"
        )
    reasons.append(
        f"the unconfounded classifier reaches only {share.get('joiners_n', 0)} joiner(s) "
        f"against {share.get('continuous_cohort_n', 0)} cohort providers, below the "
        f"{MIN_GROUP_FOR_A_VERDICT} needed on each side"
    )
    return {
        "call": "UNRESOLVED_WITHDRAWAL_STANDS",
        "decided_by": "neither classifier reached a testable state",
        "basis": "; ".join(reasons),
        "direction_of_the_weak_evidence": (
            f"What little unconfounded evidence exists points TOWARD the confounder: the "
            f"{share.get('joiners_n', 0)} joiners with a measurable under-18 share have a "
            f"median of {_fmt(share.get('joiners_median_share'))} against a cohort median of "
            f"{_fmt(share.get('continuous_cohort_median_share'))}. It flips on the inclusion "
            "of a single provider (see the threshold table below) and is not a result."
        ),
    }


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------


def _fmt(value: Any, spec: str = "{:.3f}") -> str:
    return "-" if value is None else spec.format(value)


_VERDICT_SENTENCES = {
    "STAY_WITHDRAWN": (
        "The withdrawn comparator claim should STAY WITHDRAWN. Later-joining providers were "
        "disproportionately children and young people's services."
    ),
    "PARTLY_REINSTATE": (
        "The withdrawn comparator claim should be PARTLY REINSTATED - the under-18 age "
        "gradient only. Later-joining providers were NOT disproportionately children and "
        "young people's services, so the confounder the withdrawal box named is refuted. "
        "The female-excess half stays withdrawn and is untestable in MHSDS."
    ),
    "UNRESOLVED_WITHDRAWAL_STANDS": (
        "The withdrawn comparator claim should STAY WITHDRAWN, but not because the "
        "confounder was demonstrated - because it cannot be excluded from this archive. "
        "The question §4 item 1 poses is not answerable from MHSDS."
    ),
}


def render(result: dict[str, Any]) -> str:
    call = result["verdict"]
    limits = result["structural_limits"]
    intensity = result["classifier_intensity"]
    share = result["classifier_share"]
    lines: list[str] = []
    add = lines.append

    add("# Were later-joining MHSDS providers disproportionately CYP services?")
    add("")
    add(
        "**Claim tier: `DESCRIPTIVE_EVIDENCE_ONLY`. Released: no.** Generated by "
        "`scripts/mhsds_cyp_cohort.py`; every figure below is in `data/mhsds_cyp_cohort.json`."
    )
    add("")
    add(
        "`docs/PROJECT_V2_SPECIFICATION.md` §4 item 1 names this question as the one that "
        '"directly determines whether adolescent-specific trends are artefactual". The '
        'warning box in `docs/REFERRAL_BASELINE.md` names it as "plausible and has not been '
        'checked". It has now been checked as far as the archive permits, which is not as '
        "far as the question needs."
    )
    add("")

    add("## The verdict")
    add("")
    add(f"**{_VERDICT_SENTENCES[call['call']]}**")
    add("")
    add(f"Decided by: {call['decided_by']}.")
    add("")
    add(f"Because {call['basis']}.")
    add("")
    if "direction_of_the_weak_evidence" in call:
        add(call["direction_of_the_weak_evidence"])
        add("")

    add("## What the archive cannot do, stated before what it can")
    add("")
    add(
        "The decisive analysis as the brief specifies it - the AS08 fixed-cohort computation "
        "restricted to the under-18 band, over the comparator window 2017/18-2023/24 - "
        "**cannot be computed from this archive.** Not underpowered: absent. This was "
        "established by enumerating every `Provider`-breakdown measure in the archive before "
        "any statistic was computed."
    )
    add("")
    add(
        f"- There is no provider-by-age breakdown anywhere "
        f"(`provider_by_age_breakdown_exists`: "
        f"{limits['provider_by_age_breakdown_exists']}). Age appears only as `England; Age`, "
        "which carries no provider dimension and so admits no cohort restriction."
    )
    add(
        f"- Every provider-level age split begins "
        f"**{limits['earliest_provider_level_age_split_month']}**. The comparator window "
        "closes 2024-03."
    )
    add(
        f"- `England; Age` itself begins **{limits['england_age_first_month']}**, so even the "
        "England-level under-18 series does not reach back into the window."
    )
    add("")
    add(
        "**Half the withdrawn claim is untestable in MHSDS at any cohort size, ever.** "
        + result["sex_within_under_18"]["reason"]
    )
    add("")

    add("## The cohort and the joiners")
    add("")
    coh = result["cohort"]
    dec = result["all_ages_decomposition"]
    add(
        f"Over {result['window']['first']} to {result['window']['last']}, "
        f"{coh['providers_ever_present']} providers appear at least once; "
        f"**{coh['continuous_cohort_size']}** publish a usable MHS01 value in every month "
        f"(AS08's cohort); **{coh['joiner_set_size']}** are present in the final month but "
        f"absent or unusable in the first. Providers present rose "
        f"{coh['providers_present_first_month']} to {coh['providers_present_last_month']}."
    )
    add("")
    add(
        f"All ages, recomputed here: the cohort rises "
        f"x{dec['continuous_cohort_ratio']:.3f} against x{dec['unrestricted_ratio']:.3f} "
        f"unrestricted, so "
        f"{dec['log_growth_share_surviving_cohort_restriction']:.1%} of the log growth "
        f"survives restriction. Joiners hold "
        f"{_fmt(dec['joiner_share_of_final_month_activity'], '{:.1%}')} of activity in "
        f"{dec['final_month']}. **This is all ages and does not answer the age-specific "
        "question**; it is here so the reader has AS08's context on the same page."
    )
    add("")
    add(
        f"Join month is the first month a provider published a **usable** MHS01 value. "
        f"{result['join_dates']['providers_with_a_join_month']} providers have one, "
        f"{result['join_dates']['earliest']} to {result['join_dates']['latest']}."
    )
    add("")

    add("## Classifier 1 - CYP intensity index (broad, and refuted as a size artefact)")
    add("")
    add(f"Definition: {intensity['definition']}.")
    add("")
    if intensity.get("test") in (None, "NOT_RUN"):
        add(f"Not run: {intensity.get('reason')}")
        add("")
    else:
        add("| Quantity | Value |")
        add("|---|---|")
        add(f"| Providers | {intensity['n']} |")
        add(f"| Distinct join months | {intensity['distinct_join_months']} |")
        add(f"| Spearman rho, join month vs index | **{intensity['spearman_rho_raw']:+.4f}** |")
        add(
            f"| Permutation p (two-sided, {PERMUTATION_DRAWS} draws) | "
            f"{intensity['permutation_p_two_sided']:.5f} |"
        )
        add(
            f"| Minimum detectable rho at 80% power | "
            f"{intensity['minimum_detectable_rho_at_80_percent_power']:.3f} |"
        )
        add(
            f"| Spearman rho, join month vs log provider size | "
            f"{intensity['spearman_rho_join_against_log_size']:+.4f} |"
        )
        add(
            f"| Spearman rho, index vs log provider size | "
            f"{intensity['spearman_rho_index_against_log_size']:+.4f} |"
        )
        add(
            f"| **Partial rho, controlling for size** | "
            f"**{intensity['partial_spearman_controlling_for_log_size']:+.4f}** |"
        )
        add("")
        add(intensity["interpretation"])
        add("")
        add(
            "The partial correlation assumes the confounding is monotone in ranks. "
            "Stratifying assumes nothing of the kind, and agrees:"
        )
        add("")
        add(
            "| Size tertile | n | Median index | rho join vs index | Cohort n | Joiners n | "
            "Cohort median | Joiners median | p |"
        )
        add("|---|---|---|---|---|---|---|---|---|")
        for tertile in intensity["by_size_tertile"]:
            add(
                f"| {tertile['tertile']} | {tertile['n']} | "
                f"{tertile['median_index']:.4f} | "
                f"{_fmt(tertile.get('spearman_rho_join_against_index'), '{:+.3f}')} | "
                f"{tertile['continuous_cohort_n']} | {tertile['joiners_n']} | "
                f"{_fmt(tertile.get('continuous_cohort_median'), '{:.4f}')} | "
                f"{_fmt(tertile.get('joiners_median'), '{:.4f}')} | "
                f"{_fmt(tertile.get('mann_whitney_p_two_sided'), '{:.4f}')} |"
            )
        add("")
        support = intensity["common_support"]
        if support.get("overlap_computable"):
            add(
                f"**Common support is the deeper problem.** Of "
                f"{support['joiners_total']} joiners carrying an index, "
                f"{support['joiners_inside_cohort_size_range']} fall inside the size range "
                f"the two groups share; of {support['cohort_total']} cohort providers, "
                f"{support['cohort_inside_joiner_size_range']} do. The smallest size tertile "
                "contains no continuous-cohort provider at all. Over most of the joiners' "
                "size range there is nothing to compare them to, and no reweighting can "
                "manufacture a comparison where the data has none."
            )
            add("")

    add("## Classifier 2 - under-18 share (unconfounded, and too sparse to decide)")
    add("")
    add(f"Definition: {share['definition']}.")
    add("")
    add(
        "Numerator and denominator are the same published measure, from the same provider, "
        "for the same month. Nothing is summed, no nesting level is crossed, and provider "
        "size cannot enter - which is exactly what Classifier 1 lacked. No provider name is "
        "read at any point."
    )
    add("")
    add("| Family | Measure | Providers with a share | Median share | Mean within-provider SD |")
    add("|---|---|---|---|---|")
    for parent, _child, _label in CYP_FAMILIES:
        entry = share["families"][parent]
        add(
            f"| {parent} | {entry['measure']} | {entry['providers_with_a_share']} | "
            f"{_fmt(entry['median_share'])} | "
            f"{_fmt(entry['mean_within_provider_share_stdev'])} |"
        )
    add("")
    add(
        f"**{share['providers_with_a_share']} providers carry a share at all: "
        f"{share['continuous_cohort_n']} from the continuous cohort and "
        f"{share['joiners_n']} joiners.** {share['why_so_few']}"
    )
    add("")
    add(
        "| Min months required | Providers | Cohort n | Joiners n | Cohort median | "
        "Joiner median | Joiner shares | p |"
    )
    add("|---|---|---|---|---|---|---|---|")
    for entry in share["sensitivity_to_the_month_threshold"]:
        add(
            f"| {entry['min_months']} | {entry['providers_with_a_share']} | "
            f"{entry['continuous_cohort_n']} | {entry['joiners_n']} | "
            f"{_fmt(entry.get('continuous_cohort_median_share'))} | "
            f"{_fmt(entry.get('joiners_median_share'))} | "
            f"{', '.join(f'{v:.3f}' for v in entry['joiner_shares'])} | "
            f"{_fmt(entry.get('mann_whitney_p_two_sided'), '{:.4f}')} |"
        )
    add("")
    add(
        "Read the last two columns together. The joiners that can be measured do look like "
        "CYP services - shares near 1.0 against a cohort median near 0.14 - and at the "
        "stricter thresholds the contrast is nominally significant. But it rests on three "
        "organisations, and admitting a fourth at the loosest threshold moves p from about "
        "0.02 to about 0.20. **A result that turns on one provider is not a result**, and "
        "NON-NEGOTIABLE 4 says to state the size and stop rather than present it as one."
    )
    add("")

    add("## The under-18 fixed cohort, on the only window where it can be run")
    add("")
    u18 = result["under_18_fixed_cohort"]
    add(f"**Window {u18['window']['first']} to {u18['window']['last']}.** {u18['why']}")
    add("")
    add(
        "| Family | Continuous under-18 cohort size | Providers present first/last | "
        "Cohort ratio | Unrestricted ratio |"
    )
    add("|---|---|---|---|---|")
    for parent, _child, _label in CYP_FAMILIES:
        entry = u18["by_family"].get(parent)
        if not entry:
            continue
        if entry.get("trend") == "NOT_COMPUTED":
            add(
                f"| {parent} | {entry['continuous_cohort_size']} | "
                f"{entry['providers_present_first_month']}/"
                f"{entry['providers_present_last_month']} | not computed | "
                f"{entry['reason']} |"
            )
            continue
        add(
            f"| {parent} | {entry['continuous_cohort_size']} | "
            f"{entry['providers_present_first_month']}/"
            f"{entry['providers_present_last_month']} | "
            f"x{entry['continuous_cohort_ratio']:.3f} | x{entry['unrestricted_ratio']:.3f} |"
        )
    add("")
    add(
        "Cohort size is stated before the trend, as required. These ratios **must not** be "
        "read as the comparator test: the window sits at and beyond the comparator's end, "
        "and provider participation is nearly flat across it, so there is no coverage ramp "
        "for the restriction to remove."
    )
    add("")

    add("## England age bands, published separately")
    add("")
    add(
        "Bands are never merged. `England; Age` publishes single years 16 and 17 beside "
        '"11 to 15"; summing them into an "under 18" is the merge this project forbids. '
        "These are England totals with no provider dimension, so no cohort restriction is "
        "possible on them - they are context, not a test."
    )
    add("")
    for measure, block in sorted(result["england_age_bands"].items()):
        add(f"### {measure} ({block['first_month']} to {block['last_month']})")
        add("")
        add("| Band | Complete FYs | Ratio | Months missing or suppressed |")
        add("|---|---|---|---|")
        for band, entry in sorted(block["bands"].items(), key=lambda item: -item[1]["ratio"]):
            add(
                f"| {band} | {entry['complete_financial_years'][0]}-"
                f"{entry['complete_financial_years'][-1]} | x{entry['ratio']:.3f} | "
                f"{entry['months_missing_or_suppressed']} |"
            )
        add("")

    add("## What `docs/REFERRAL_BASELINE.md` needs")
    add("")
    add("That file is not edited by this script. What its warning box needs, on this evidence:")
    add("")
    for item in _baseline_actions(result):
        add(f"- {item}")
    add("")

    add("## Limits")
    add("")
    for item in _limits(result):
        add(f"- {item}")
    add("")
    add(
        "**Compatibility is not support.** No mechanism was calibrated here, so "
        "`compare_mechanisms` was not invoked and nothing inherits its refutation asymmetry "
        "in either direction. What this file does is refute one candidate *classifier* and "
        "report that the question itself is out of reach of this archive."
    )
    add("")
    return "\n".join(lines)


def _baseline_actions(result: dict[str, Any]) -> list[str]:
    call = result["verdict"]["call"]
    items: list[str] = []
    if call == "UNRESOLVED_WITHDRAWAL_STANDS":
        items += [
            'The sentence "If the providers joining later were disproportionately children '
            'and young people\'s services - which is plausible and has not been checked" '
            "should be updated to record that it HAS now been checked against MHSDS and "
            "that MHSDS cannot answer it, citing this file. The withdrawal stands, but its "
            "status changes from \"unchecked\" to \"unanswerable from this source\".",
            "The box's promised remedy - \"restrict to providers submitting continuously "
            "across the whole window\" - should be corrected. That restriction was run "
            "(AS08) and works for ALL AGES only. It cannot be run for the under-18 band, "
            "because MHSDS publishes no provider-level age split before 2023-04 and no "
            "provider-by-age breakdown at all.",
            "The sex-ratio section must stay withdrawn and should be marked **untestable in "
            "MHSDS**, not merely unchecked. There is no age-by-sex cross-tab at any level, "
            "so no future provider-cohort work on this archive will change it.",
            "The box should record that the one candidate classifier that WAS broad enough "
            "to test - CYP closed referrals over all-ages activity - showed a large apparent "
            "effect that vanished on adjustment for provider size. A successor tempted by "
            "the same index should find that already tried and refuted here.",
        ]
    elif call == "STAY_WITHDRAWN":
        items += [
            "The withdrawal is confirmed on its own stated ground; the box should record the "
            "measured magnitude rather than leaving it as a conjecture."
        ]
    else:
        items += [
            "The age-gradient section should have its blanket withdrawal narrowed: the "
            "coverage ramp is real and the levels remain upper bounds, but the named "
            "mechanism for why the ramp would hit the under-18 band specifically is refuted.",
            "The sex-ratio section must stay withdrawn; it is untestable in MHSDS.",
        ]
    items.append(
        "Whatever is written there, Fingertips indicator 93623 is a different collection "
        "from MHSDS with its own compilation. This analysis constrains a proposed mechanism, "
        "not that indicator's numbers directly."
    )
    items.append(
        "What would actually settle it: a provider-by-age extract of MHSDS covering "
        "2017/18-2023/24, which is not in the published time series and would need a data "
        "request - the same route as the FOI already drafted under `studies/foi_requests/`."
    )
    return items


def _limits(result: dict[str, Any]) -> list[str]:
    share = result["classifier_share"]
    spreads = [
        entry["mean_within_provider_share_stdev"]
        for entry in share["families"].values()
        if entry["mean_within_provider_share_stdev"] is not None
    ]
    return [
        "**Both classifiers are measured from 2023-04 and applied to joins dated from 2016.** "
        "A provider's case mix is assumed stable enough to carry backwards. The measured "
        "within-provider month-to-month spread of the share averages "
        f"{statistics.mean(spreads):.3f} across families - evidence over 39 months, not over "
        "nine years. A provider that converted from adult to CYP work after joining is "
        "misclassified.",
        "**The unconfounded share is measured on crisis-care and A&E-liaison referral "
        "routes**, the only provider-level age splits published. They are not the general "
        "referral flow the comparator measured, and a provider could be CYP-heavy in routine "
        "referrals without being so in crisis referrals.",
        "**Providers that merged, split or changed organisation code leave the continuous "
        "cohort by construction**, so the cohort is not a random sample. AS08's limit, "
        "inherited unchanged.",
        "**MHS01 is a stock, not the referral flow** the comparator measured. MHS32 at "
        "provider level begins 2022-04 and cannot cover the window.",
        "**Counts, not rates.** No population denominator is applied here; that is AS11's job.",
        "**The joiner set is defined by presence in the window's last month and absence in "
        "its first.** A provider that joined mid-window and left before 2024-03 is in "
        "neither group, so the two groups do not exhaust the archive.",
    ]


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MHSDS CYP joiner analysis")
    parser.add_argument("--force", action="store_true", help="re-read the MHSDS archive")
    parser.add_argument("--archive", type=Path, default=None)
    args = parser.parse_args(argv)

    cells = extract(force=args.force, archive=args.archive)
    result = analyse(cells)

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    DOC_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOC_OUT.write_text(render(result), encoding="utf-8")

    print(f"verdict: {result['verdict']['call']}")
    print(f"  decided by: {result['verdict']['decided_by']}")
    print(f"  {result['verdict']['basis']}")
    print(f"wrote {JSON_OUT.relative_to(REPO_ROOT)} and {DOC_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
