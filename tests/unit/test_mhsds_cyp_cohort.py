"""Unit tests for the MHSDS CYP-joiner analysis.

Nothing here touches the 660MB archive or the network. What is tested is the arithmetic the
conclusion rests on and, more importantly, the refusals: a suppressed cell must not become a
zero, a size confound must be detected rather than reported as a finding, and an
underpowered contrast must not be dressed up as an answer.

The verdict logic gets its own tests because it is the part a successor is most likely to
trust without reading. It must return ``PARTLY_REINSTATE`` on planted evidence that the
confounder is absent, ``STAY_WITHDRAWN`` on planted evidence that it is present, and
``UNRESOLVED_WITHDRAWAL_STANDS`` when neither classifier can see - and it must not be
possible to reach a reinstatement through an underpowered contrast.
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "mhsds_cyp_cohort", REPO_ROOT / "scripts" / "mhsds_cyp_cohort.py"
)
assert _SPEC is not None and _SPEC.loader is not None
mhsds_cyp_cohort = importlib.util.module_from_spec(_SPEC)
sys.modules["mhsds_cyp_cohort"] = mhsds_cyp_cohort
_SPEC.loader.exec_module(mhsds_cyp_cohort)

cyp = mhsds_cyp_cohort


# --------------------------------------------------------------------------------------
# Periods
# --------------------------------------------------------------------------------------


def test_month_range_is_inclusive_and_crosses_a_year() -> None:
    assert cyp.month_range("2023-11", "2024-02") == [
        "2023-11",
        "2023-12",
        "2024-01",
        "2024-02",
    ]


def test_month_range_refuses_a_reversed_window() -> None:
    with pytest.raises(ValueError):
        cyp.month_range("2024-02", "2023-11")


def test_month_ordinal_and_label_round_trip() -> None:
    for label in ("2016-01", "2016-12", "2024-03", "2026-06"):
        assert cyp.month_label(cyp.month_ordinal(label)) == label


def test_financial_year_starts_in_april_and_is_not_a_calendar_year() -> None:
    assert cyp.financial_year("2017-03") == "2016/17"
    assert cyp.financial_year("2017-04") == "2017/18"
    assert cyp.financial_year("2023-12") == "2023/24"


# --------------------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------------------


def test_rank_shares_ties() -> None:
    assert cyp.rank([10.0, 20.0, 20.0, 30.0]) == [1.0, 2.5, 2.5, 4.0]


def test_spearman_is_one_on_a_monotone_nonlinear_relation() -> None:
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert cyp.spearman(xs, [x**3 for x in xs]) == pytest.approx(1.0)


def test_pearson_refuses_a_constant_series() -> None:
    with pytest.raises(ValueError):
        cyp.pearson([1.0, 2.0, 3.0], [5.0, 5.0, 5.0])


def test_partial_spearman_refuses_a_control_that_is_a_variable() -> None:
    """A perfect rank duplicate leaves nothing to partial; refusing beats returning 0/0."""

    control = [float(index) for index in range(30)]
    with pytest.raises(ValueError, match="perfectly rank-correlated"):
        cyp.partial_spearman(control, [-v for v in control], control)


def test_partial_spearman_removes_a_planted_common_cause() -> None:
    """A and B are both driven by C and unrelated otherwise; the partial must vanish.

    This is precisely the CYP-index situation: join date and the index are both driven by
    provider size. If this function did not strip it, the analysis would report a size
    gradient as a case-mix finding.
    """

    rng = random.Random(11)
    control = [float(index) for index in range(120)]
    # Both variables track the control closely but not perfectly, with INDEPENDENT noise, so
    # the raw correlation between them is high while none of it survives conditioning.
    left = [value + rng.gauss(0.0, 8.0) for value in control]
    right = [-value + rng.gauss(0.0, 8.0) for value in control]
    assert abs(cyp.spearman(left, right)) > 0.8
    assert abs(cyp.partial_spearman(left, right, control)) < 0.3


def test_partial_spearman_keeps_a_genuine_association() -> None:
    control = [float(index % 3) for index in range(30)]
    left = [float(index) for index in range(30)]
    right = [float(index) for index in range(30)]
    assert cyp.partial_spearman(left, right, control) > 0.9


def test_minimum_detectable_rho_falls_as_the_sample_grows() -> None:
    assert cyp.minimum_detectable_rho(30) > cyp.minimum_detectable_rho(200)
    assert 0.0 < cyp.minimum_detectable_rho(189) < 1.0


def test_minimum_detectable_rho_refuses_a_tiny_sample() -> None:
    with pytest.raises(ValueError):
        cyp.minimum_detectable_rho(5)


def test_permutation_p_is_high_when_the_pairing_is_arbitrary() -> None:
    left = [float(index) for index in range(20)]
    right = [1.0, 5.0, 3.0, 2.0, 4.0] * 4
    assert cyp.permutation_p_two_sided(left, right, draws=500) > 0.2


def test_mann_whitney_separates_two_disjoint_groups() -> None:
    _u, p = cyp.mann_whitney_u([5.0] * 12, [1.0] * 12)
    assert p < 0.01


def test_mann_whitney_refuses_an_empty_group() -> None:
    with pytest.raises(ValueError):
        cyp.mann_whitney_u([], [1.0])


def test_log_growth_share_composes_multiplicatively() -> None:
    assert cyp.log_growth_share(2.0, 4.0) == pytest.approx(0.5)


def test_log_growth_share_refuses_a_flat_whole() -> None:
    with pytest.raises(ValueError):
        cyp.log_growth_share(1.2, 1.0)


# --------------------------------------------------------------------------------------
# Join dates - a suppressed cell is not a join
# --------------------------------------------------------------------------------------


def test_first_reporting_month_ignores_a_suppressed_first_appearance() -> None:
    cells: dict[str, dict[str, float | None]] = {
        "2017-04": {"A": None},
        "2017-05": {"A": 10.0},
    }
    assert cyp.first_reporting_month(cells) == {"A": "2017-05"}


def test_first_reporting_month_takes_the_earliest_usable_month() -> None:
    cells: dict[str, dict[str, float | None]] = {
        "2017-06": {"A": 5.0},
        "2017-04": {"A": 7.0},
        "2017-05": {"A": 6.0},
    }
    assert cyp.first_reporting_month(cells)["A"] == "2017-04"


# --------------------------------------------------------------------------------------
# Cohorts - the AS08 rule, inherited
# --------------------------------------------------------------------------------------


def _three_month_cells() -> dict[str, dict[str, float | None]]:
    return {
        "2017-04": {"CONT": 100.0, "SUPP": None},
        "2017-05": {"CONT": 110.0, "SUPP": 5.0, "LATE": 20.0},
        "2017-06": {"CONT": 120.0, "SUPP": 6.0, "LATE": 30.0},
    }


def test_build_cohort_excludes_a_provider_with_a_suppressed_cell() -> None:
    cohort = cyp.build_cohort(_three_month_cells(), "2017-04", "2017-06")
    assert cohort.continuous == ("CONT",)


def test_build_cohort_series_never_reads_a_hole_as_zero() -> None:
    """The cohort series must be the cohort's own activity, not a total with a dip in it."""

    cohort = cyp.build_cohort(_three_month_cells(), "2017-04", "2017-06")
    assert cohort.series == (100.0, 110.0, 120.0)
    # The unrestricted series sums only what was published, and 2017-04 has one provider.
    assert cohort.unrestricted == (100.0, 135.0, 156.0)


