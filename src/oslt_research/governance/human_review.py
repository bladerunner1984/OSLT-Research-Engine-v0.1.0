from __future__ import annotations

from dataclasses import dataclass, field

from oslt_research.domain.enums import ClaimTier
from oslt_research.domain.models import KernelResult, SynthesisOutcome


@dataclass(frozen=True)
class ReviewDecision:
    required: bool
    reasons: list[str] = field(default_factory=list)


def kernel_review_decision(result: KernelResult) -> ReviewDecision:
    reasons: list[str] = []
    sensitive_terms = {"child", "children", "adolescent", "vulnerable"}
    population = result.scope.population.casefold()
    if any(term in population for term in sensitive_terms):
        reasons.append("SENSITIVE_OR_CHILD_POPULATION")
    if result.epistemic_status.value == "CAUSAL_INFERENCE" and result.claim_tier in {
        ClaimTier.ASSOCIATION_ONLY,
        ClaimTier.LIMITED_CAUSAL_EVIDENCE,
    }:
        reasons.append("CAUSAL_CLAIM_WITH_LIMITED_CERTAINTY")
    if result.falsifier_status.value in {"PARTIALLY_TRIGGERED", "TRIGGERED"}:
        reasons.append("FALSIFIER_TRIGGERED")
    if result.certainty.provenance_completeness < 0.8:
        reasons.append("LOW_PROVENANCE_COMPLETENESS")
    return ReviewDecision(required=bool(reasons), reasons=reasons)


def synthesis_review_decision(outcome: SynthesisOutcome) -> ReviewDecision:
    reasons = list(outcome.warnings)
    if outcome.unresolved_contradictions:
        reasons.append("UNRESOLVED_SUBSTANTIVE_CONTRADICTION")
    if outcome.claim_tier in {
        ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE,
        ClaimTier.HIGH_TRIANGULATED_CAUSAL_EVIDENCE,
    }:
        reasons.append("HIGH_IMPACT_CAUSAL_RELEASE")
    return ReviewDecision(required=bool(reasons), reasons=sorted(set(reasons)))
