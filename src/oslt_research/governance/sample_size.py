from __future__ import annotations

import math
from dataclasses import dataclass

from oslt_research.domain.enums import ClaimTier


@dataclass(frozen=True)
class AttainableInferenceEnvelope:
    available_n: int
    outcome_events: int | None
    effective_parameters: int
    design_effect: float
    attrition_fraction: float
    effective_n: float
    events_per_effective_parameter: float | None
    permitted_claim_tier: ClaimTier
    warnings: list[str]


def proportion_sample_size(
    expected_proportion: float,
    margin_of_error: float,
    *,
    confidence_z: float = 1.96,
) -> int:
    if not 0 < expected_proportion < 1:
        raise ValueError("expected_proportion must be between 0 and 1")
    if margin_of_error <= 0:
        raise ValueError("margin_of_error must be positive")
    return math.ceil(
        confidence_z**2
        * expected_proportion
        * (1 - expected_proportion)
        / margin_of_error**2
    )


def two_group_standardised_mean_sample_per_arm(
    effect_size: float,
    *,
    alpha_z: float = 1.96,
    power_z: float = 0.84,
) -> int:
    if effect_size <= 0:
        raise ValueError("effect_size must be positive")
    return math.ceil(2 * (alpha_z + power_z) ** 2 / effect_size**2)


def source_population_for_events(target_events: int, event_rate: float) -> int:
    if target_events <= 0:
        raise ValueError("target_events must be positive")
    if not 0 < event_rate <= 1:
        raise ValueError("event_rate must be in (0,1]")
    return math.ceil(target_events / event_rate)


def design_effect(cluster_size: float, intraclass_correlation: float) -> float:
    if cluster_size < 1:
        raise ValueError("cluster_size must be at least 1")
    if not 0 <= intraclass_correlation <= 1:
        raise ValueError("intraclass_correlation must be between 0 and 1")
    return 1 + (cluster_size - 1) * intraclass_correlation


def attainable_envelope(
    *,
    available_n: int,
    effective_parameters: int,
    outcome_events: int | None = None,
    design_effect_value: float = 1.0,
    attrition_fraction: float = 0.0,
) -> AttainableInferenceEnvelope:
    if available_n <= 0:
        raise ValueError("available_n must be positive")
    if effective_parameters <= 0:
        raise ValueError("effective_parameters must be positive")
    if design_effect_value < 1:
        raise ValueError("design_effect_value must be at least 1")
    if not 0 <= attrition_fraction < 1:
        raise ValueError("attrition_fraction must be in [0,1)")

    effective_n = available_n * (1 - attrition_fraction) / design_effect_value
    events_per_parameter = (
        outcome_events / effective_parameters if outcome_events is not None else None
    )
    warnings: list[str] = []

    if effective_n < 200:
        tier = ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY
        warnings.append("VERY_LIMITED_EFFECTIVE_SAMPLE")
    elif outcome_events is not None and outcome_events < 50:
        tier = ClaimTier.ASSOCIATION_ONLY
        warnings.append("RARE_EVENT_INFORMATION_LIMIT")
    elif effective_n < 1_000:
        tier = ClaimTier.ASSOCIATION_ONLY
        warnings.append("SUBGROUP_AND_INTERACTION_LIMIT")
    elif outcome_events is not None and events_per_parameter is not None and events_per_parameter < 10:
        tier = ClaimTier.ASSOCIATION_ONLY
        warnings.append("MODEL_PARAMETER_INFORMATION_LIMIT")
    else:
        tier = ClaimTier.LIMITED_CAUSAL_EVIDENCE

    warnings.append("CLAIM_TIER_IS_PLANNING_CEILING_NOT_CAUSAL_VALIDATION")
    return AttainableInferenceEnvelope(
        available_n=available_n,
        outcome_events=outcome_events,
        effective_parameters=effective_parameters,
        design_effect=design_effect_value,
        attrition_fraction=attrition_fraction,
        effective_n=effective_n,
        events_per_effective_parameter=events_per_parameter,
        permitted_claim_tier=tier,
        warnings=warnings,
    )