def test_build_cohort_identifies_joiners_as_present_at_the_end_not_the_start() -> None:
    cohort = cyp.build_cohort(_three_month_cells(), "2017-04", "2017-06")
    assert set(cohort.joiners) == {"SUPP", "LATE"}


def test_build_cohort_refuses_a_month_with_no_rows_at_all() -> None:
    cells = {"2017-04": {"A": 1.0}, "2017-06": {"A": 2.0}}
    with pytest.raises(ValueError, match="no provider rows"):
        cyp.build_cohort(cells, "2017-04", "2017-06")


def test_build_cohort_refuses_when_nobody_reported_throughout() -> None:
    cells: dict[str, dict[str, float | None]] = {
        "2017-04": {"A": 1.0},
        "2017-05": {"B": 2.0},
    }
    with pytest.raises(ValueError, match="every month"):
        cyp.build_cohort(cells, "2017-04", "2017-05")


def test_financial_year_means_drops_incomplete_years() -> None:
    months = cyp.month_range("2023-01", "2024-06")
    values = [1.0] * len(months)
    means = cyp.financial_year_means(months, values)
    assert set(means) == {"2023/24"}


# --------------------------------------------------------------------------------------
# The under-18 share - the unconfounded classifier
# --------------------------------------------------------------------------------------


