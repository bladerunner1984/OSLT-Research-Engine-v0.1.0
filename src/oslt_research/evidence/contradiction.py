from __future__ import annotations

from itertools import combinations
from typing import Iterable

from oslt_research.domain.enums import ContradictionClass, FindingDirection
from oslt_research.domain.models import ContradictionAssessment, KernelResult


OPPOSING_DIRECTIONS = {
    (FindingDirection.SUPPORTS, FindingDirection.WEAKENS),
    (FindingDirection.WEAKENS, FindingDirection.SUPPORTS),
    (FindingDirection.SUPPORTS, FindingDirection.FALSIFIES),
    (FindingDirection.FALSIFIES, FindingDirection.SUPPORTS),
}


def assess_pair(left: KernelResult, right: KernelResult) -> ContradictionAssessment:
    if left.proposition_id != right.proposition_id:
        return ContradictionAssessment(
            left_result_id=left.result_id,
            right_result_id=right.result_id,
            classification=ContradictionClass.NOT_COMPARABLE.value,
            explanation="Different propositions are not direct contradictions.",
        )

    left_scope = left.scope
    right_scope = right.scope
    comparisons = [
        ("construct_name", ContradictionClass.CONSTRUCT_MISMATCH),
        ("population", ContradictionClass.SCOPE_MISMATCH),
        ("period", ContradictionClass.PERIOD_MISMATCH),
        ("jurisdiction", ContradictionClass.JURISDICTION_MISMATCH),
        ("estimand", ContradictionClass.ESTIMAND_MISMATCH),
    ]
    for field, classification in comparisons:
        if getattr(left_scope, field).strip().casefold() != getattr(right_scope, field).strip().casefold():
            return ContradictionAssessment(
                left_result_id=left.result_id,
                right_result_id=right.result_id,
                classification=classification.value,
                explanation=f"Results differ on {'construct' if field == 'construct_name' else field}; align scope before substantive comparison.",
            )

    if (left.finding_direction, right.finding_direction) in OPPOSING_DIRECTIONS:
        return ContradictionAssessment(
            left_result_id=left.result_id,
            right_result_id=right.result_id,
            classification=ContradictionClass.SUBSTANTIVE_CONTRADICTION.value,
            explanation="Aligned results point in opposing substantive directions.",
        )

    return ContradictionAssessment(
        left_result_id=left.result_id,
        right_result_id=right.result_id,
        classification=ContradictionClass.CONSISTENT.value,
        explanation="No aligned substantive contradiction detected.",
    )


def find_substantive_contradictions(results: Iterable[KernelResult]) -> list[ContradictionAssessment]:
    assessments = [assess_pair(left, right) for left, right in combinations(results, 2)]
    return [
        item
        for item in assessments
        if item.classification == ContradictionClass.SUBSTANTIVE_CONTRADICTION.value
    ]
