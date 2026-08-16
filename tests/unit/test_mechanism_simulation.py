from __future__ import annotations

import pytest

from oslt_research.domain.enums import ClaimTier, EpistemicStatus, FindingDirection
from oslt_research.governance.mechanism_simulation import (
    MechanismCandidate,
    ObservedSeries,
    calibrate_mechanism,
    Corroboration,
    SeverityBand,
    assess_severity,
    compare_mechanisms,
    normalised_rmse,
)


OBSERVED = ObservedSeries(
    name="test series",
    source_id="DS_TEST",
    values=(10.0, 20.0, 30.0, 40.0),
    periods=("a", "b", "c", "d"),
)


def linear(params: dict[str, float], n: int) -> list[float]:
    return [params["intercept"] + params["slope"] * i for i in range(n)]


def flat(params: dict[str, float], n: int) -> list[float]:
    return [params["level"]] * n


LINEAR = MechanismCandidate(
    "LINEAR", "linear", linear,
    {"intercept": (10.0,), "slope": (5.0, 10.0, 15.0)},
)
FLAT = MechanismCandidate("FLAT", "no change", flat, {"level": (1.0, 2.0)})


# ------------------------------------------------------------------ primitives


def test_observed_series_needs_enough_points_to_constrain():
    with pytest.raises(ValueError, match="at least three"):
        ObservedSeries(name="x", source_id="s", values=(1.0, 2.0))


def test_observed_series_rejects_mismatched_periods():
    with pytest.raises(ValueError, match="same length"):
        ObservedSeries(name="x", source_id="s", values=(1.0, 2.0, 3.0), periods=("a",))