def _share_cells(months: list[str]) -> dict[str, dict[str, dict[str, float | None]]]:
    return {
        "CCR70": {m: {"ADULT": 100.0, "CAMHS": 40.0} for m in months},
        "CCR70b": {m: {"ADULT": 5.0, "CAMHS": 40.0} for m in months},
    }


def test_family_share_is_the_child_over_its_own_parent() -> None:
    months = cyp.month_range("2023-04", "2024-03")
    shares = cyp.family_shares(_share_cells(months), "CCR70", "CCR70b", months)
    assert shares["ADULT"].share == pytest.approx(0.05)
    assert shares["CAMHS"].share == pytest.approx(1.0)


def test_family_share_drops_a_suppressed_child_rather_than_scoring_it_zero() -> None:
    """The whole classification turns on this. A suppressed under-18 cell is not a zero.

    If it were read as zero, a provider with a published parent and eleven suppressed
    under-18 months would be scored as an adult-only service on evidence that is absent.
    """

    months = cyp.month_range("2023-04", "2024-03")
    cells = _share_cells(months)
    cells["CCR70b"][months[0]]["CAMHS"] = None
    shares = cyp.family_shares(cells, "CCR70", "CCR70b", months, min_months=6)
    assert shares["CAMHS"].months_used == len(months) - 1
    assert shares["CAMHS"].share == pytest.approx(1.0)


def test_family_share_drops_a_month_whose_parent_is_missing() -> None:
    months = cyp.month_range("2023-04", "2024-03")
    cells = _share_cells(months)
    cells["CCR70"][months[0]]["ADULT"] = None
    shares = cyp.family_shares(cells, "CCR70", "CCR70b", months, min_months=6)
    assert shares["ADULT"].months_used == len(months) - 1


def test_family_share_drops_a_zero_parent_rather_than_dividing_by_it() -> None:
    months = cyp.month_range("2023-04", "2024-03")
    cells = _share_cells(months)
    cells["CCR70"][months[0]]["ADULT"] = 0.0
    cells["CCR70b"][months[0]]["ADULT"] = 0.0
    shares = cyp.family_shares(cells, "CCR70", "CCR70b", months, min_months=6)
    assert shares["ADULT"].months_used == len(months) - 1


def test_family_share_requires_enough_months() -> None:
    months = cyp.month_range("2023-04", "2023-08")
    shares = cyp.family_shares(_share_cells(months), "CCR70", "CCR70b", months)
    assert shares == {}


def test_family_share_refuses_a_child_larger_than_its_parent() -> None:
    """A part bigger than its whole means these measures are not what the code assumes."""

    months = cyp.month_range("2023-04", "2024-03")
    cells = _share_cells(months)
    cells["CCR70b"][months[0]]["ADULT"] = 500.0
    with pytest.raises(ValueError, match="part/whole"):
        cyp.family_shares(cells, "CCR70", "CCR70b", months, min_months=6)


def test_share_stdev_detects_an_unstable_provider() -> None:
    stable = cyp.FamilyShare("P", "C", 3, 3.0, 10.0, 0.3, (0.3, 0.3, 0.3))
    unstable = cyp.FamilyShare("P", "C", 3, 3.0, 10.0, 0.3, (0.05, 0.3, 0.8))
    assert stable.share_stdev == pytest.approx(0.0)
    assert unstable.share_stdev is not None and unstable.share_stdev > 0.3


