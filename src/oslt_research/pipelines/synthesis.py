from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from oslt_research.domain.enums import ClaimTier, EpistemicStatus, ModelFamily
from oslt_research.domain.models import CertaintyVector, KernelResult, SynthesisOutcome
from oslt_research.evidence.contradiction import find_substantive_contradictions
from oslt_research.evidence.dependency import EvidenceDependencyGraph
from oslt_research.governance.claim_gates import calibrate_claim_tier


TIER_RANK = {
    ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY: 0,
    ClaimTier.THEORY_DEPENDENT_INTERPRETATION: 0,
    ClaimTier.SIMULATION_ONLY: 0,
    ClaimTier.ASSOCIATION_ONLY: 1,
    ClaimTier.LIMITED_CAUSAL_EVIDENCE: 2,
    ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE: 3,
    ClaimTier.HIGH_TRIANGULATED_CAUSAL_EVIDENCE: 4,
}


def _aggregate_certainty(results: list[KernelResult]) -> CertaintyVector:
    fields = CertaintyVector.model_fields
    minima = {
        name: min(getattr(result.certainty, name) for result in results) for name in fields
    }
    return CertaintyVector(**minima)


class MasterSynthesisKernel:
    """Dependency-aware comparative synthesis over structured kernel results.

    The output is a comparative support index, not a probability of truth and not a vote count.
    """

    name = "MASTER_SYNTHESIS"

    def synthesise(self, *, run_id: str, results: Iterable[KernelResult]) -> SynthesisOutcome:
        items = [item for item in results if item.run_id == run_id]
        excluded = [item.result_id for item in results if item.run_id != run_id]
        if not items:
            raise ValueError("NO_ALIGNED_KERNEL_RESULTS")

        contradictions = find_substantive_contradictions(items)
        contributions: dict[tuple[str, str], float] = {}
        contribution_weights: dict[tuple[str, str], float] = {}

        for result in items:
            weight = EvidenceDependencyGraph.effective_result_weight(result)
            families = result.dependency_families or [f"result:{result.result_id}"]
            impacts = result.model_impacts or {result.model_family.value: 0.0}
            for model_name, impact in impacts.items():
                share = weight / max(1, len(families))
                for family in families:
                    key = (model_name, family)
                    candidate = impact * share
                    # Dependency collapse: one research family contributes at most once per model.
                    if key not in contributions or abs(candidate) > abs(contributions[key]):
                        contributions[key] = candidate
                        contribution_weights[key] = abs(share)

        raw_scores: dict[str, float] = defaultdict(float)
        denominators: dict[str, float] = defaultdict(float)
        for (model_name, family), contribution in contributions.items():
            raw_scores[model_name] += contribution
            denominators[model_name] += contribution_weights[(model_name, family)]

        indices: dict[str, float] = {}
        for family in ModelFamily:
            denominator = denominators.get(family.value, 0.0)
            score = raw_scores.get(family.value, 0.0)
            indices[family.value] = round(score / denominator, 6) if denominator else 0.0

        maximum = max(indices.values())
        leading = sorted(
            name for name, value in indices.items() if value >= maximum - 0.05
        )

        aggregate = _aggregate_certainty(items)
        causal_requested = any(
            item.epistemic_status == EpistemicStatus.CAUSAL_INFERENCE for item in items
        )
        aggregate_status = (
            EpistemicStatus.CAUSAL_INFERENCE if causal_requested else EpistemicStatus.ASSOCIATION
        )
        calibrated = calibrate_claim_tier(aggregate, aggregate_status)
        max_result_tier = min(items, key=lambda item: TIER_RANK[item.claim_tier]).claim_tier
        claim_tier = (
            calibrated
            if TIER_RANK[calibrated] <= TIER_RANK[max_result_tier]
            else max_result_tier
        )
        limiting_dimension, limiting_score = aggregate.minimum()

        warnings: list[str] = [
            "COMPARATIVE_SUPPORT_INDEX_IS_NOT_A_TRUTH_PROBABILITY",
            "MODEL_AGREEMENT_HAS_ZERO_EVIDENTIAL_WEIGHT",
        ]
        if contradictions:
            warnings.append("UNRESOLVED_SUBSTANTIVE_CONTRADICTION")
        if all(abs(value) < 0.05 for value in indices.values()):
            warnings.append("EVIDENCE_DOES_NOT_DISCRIMINATE_BETWEEN_MODELS")

        human_review_required = bool(contradictions) or claim_tier in {
            ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE,
            ClaimTier.HIGH_TRIANGULATED_CAUSAL_EVIDENCE,
        }
        conclusion = (
            "The currently admitted kernel results provide the highest comparative support to "
            f"{', '.join(leading)}. The limiting certainty dimension is {limiting_dimension} "
            f"({limiting_score:.2f}). This ranking is bounded by the aligned scopes, dependency "
            "families and available counterevidence; it is not a universal or individual-level cause."
        )
        return SynthesisOutcome(
            synthesis_id=f"SYN-{run_id}",
            run_id=run_id,
            included_result_ids=[item.result_id for item in items],
            excluded_result_ids=excluded,
            comparative_support_index=indices,
            leading_models=leading,
            unresolved_contradictions=contradictions,
            limiting_dimension=limiting_dimension,
            limiting_score=limiting_score,
            claim_tier=claim_tier,
            bounded_conclusion=conclusion,
            human_review_required=human_review_required,
            warnings=warnings,
        )
