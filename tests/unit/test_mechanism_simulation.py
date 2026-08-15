from __future__ import annotations

import pytest

from oslt_research.domain.enums import ClaimTier, EpistemicStatus, FindingDirection
from oslt_research.governance.mechanism_simulation import (
    MechanismCandidate,
    ObservedSeries,
    calibrate_mechanism,
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
