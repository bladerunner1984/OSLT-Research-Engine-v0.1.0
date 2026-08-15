import pytest

from oslt_research.ai.gateway import DisabledModelGateway, ModelGatewayError, ModelRequest
from oslt_research.domain.enums import (
    ClaimTier,
    EpistemicStatus,
    FalsifierStatus,
    FindingDirection,
    ModelFamily,
)
from oslt_research.domain.models import (
    CertaintyVector,
    ContradictionAssessment,
    KernelResult,
    ScopeContext,
    SynthesisOutcome,
)
from oslt_research.governance.human_review import kernel_review_decision, synthesis_review_decision


def certainty(value: float = 0.7, *, provenance: float | None = None) -> CertaintyVector:
    values = {name: value for name in CertaintyVector.model_fields}
    if provenance is not None:
        values["provenance_completeness"] = provenance
    return CertaintyVector(**values)


async def test_disabled_model_gateway_is_fail_closed():
    gateway = DisabledModelGateway()
    with pytest.raises(ModelGatewayError, match="MODEL_GATEWAY_DISABLED"):
        await gateway.complete(
            ModelRequest(
                task_id="orientation-coding",
                system_prompt="Follow the evidence contract.",
                user_payload="Classify this public abstract.",
                response_schema={"type": "object"},
            )
        )


def test_kernel_review_required_for_sensitive_limited_causal_result():
    result = KernelResult(
        result_id="KR-1",
        run_id="R1",
        kernel_name="DEVELOPMENTAL",
        proposition_id="MD01",
        model_family=ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL,
        scope=ScopeContext(
            construct="development",
            population="children",
            period="adolescence",
            jurisdiction="UK",
            estimand="average association",
        ),
        epistemic_status=EpistemicStatus.CAUSAL_INFERENCE,
        finding_direction=FindingDirection.SUPPORTS,
        uncertainty="Wide interval; observational design",
        certainty=certainty(0.65, provenance=0.6),
        claim_tier=ClaimTier.LIMITED_CAUSAL_EVIDENCE,
        evidence_ids=["EV-1"],
        dependency_families=["FAM-1"],
        falsifier_status=FalsifierStatus.TRIGGERED,
        model_impacts={ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value: 0.4},
        narrative="A limited observational association was detected.",
    )
    decision = kernel_review_decision(result)
    assert decision.required is True
    assert "SENSITIVE_OR_CHILD_POPULATION" in decision.reasons
    assert "CAUSAL_CLAIM_WITH_LIMITED_CERTAINTY" in decision.reasons
    assert "FALSIFIER_TRIGGERED" in decision.reasons
    assert "LOW_PROVENANCE_COMPLETENESS" in decision.reasons


def test_synthesis_review_required_for_unresolved_contradiction():
    outcome = SynthesisOutcome(
        synthesis_id="SYN-R1",
        run_id="R1",
        included_result_ids=["KR-1", "KR-2"],
        excluded_result_ids=[],
        comparative_support_index={family.value: 0.0 for family in ModelFamily},
        leading_models=[ModelFamily.NULL_OR_ALTERNATIVE.value],
        unresolved_contradictions=[
            ContradictionAssessment(
                left_result_id="KR-1",
                right_result_id="KR-2",
                classification="SUBSTANTIVE_CONTRADICTION",
                explanation="Aligned results point in opposite directions.",
            )
        ],
        limiting_dimension="causal_identification",
        limiting_score=0.2,
        claim_tier=ClaimTier.ASSOCIATION_ONLY,
        bounded_conclusion="Evidence is inconclusive.",
        human_review_required=True,
    )
    decision = synthesis_review_decision(outcome)
    assert decision.required is True
    assert "UNRESOLVED_SUBSTANTIVE_CONTRADICTION" in decision.reasons