# --------------------------------------------------------------------------------------
# The CYP intensity index - months are paired, never borrowed
# --------------------------------------------------------------------------------------


def test_cyp_intensity_drops_months_where_either_side_is_unusable() -> None:
    months = cyp.month_range("2023-04", "2024-05")
    cyp_cells = {cyp.MEASURE_CYP_CLOSED_REFERRALS: {m: {"A": 10.0} for m in months}}
    provider_cells: dict[str, dict[str, float | None]] = {m: {"A": 100.0} for m in months}
    provider_cells[months[0]]["A"] = None
    index = cyp.cyp_intensity(cyp_cells, provider_cells, months)
    # The dropped month must leave BOTH sides, or the ratio is taken over mismatched spans.
    assert index["A"].months_used == len(months) - 1
    assert index["A"].index == pytest.approx(0.1)


def test_cyp_intensity_requires_enough_paired_months() -> None:
    months = cyp.month_range("2023-04", "2023-08")
    cyp_cells = {cyp.MEASURE_CYP_CLOSED_REFERRALS: {m: {"A": 10.0} for m in months}}
    provider_cells: dict[str, dict[str, float | None]] = {m: {"A": 100.0} for m in months}
    assert cyp.cyp_intensity(cyp_cells, provider_cells, months) == {}


# --------------------------------------------------------------------------------------
# The verdict rule
# --------------------------------------------------------------------------------------


def _result(share: dict[str, Any], intensity: dict[str, Any]) -> dict[str, Any]:
    return {"classifier_share": share, "classifier_intensity": intensity}


def test_verdict_reinstates_when_a_powered_share_shows_no_cyp_excess() -> None:
    call = cyp.verdict(
        _result(
            {
                "powered": True,
                "continuous_cohort_median_share": 0.14,
                "joiners_median_share": 0.13,
                "mann_whitney_p_two_sided": 0.8,
            },
            {"test": "NOT_RUN"},
        )
    )
    assert call["call"] == "PARTLY_REINSTATE"


def test_verdict_stays_withdrawn_when_a_powered_share_shows_a_cyp_excess() -> None:
    call = cyp.verdict(
        _result(
            {
                "powered": True,
                "continuous_cohort_median_share": 0.14,
                "joiners_median_share": 0.90,
                "mann_whitney_p_two_sided": 0.001,
            },
            {"test": "NOT_RUN"},
        )
    )
    assert call["call"] == "STAY_WITHDRAWN"


def test_verdict_refuses_to_be_decided_by_a_size_confounded_classifier() -> None:
    """The trap this whole analysis exists to avoid.

    A large, highly significant raw correlation that vanishes on adjustment must NOT be
    allowed to decide the question in either direction.
    """

    call = cyp.verdict(
        _result(
            {"powered": False, "joiners_n": 3, "continuous_cohort_n": 53},
            {
                "test": "ran",
                "n": 189,
                "size_confounded": True,
                "spearman_rho_raw": 0.589,
                "permutation_p_two_sided": 0.00005,
                "partial_spearman_controlling_for_log_size": 0.039,
            },
        )
    )
    assert call["call"] == "UNRESOLVED_WITHDRAWAL_STANDS"


def test_verdict_may_be_decided_by_an_unconfounded_broad_classifier() -> None:
    call = cyp.verdict(
        _result(
            {"powered": False, "joiners_n": 3, "continuous_cohort_n": 53},
            {
                "test": "ran",
                "n": 189,
                "size_confounded": False,
                "spearman_rho_raw": 0.45,
                "partial_spearman_controlling_for_log_size": 0.42,
            },
        )
    )
    assert call["call"] == "STAY_WITHDRAWN"