def test_normalised_rmse_is_zero_for_an_exact_match():
    assert normalised_rmse([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0


def test_normalised_rmse_rejects_length_mismatch():
    with pytest.raises(ValueError):
        normalised_rmse([1.0], [1.0, 2.0])


def test_grid_expands_to_the_cartesian_product():
    assert len(LINEAR.grid_points()) == 3
    assert len(FLAT.grid_points()) == 2


# ----------------------------------------------------------------- calibration


def test_a_mechanism_that_reproduces_the_series_is_compatible():
    result = calibrate_mechanism(LINEAR, OBSERVED, tolerance=0.1)
    assert not result.refuted
    assert result.accepted >= 1
    assert result.best_distance == pytest.approx(0.0, abs=1e-9)


def test_a_mechanism_that_cannot_reproduce_the_series_is_refuted():
    result = calibrate_mechanism(FLAT, OBSERVED, tolerance=0.1)
    assert result.refuted
    assert result.accepted == 0
    assert result.finding_direction is FindingDirection.WEAKENS
    assert "disfavoured" in result.narrative


def test_compatibility_is_never_reported_as_support():
    """Reproducing one aggregate series is cheap; many mechanisms manage it."""

    result = calibrate_mechanism(LINEAR, OBSERVED, tolerance=0.1)
    assert result.finding_direction is FindingDirection.INCONCLUSIVE
    assert "not support" in result.narrative
    assert result.finding_direction is not FindingDirection.SUPPORTS


def test_every_result_is_pinned_to_simulation_only():
    result = calibrate_mechanism(LINEAR, OBSERVED)
    assert result.epistemic_status is EpistemicStatus.SIMULATION
    assert result.claim_tier is ClaimTier.SIMULATION_ONLY
    assert "compatibility, not confirmation" in result.disclosure


def test_widening_tolerance_can_rescue_a_refuted_mechanism():
    """Which is exactly why tolerance belongs in the frozen specification."""

    assert calibrate_mechanism(FLAT, OBSERVED, tolerance=0.1).refuted
    assert not calibrate_mechanism(FLAT, OBSERVED, tolerance=0.99).refuted


def test_tolerance_must_be_a_fraction():
    for bad in (0.0, 1.0, 5.0):
        with pytest.raises(ValueError):
            calibrate_mechanism(LINEAR, OBSERVED, tolerance=bad)


def test_empty_grid_is_rejected():
    empty = MechanismCandidate("EMPTY", "none", flat, {"level": ()})
    with pytest.raises(ValueError, match="empty parameter grid"):
        calibrate_mechanism(empty, OBSERVED)


# ------------------------------------------------------------------ comparison


def test_comparison_eliminates_but_does_not_rank_survivors():
    outcome = compare_mechanisms([LINEAR, FLAT], OBSERVED, tolerance=0.1)
    assert outcome["refuted"] == ["FLAT"]
    assert outcome["compatible"] == ["LINEAR"]
    assert "NOT ranked against each other" in outcome["interpretation_bound"]
    assert outcome["claim_tier"] == ClaimTier.SIMULATION_ONLY.value


def test_comparison_records_the_observed_source():
    outcome = compare_mechanisms([LINEAR], OBSERVED)
    assert outcome["observed_source"] == "DS_TEST"


def test_all_mechanisms_refuted_is_a_legitimate_outcome():
    outcome = compare_mechanisms([FLAT], OBSERVED, tolerance=0.1)
    assert outcome["compatible"] == []
    assert outcome["refuted"] == ["FLAT"]


# -------------------------------------------------------------------- severity
#
# v2 fix 1. Severity answers "could this test have failed?" before anything is said
# about what the mechanism did. The asymmetry is unchanged: `finding_direction` still
# only ever reads WEAKENS or INCONCLUSIVE, and the positive channel is a separate,
# simulation-only vocabulary that is always reported AT a severity.


WIDE_LINEAR = MechanismCandidate(
    "WIDE_LINEAR", "linear over a wide slope grid", linear,
    {"intercept": (10.0,), "slope": (0.0, 5.0, 10.0, 15.0, 20.0, 25.0)},
)


def test_severity_is_zero_when_nothing_could_have_been_rejected():
    """A test every parameterisation passes is not a test."""

    result = calibrate_mechanism(FLAT, OBSERVED, tolerance=0.99)
    assert not result.refuted
    assert result.severity_index == 0.0
    assert result.severity_band is SeverityBand.NEGLIGIBLE
    assert result.corroboration is Corroboration.NO_CORROBORATION_TEST_NOT_SEVERE
    assert result.finding_direction is FindingDirection.INCONCLUSIVE
    assert not result.corroborated


def test_low_severity_survival_is_still_inconclusive_and_not_corroboration():
    """The asymmetry: compatibility on a weak test buys nothing at all."""

    result = calibrate_mechanism(WIDE_LINEAR, OBSERVED, tolerance=0.32)
    assert not result.refuted
    assert result.severity_band is SeverityBand.LOW
    assert result.finding_direction is FindingDirection.INCONCLUSIVE
    assert result.corroboration is Corroboration.COMPATIBLE_ONLY
    assert not result.corroborated
    assert "not support" in result.narrative


def test_high_severity_survival_is_corroboration_at_a_stated_severity():
    result = calibrate_mechanism(LINEAR, OBSERVED, tolerance=0.1)
    assert result.severity_band is SeverityBand.HIGH
    assert result.corroborated
    assert result.corroboration is Corroboration.CORROBORATED_AT_HIGH_SEVERITY
    # Even here the claim vocabulary does not move and the warning survives.
    assert result.finding_direction is FindingDirection.INCONCLUSIVE
    assert result.finding_direction is not FindingDirection.SUPPORTS
    assert "CORROBORATED AT SEVERITY" in result.narrative
    assert "NOT a statement that the" in result.narrative
    assert "not support" in result.narrative


def test_severity_is_zero_if_any_single_factor_is_zero():
    """Geometric mean: two strong factors may not launder one fatal weakness."""

    severity = assess_severity(grid_size=100, accepted=0, tolerance=0.9, observed=OBSERVED)
    assert severity.rejection_fraction == 1.0
    assert severity.tolerance_tightness == 0.0
    assert severity.index == 0.0


def test_severity_rises_with_the_fraction_of_the_grid_rejected():
    loose = assess_severity(grid_size=10, accepted=9, tolerance=0.05, observed=OBSERVED)
    tight = assess_severity(grid_size=10, accepted=1, tolerance=0.05, observed=OBSERVED)
    assert tight.index > loose.index


def test_severity_rises_with_the_number_of_periods_constrained():
    short = ObservedSeries(name="s", source_id="x", values=(10.0, 20.0, 30.0))
    long = ObservedSeries(name="l", source_id="x", values=tuple(10.0 * i for i in range(1, 25)))
    a = assess_severity(grid_size=10, accepted=1, tolerance=0.05, observed=short)
    b = assess_severity(grid_size=10, accepted=1, tolerance=0.05, observed=long)
    assert b.series_constraint > a.series_constraint


def test_a_refuted_mechanism_reports_severity_but_no_corroboration():
    result = calibrate_mechanism(FLAT, OBSERVED, tolerance=0.1)
    assert result.refuted
    assert result.corroboration is Corroboration.NOT_APPLICABLE_REFUTED
    assert result.severity_index > 0.0
    assert "severity" in result.narrative


def test_comparison_reports_corroboration_separately_from_compatibility():
    outcome = compare_mechanisms([LINEAR, FLAT], OBSERVED, tolerance=0.1)
    assert outcome["compatible"] == ["LINEAR"]
    assert outcome["corroborated_at_high_severity"] == ["LINEAR"]
    assert outcome["severity"]["FLAT"]["band"] == "HIGH"
    # The warning that compatibility is not support must survive the change.
    assert "NOT ranked against each other" in outcome["interpretation_bound"]
    assert "may not be" in outcome["interpretation_bound"]


def test_low_severity_survivors_are_not_listed_as_corroborated():
    outcome = compare_mechanisms([WIDE_LINEAR], OBSERVED, tolerance=0.32)
    assert outcome["compatible"] == ["WIDE_LINEAR"]
    assert outcome["corroborated_at_high_severity"] == []
