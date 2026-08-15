from __future__ import annotations

from collections.abc import Callable

import pytest

from oslt_research.domain.enums import (
    ClaimTier,
    EpistemicStatus,
    FalsifierStatus,
    FindingDirection,
    ModelFamily,
)
from oslt_research.domain.models import CertaintyVector, KernelResult, ScopeContext


CERTAINTY_FIELDS = list(CertaintyVector.model_fields)


@pytest.fixture
def certainty_factory() -> Callable[..., CertaintyVector]:
    def factory(value: float = 0.8, **overrides: float) -> CertaintyVector:
        payload = {name: value for name in CERTAINTY_FIELDS}
        payload.update(overrides)
        return CertaintyVector(**payload)

    return factory


@pytest.fixture
def result_factory(certainty_factory):
    def factory(
        *,
        result_id: str = "KR-1",
        run_id: str = "RUN-1",
        proposition_id: str = "MD11",
        model_family: ModelFamily = ModelFamily.MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL,
        finding_direction: FindingDirection = FindingDirection.SUPPORTS,
        impacts: dict[str, float] | None = None,
        dependency_families: list[str] | None = None,
        scope: ScopeContext | None = None,
        epistemic_status: EpistemicStatus = EpistemicStatus.ASSOCIATION,
        claim_tier: ClaimTier = ClaimTier.ASSOCIATION_ONLY,
        certainty: CertaintyVector | None = None,
    ) -> KernelResult:
        return KernelResult(
            result_id=result_id,
            run_id=run_id,
            proposition_id=proposition_id,
            kernel_name="TEST_KERNEL",
            model_family=model_family,
            scope=scope
            or ScopeContext(
                construct="construct",
                population="population",
                period="2020-2025",
                jurisdiction="UK",
                estimand="risk difference",
            ),
            finding_direction=finding_direction,
            epistemic_status=epistemic_status,
            effect_estimate=None,
            uncertainty="test uncertainty",
            certainty=certainty or certainty_factory(),
            evidence_ids=[f"EV-{result_id}"],
            counterevidence_ids=[],
            dependency_families=dependency_families or [f"family-{result_id}"],
            falsifier_status=FalsifierStatus.NOT_TRIGGERED,
            model_impacts=impacts
            or {
                model_family.value: 0.5,
            },
            claim_tier=claim_tier,
            narrative="test narrative",
        )

    return factory
