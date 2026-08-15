from __future__ import annotations

import pytest

from oslt_research.domain.enums import ClaimTier, EpistemicStatus
from oslt_research.domain.models import CertaintyVector
from oslt_research.governance.claim_gates import calibrate_claim_tier
from oslt_research.governance.simulation import (
    SIMULATION_DISCLOSURE,
    e_value,
    minimum_detectable_odds_ratio,
    simulate_selection_power,
)


BASE = {"n_studies": 400, "baseline_publication_probability": 0.55}


# --------------------------------------------------------- the SIMULATION_ONLY fuse


def test_simulation_output_is_pinned_to_simulation_only():
    envelope = simulate_selection_power(**BASE, odds_ratio=2.0, replicates=200)
    assert envelope.epistemic_status is EpistemicStatus.SIMULATION
    assert envelope.claim_tier is ClaimTier.SIMULATION_ONLY
    assert envelope.disclosure == SIMULATION_DISCLOSURE


def test_perfect_certainty_cannot_lift_simulation_above_the_ceiling():
    """No certainty vector, however strong, promotes simulation to an empirical tier."""

    perfect = CertaintyVector(**{name: 1.0 for name in CertaintyVector.model_fields})
    assert calibrate_claim_tier(perfect, EpistemicStatus.SIMULATION) is ClaimTier.SIMULATION_ONLY


def test_simulation_result_fields_cannot_be_overridden_by_caller():
    envelope = simulate_selection_power(**BASE, odds_ratio=2.0, replicates=200)
    with pytest.raises(Exception):
        envelope.claim_tier = ClaimTier.HIGH_TRIANGULATED_CAUSAL_EVIDENCE  # type: ignore[misc]


# ------------------------------------------------------------------------- power


def test_power_rises_with_effect_size():
    powers = [
        simulate_selection_power(**BASE, odds_ratio=ratio, replicates=800).power
        for ratio in (1.1, 1.5, 2.5)
    ]
    assert powers == sorted(powers)
    assert powers[0] < 0.5 < powers[-1]


def test_underpowered_design_is_flagged_not_silently_returned():
    envelope = simulate_selection_power(**BASE, odds_ratio=1.05, replicates=500)
    assert envelope.power < 0.80
    assert "UNDERPOWERED_A_NULL_HERE_IS_NOT_EVIDENCE_OF_ABSENCE" in envelope.warnings


def test_clustering_shrinks_the_effective_sample():
    independent = simulate_selection_power(
        **BASE, odds_ratio=1.5, n_dependency_families=400, replicates=400
    )
    clustered = simulate_selection_power(
        **BASE, odds_ratio=1.5, n_dependency_families=40,
        intraclass_correlation=0.3, replicates=400,
    )
    assert clustered.effective_n < independent.effective_n
    assert clustered.design_effect_value > independent.design_effect_value
    assert "SUBSTANTIAL_CLUSTERING_EFFECTIVE_SAMPLE_MUCH_SMALLER_THAN_RECORD_COUNT" in (
        clustered.warnings
    )


def test_power_is_reproducible_for_a_fixed_seed():
    first = simulate_selection_power(**BASE, odds_ratio=1.5, replicates=300, seed=7)
    second = simulate_selection_power(**BASE, odds_ratio=1.5, replicates=300, seed=7)
    assert first.power == second.power


def test_minimum_detectable_effect_and_its_impossible_case():
    ratio, envelope = minimum_detectable_odds_ratio(**BASE, replicates=400)
    assert ratio is not None and envelope is not None
    assert 1.0 < ratio < 12.0
    assert envelope.power >= 0.80

    tiny = minimum_detectable_odds_ratio(
        n_studies=8, baseline_publication_probability=0.55, search_ceiling=1.2, replicates=300
    )
    assert tiny == (None, None)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_studies": 0, "baseline_publication_probability": 0.5, "odds_ratio": 2.0},
        {"n_studies": 10, "baseline_publication_probability": 1.5, "odds_ratio": 2.0},
        {"n_studies": 10, "baseline_publication_probability": 0.5, "odds_ratio": 0},
        {"n_studies": 10, "baseline_publication_probability": 0.5, "odds_ratio": 2.0,
         "n_dependency_families": 99},
    ],
)
def test_power_rejects_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        simulate_selection_power(**kwargs)


# ------------------------------------------------------------------- sensitivity


@pytest.mark.parametrize(
    "ratio,expected",
    [(1.0, 1.0), (2.0, 3.414), (0.5, 3.414)],
)
def test_e_value_matches_the_published_formula(ratio, expected):
    assert e_value(ratio).e_value == pytest.approx(expected, abs=1e-3)


def test_e_value_for_confidence_limit_crossing_null_is_one():
    bound = e_value(1.15, confidence_limit=0.95)
    assert bound.e_value_for_ci_limit == 1.0


def test_e_value_interpretation_bands():
    assert "FRAGILE" in e_value(1.05).interpretation
    assert "MODERATE" in e_value(1.3).interpretation
    assert "ROBUST" in e_value(4.0).interpretation


def test_e_value_rejects_non_positive_inputs():
    with pytest.raises(ValueError):
        e_value(0)
    with pytest.raises(ValueError):
        e_value(1.5, confidence_limit=-1)