def test_an_underpowered_share_can_never_reach_a_reinstatement() -> None:
    """An underpowered contrast must fall through to UNRESOLVED, not to a reinstatement.

    Reinstating a withdrawn claim requires positive evidence that its stated defeater is
    absent. "We could not tell" is not that, and this test pins the asymmetry.
    """

    call = cyp.verdict(
        _result(
            {
                "powered": False,
                "joiners_n": 3,
                "continuous_cohort_n": 53,
                "joiners_median_share": 0.999,
                "continuous_cohort_median_share": 0.136,
            },
            {"test": "NOT_RUN"},
        )
    )
    assert call["call"] == "UNRESOLVED_WITHDRAWAL_STANDS"
    assert "3 joiner" in call["basis"]


def test_every_verdict_call_has_a_rendered_sentence() -> None:
    """A verdict the doc cannot render would produce a KeyError at write time."""

    for call in ("STAY_WITHDRAWN", "PARTLY_REINSTATE", "UNRESOLVED_WITHDRAWAL_STANDS"):
        assert call in cyp._VERDICT_SENTENCES


# --------------------------------------------------------------------------------------
# The published artefacts
# --------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def published() -> dict[str, Any]:
    path = REPO_ROOT / "data" / "mhsds_cyp_cohort.json"
    if not path.exists():
        pytest.skip("run scripts/mhsds_cyp_cohort.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def test_published_result_releases_nothing_and_caps_the_tier(
    published: dict[str, Any],
) -> None:
    assert published["released"] is False
    assert published["claim_tier"] == "DESCRIPTIVE_EVIDENCE_ONLY"


def test_published_result_records_that_the_under_18_cohort_is_impossible(
    published: dict[str, Any],
) -> None:
    limits = published["structural_limits"]
    assert limits["provider_by_age_breakdown_exists"] is False
    assert limits["under_18_cohort_over_comparator_window_possible"] is False
    assert limits["earliest_provider_level_age_split_month"] > published["window"]["first"]


def test_published_result_records_the_sex_split_as_untestable(
    published: dict[str, Any],
) -> None:
    assert published["sex_within_under_18"]["testable"] is False


def test_published_result_reproduces_the_as08_all_ages_decomposition(
    published: dict[str, Any],
) -> None:
    """If this drifts, either AS08 or this file is reading a different archive."""

    assert published["cohort"]["continuous_cohort_size"] == 71
    decomposition = published["all_ages_decomposition"]
    assert decomposition["continuous_cohort_ratio"] == pytest.approx(1.411, abs=0.005)
    assert decomposition["unrestricted_ratio"] == pytest.approx(1.517, abs=0.005)
    assert decomposition["log_growth_share_surviving_cohort_restriction"] == pytest.approx(
        0.826, abs=0.005
    )


def test_published_result_detected_the_size_confound(published: dict[str, Any]) -> None:
    intensity = published["classifier_intensity"]
    assert intensity["size_confounded"] is True
    assert abs(intensity["spearman_rho_raw"]) > 0.4
    assert abs(intensity["partial_spearman_controlling_for_log_size"]) < 0.2


def test_published_result_reports_cohort_sizes_before_any_under_18_trend(
    published: dict[str, Any],
) -> None:
    for entry in published["under_18_fixed_cohort"]["by_family"].values():
        assert "continuous_cohort_size" in entry
    assert published["under_18_fixed_cohort"]["bears_on_the_comparator_window"] is False


def test_published_doc_states_the_verdict_and_names_the_baseline_file() -> None:
    path = REPO_ROOT / "docs" / "MHSDS_CYP_ANALYSIS.md"
    if not path.exists():
        pytest.skip("run scripts/mhsds_cyp_cohort.py first")
    text = path.read_text(encoding="utf-8")
    assert "DESCRIPTIVE_EVIDENCE_ONLY" in text
    assert "REFERRAL_BASELINE.md" in text
    assert any(
        sentence[:40] in text for sentence in cyp._VERDICT_SENTENCES.values()
    ), "the doc must carry one of the three verdict sentences verbatim"



def test_published_age_bands_are_never_merged(published: dict[str, Any]) -> None:
    """Single years 16 and 17 must survive as their own bands, with no 'under 18' total."""

    for block in published["england_age_bands"].values():
        bands = set(block["bands"])
        assert {"16", "17"} <= bands
        assert not any("under" in band.lower() for band in bands)
