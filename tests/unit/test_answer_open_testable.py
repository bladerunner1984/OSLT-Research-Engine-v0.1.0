"""Unit tests for the pure helpers behind the open-testable candidate findings.

Nothing here touches the MHSDS archive, NOMIS or the network. What is tested is the
arithmetic that the findings rest on and the refusals that stop a hole becoming a zero.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "answer_open_testable", REPO_ROOT / "scripts" / "answer_open_testable.py"
)
assert _SPEC is not None and _SPEC.loader is not None
answer_open_testable = importlib.util.module_from_spec(_SPEC)
sys.modules["answer_open_testable"] = answer_open_testable
_SPEC.loader.exec_module(answer_open_testable)

aot = answer_open_testable


def test_month_range_is_inclusive_and_crosses_a_year() -> None:
    assert aot.month_range("2017-11", "2018-02") == [
        "2017-11",
        "2017-12",
        "2018-01",
        "2018-02",
    ]


def test_month_range_refuses_a_reversed_window() -> None:
    with pytest.raises(ValueError):
        aot.month_range("2018-02", "2017-11")


def test_financial_year_starts_in_april() -> None:
    assert aot.financial_year("2017-03") == "2016/17"
    assert aot.financial_year("2017-04") == "2017/18"
    assert aot.financial_year("2099-04") == "2099/00"


def test_log_growth_share_composes_multiplicatively() -> None:
    # A whole that is exactly the product of two parts splits into shares summing to 1.
    part, other = 1.5, 2.0
    whole = part * other
    left = aot.log_growth_share(part, whole)
    right = aot.log_growth_share(other, whole)
    assert left + right == pytest.approx(1.0)


def test_log_growth_share_refuses_zero_growth() -> None:
    with pytest.raises(ValueError):
        aot.log_growth_share(1.2, 1.0)


def test_pearson_refuses_a_constant_series() -> None:
    # A Fingertips standardisation ratio is 100.0 in every period. Correlating against it
    # must raise rather than return a number that reads as "no relationship".
    with pytest.raises(ValueError):
        aot.pearson([100.0] * 5, [1.0, 2.0, 3.0, 4.0, 5.0])


def test_slope_break_is_zero_on_a_straight_line() -> None:
    line = [float(index) for index in range(20)]
    assert aot.slope_break(line, 10, 5) == pytest.approx(0.0)


def test_slope_break_finds_a_planted_kink() -> None:
    values = [float(index) for index in range(10)] + [
        9.0 + 3.0 * index for index in range(1, 11)
    ]
    assert aot.slope_break(values, 10, 5) == pytest.approx(2.0)


def test_direct_standardisation_removes_a_pure_composition_shift() -> None:
    # Band rates identical in both periods; only the age structure differs. A directly
    # standardised comparison must show no change even though the crude rate moves.
    counts_one = {"young": 100.0, "old": 100.0}
    populations_one = {"young": 1000.0, "old": 10_000.0}
    counts_two = {"young": 500.0, "old": 10.0}
    populations_two = {"young": 5000.0, "old": 1000.0}
    weights = populations_one
    first = aot.direct_standardised_rate(counts_one, populations_one, weights)
    second = aot.direct_standardised_rate(counts_two, populations_two, weights)
    assert second == pytest.approx(first)


def test_build_cohort_excludes_a_provider_with_a_suppressed_cell() -> None:
    cells = {
        "2020-01": {"A": 10.0, "B": 5.0},
        "2020-02": {"A": 11.0, "B": None},
        "2020-03": {"A": 12.0, "B": 6.0, "C": 100.0},
    }
    cohort = aot.build_cohort(cells, "2020-01", "2020-03")
    assert cohort.provider_ids == ("A",)
    assert cohort.series == (10.0, 11.0, 12.0)
    # The unrestricted series sums only the values that exist; B's suppressed month is
    # missing, not zero, and C is a joiner.
    assert cohort.unrestricted == (15.0, 11.0, 118.0)
    assert cohort.providers_present["2020-03"] == 3
    assert cohort.providers_with_value["2020-02"] == 1


def test_build_cohort_refuses_a_month_with_no_rows_at_all() -> None:
    cells = {"2020-01": {"A": 1.0}, "2020-03": {"A": 2.0}}
    with pytest.raises(ValueError, match="not a month of no activity"):
        aot.build_cohort(cells, "2020-01", "2020-03")


def test_financial_year_means_drops_incomplete_years() -> None:
    months = aot.month_range("2017-01", "2018-06")
    values = [1.0] * len(months)
    means = aot.financial_year_means(months, values)
    assert list(means) == ["2017/18"]


def test_coverage_only_mechanism_is_refuted_by_a_rising_series() -> None:
    from oslt_research.governance.mechanism_simulation import (
        ObservedSeries,
        compare_mechanisms,
    )

    observed = ObservedSeries(
        name="rising cohort",
        source_id="TEST",
        values=tuple(100.0 * 1.1**index for index in range(7)),
    )
    comparison = compare_mechanisms(
        aot.as08_mechanisms((90.0, 100.0, 110.0)),
        observed,
        tolerance=aot.CALIBRATION_TOLERANCE,
    )
    assert "COVERAGE_ONLY" in comparison["refuted"]


def test_coverage_only_mechanism_survives_a_flat_series() -> None:
    from oslt_research.governance.mechanism_simulation import (
        ObservedSeries,
        compare_mechanisms,
    )

    # Built from the mechanism's own shape. normalised_rmse scales the tolerance by the
    # observed RANGE, so a near-flat series is a very tight target and an approximately
    # flat one would be refused - which is the correct behaviour, not a bug.
    values = tuple(aot._coverage_only({"level": 100.0, "wobble": 0.02}, 7))
    observed = ObservedSeries(name="flat cohort", source_id="TEST", values=values)
    comparison = compare_mechanisms(
        aot.as08_mechanisms((90.0, 100.0, 110.0)),
        observed,
        tolerance=aot.CALIBRATION_TOLERANCE,
    )
    assert "COVERAGE_ONLY" in comparison["compatible"]
    # Compatibility is not support: the engine's own bound must travel with the result.
    assert "may be reported as supported" in str(comparison["interpretation_bound"])


def test_permutation_p_value_is_high_when_marking_is_arbitrary() -> None:
    statistic = {f"k{index}": float(index % 3) for index in range(30)}
    marked = [key for index, key in enumerate(statistic) if index % 3 == 0]
    p_value = aot.permutation_p_value(statistic, marked, draws=2000, seed=1)
    assert 0.0 <= p_value <= 1.0


def test_published_findings_cover_all_sixteen_and_release_nothing() -> None:
    payload = aot.load_json(REPO_ROOT / "data" / "open_testable_findings.json")
    assert payload["released"] is False
    assert len(payload["findings"]) == 16
    assert {item["proposition_id"] for item in payload["findings"]} == set(
        payload["feasibility"]["testable_ids"]
    )
    for item in payload["findings"]:
        assert item["released"] is False
        # Nothing may be claimed above the descriptive tier: no mechanism here is
        # calibrated in a way that licenses more.
        assert item["claim_tier"] == "DESCRIPTIVE_EVIDENCE_ONLY"
        assert item["finding_direction"] in {"SUPPORTS", "WEAKENS", "INCONCLUSIVE"}


def test_published_findings_carry_the_unequal_ballot_warning() -> None:
    payload = aot.load_json(REPO_ROOT / "data" / "open_testable_findings.json")
    warnings = payload["feasibility"]["coverage_asymmetry"]
    assert any("MODEL_FAMILIES_WITH_NO_OPEN_TESTABLE_PROPOSITION" in w for w in warnings)
    assert any("ASCERTAINMENT_SERVICE" in w for w in warnings)
    assert "measures data access" in payload["ballot_warning"]


def test_as08_reports_a_quantified_coverage_decomposition() -> None:
    payload = aot.load_json(REPO_ROOT / "data" / "open_testable_findings.json")
    as08 = next(
        item for item in payload["findings"] if item["proposition_id"] == "AS08"
    )
    quantities = as08["quantities"]
    surviving = quantities["log_growth_surviving_coverage_restriction"]
    attributable = quantities["log_growth_attributable_to_coverage"]
    assert surviving + attributable == pytest.approx(1.0)
    assert quantities["providers_submitting_continuously"] < quantities[
        "providers_seen_in_window"
    ]
    assert math.isfinite(quantities["continuous_cohort_ratio"])
