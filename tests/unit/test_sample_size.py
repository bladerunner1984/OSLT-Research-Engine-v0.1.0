import pytest

from oslt_research.domain.enums import ClaimTier
from oslt_research.governance.sample_size import (
    attainable_envelope,
    design_effect,
    proportion_sample_size,
    source_population_for_events,
    two_group_standardised_mean_sample_per_arm,
)


def test_closed_form_helpers():
    assert 380 <= proportion_sample_size(0.5, 0.05) <= 385
    assert two_group_standardised_mean_sample_per_arm(0.2) > 390
    assert source_population_for_events(3000, 0.1) == 30000
    assert design_effect(20, 0.05) == pytest.approx(1.95)


def test_envelope_lowers_claim_ceiling_instead_of_standard():
    tiny = attainable_envelope(available_n=100, effective_parameters=5)
    assert tiny.permitted_claim_tier == ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY
    medium = attainable_envelope(available_n=500, effective_parameters=5, outcome_events=100)
    assert medium.permitted_claim_tier == ClaimTier.ASSOCIATION_ONLY
    large = attainable_envelope(available_n=5000, effective_parameters=20, outcome_events=500)
    assert large.permitted_claim_tier == ClaimTier.LIMITED_CAUSAL_EVIDENCE
    assert "CLAIM_TIER_IS_PLANNING_CEILING_NOT_CAUSAL_VALIDATION" in large.warnings


@pytest.mark.parametrize(
    "call",
    [
        lambda: proportion_sample_size(0, 0.1),
        lambda: two_group_standardised_mean_sample_per_arm(0),
        lambda: source_population_for_events(0, 0.1),
        lambda: design_effect(0, 0.1),
        lambda: attainable_envelope(available_n=0, effective_parameters=1),
    ],
)
def test_invalid_sample_inputs_fail(call):
    with pytest.raises(ValueError):
        call()
