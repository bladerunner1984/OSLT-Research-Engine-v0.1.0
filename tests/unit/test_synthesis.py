import pytest

from oslt_research.domain.enums import FindingDirection, ModelFamily
from oslt_research.pipelines.synthesis import MasterSynthesisKernel


def test_synthesis_dependency_collapses_and_ranks_models(result_factory):
    first = result_factory(
        result_id="R1",
        impacts={
            ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value: 0.8,
            ModelFamily.NULL_OR_ALTERNATIVE.value: -0.8,
        },
        dependency_families=["shared-family"],
    )
    duplicate = result_factory(
        result_id="R2",
        impacts={
            ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value: 0.4,
            ModelFamily.NULL_OR_ALTERNATIVE.value: -0.4,
        },
        dependency_families=["shared-family"],
    )
    outcome = MasterSynthesisKernel().synthesise(run_id="RUN-1", results=[first, duplicate])
    assert outcome.leading_models == [ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value]
    assert outcome.comparative_support_index[
        ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL.value
    ] > 0
    assert "COMPARATIVE_SUPPORT_INDEX_IS_NOT_A_TRUTH_PROBABILITY" in outcome.warnings


def test_synthesis_detects_aligned_contradiction(result_factory):
    left = result_factory(result_id="L", finding_direction=FindingDirection.SUPPORTS)
    right = result_factory(result_id="R", finding_direction=FindingDirection.FALSIFIES)
    outcome = MasterSynthesisKernel().synthesise(run_id="RUN-1", results=[left, right])
    assert outcome.unresolved_contradictions
    assert outcome.human_review_required


def test_synthesis_rejects_empty_aligned_result_set(result_factory):
    other = result_factory(result_id="R", run_id="OTHER")
    with pytest.raises(ValueError, match="NO_ALIGNED_KERNEL_RESULTS"):
        MasterSynthesisKernel().synthesise(run_id="RUN-1", results=[other])
