from oslt_research.domain.enums import ClaimTier, EpistemicStatus
from oslt_research.governance.claim_gates import calibrate_claim_tier


def test_noncausal_statuses_are_bounded(certainty_factory):
    certainty = certainty_factory()
    assert (
        calibrate_claim_tier(certainty, EpistemicStatus.OBSERVATION)
        == ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY
    )
    assert (
        calibrate_claim_tier(certainty, EpistemicStatus.ASSOCIATION)
        == ClaimTier.ASSOCIATION_ONLY
    )
    assert (
        calibrate_claim_tier(certainty, EpistemicStatus.INTERPRETATION, theory_dependent=True)
        == ClaimTier.THEORY_DEPENDENT_INTERPRETATION
    )
    assert (
        calibrate_claim_tier(certainty, EpistemicStatus.SIMULATION)
        == ClaimTier.SIMULATION_ONLY
    )


def test_causal_gate_uses_weakest_dimension(certainty_factory):
    high = certainty_factory(0.85, replication=0.8, source_independence=0.8)
    assert (
        calibrate_claim_tier(high, EpistemicStatus.CAUSAL_INFERENCE)
        == ClaimTier.HIGH_TRIANGULATED_CAUSAL_EVIDENCE
    )
    moderate = certainty_factory(0.72, replication=0.6)
    assert (
        calibrate_claim_tier(moderate, EpistemicStatus.CAUSAL_INFERENCE)
        == ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE
    )
    limited = certainty_factory(0.75, replication=0.45, measurement_validity=0.45)
    assert (
        calibrate_claim_tier(limited, EpistemicStatus.CAUSAL_INFERENCE)
        == ClaimTier.LIMITED_CAUSAL_EVIDENCE
    )


def test_temporal_or_identification_failure_demotes_to_association(certainty_factory):
    certainty = certainty_factory(0.9, causal_identification=0.6)
    assert (
        calibrate_claim_tier(certainty, EpistemicStatus.CAUSAL_INFERENCE)
        == ClaimTier.ASSOCIATION_ONLY
    )
