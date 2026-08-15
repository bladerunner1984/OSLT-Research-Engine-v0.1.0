from __future__ import annotations

from oslt_research.domain.enums import ClaimTier, EpistemicStatus
from oslt_research.domain.models import CertaintyVector


def calibrate_claim_tier(
    certainty: CertaintyVector,
    epistemic_status: EpistemicStatus,
    *,
    theory_dependent: bool = False,
    simulation_only: bool = False,
) -> ClaimTier:
    """Return the maximum permissible claim tier.

    Certainty is deliberately limited by the weakest dimension. Strong performance elsewhere cannot
    average away a fatal weakness in provenance, temporality, identification or independence.
    """

    if simulation_only or epistemic_status == EpistemicStatus.SIMULATION:
        return ClaimTier.SIMULATION_ONLY
    if theory_dependent and epistemic_status == EpistemicStatus.INTERPRETATION:
        return ClaimTier.THEORY_DEPENDENT_INTERPRETATION

    _, minimum = certainty.minimum()

    if epistemic_status not in {EpistemicStatus.CAUSAL_INFERENCE, EpistemicStatus.RECOMMENDATION}:
        if epistemic_status == EpistemicStatus.ASSOCIATION:
            return ClaimTier.ASSOCIATION_ONLY
        return ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY

    if certainty.causal_identification < 0.70 or certainty.temporal_ordering < 0.70:
        return ClaimTier.ASSOCIATION_ONLY
    if minimum >= 0.80 and certainty.replication >= 0.75 and certainty.source_independence >= 0.75:
        return ClaimTier.HIGH_TRIANGULATED_CAUSAL_EVIDENCE
    if minimum >= 0.60 and certainty.replication >= 0.50:
        return ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE
    if minimum >= 0.40:
        return ClaimTier.LIMITED_CAUSAL_EVIDENCE
    return ClaimTier.ASSOCIATION_ONLY
