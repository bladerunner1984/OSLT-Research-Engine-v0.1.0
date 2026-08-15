from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import NormalDist

import numpy as np

from oslt_research.domain.enums import ClaimTier, EpistemicStatus

from .sample_size import design_effect


#: Every object in this module carries it. Simulation answers "what could this design
#: detect, and what would it take to overturn it" - never "what is true of the world".
SIMULATION_DISCLOSURE = (
    "SIMULATION OUTPUT. This quantifies the properties of a study design under stated "
    "assumptions. It is not evidence about any population, cannot support a claim about "
    "observed people, and must not be reported as a finding. Its values follow from the "
    "assumptions supplied, and change when those assumptions change."
)


@dataclass(frozen=True)
class SimulationResult:
    """Base for simulation outputs, pinned to the SIMULATION_ONLY ceiling.

    epistemic_status and claim_tier are not parameters. calibrate_claim_tier() routes
    EpistemicStatus.SIMULATION to ClaimTier.SIMULATION_ONLY unconditionally, and these
    objects are constructed so no caller can present them at any other tier.
    """

    assumptions: dict[str, float | int | str]
    epistemic_status: EpistemicStatus = field(default=EpistemicStatus.SIMULATION, init=False)
    claim_tier: ClaimTier = field(default=ClaimTier.SIMULATION_ONLY, init=False)
    disclosure: str = field(default=SIMULATION_DISCLOSURE, init=False)


@dataclass(frozen=True)
class PowerEnvelope(SimulationResult):
    replicates: int = 0
    power: float = 0.0
    effective_n: float = 0.0
    design_effect_value: float = 1.0
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SensitivityBound(SimulationResult):
    observed_ratio: float = 1.0
    e_value: float = 1.0
    e_value_for_ci_limit: float | None = None
    interpretation: str = ""


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def simulate_selection_power(
    *,
    n_studies: int,
    baseline_publication_probability: float,
    odds_ratio: float,
    proportion_exposed: float = 0.5,
    n_dependency_families: int | None = None,
    intraclass_correlation: float = 0.05,
    alpha: float = 0.05,
    replicates: int = 2_000,
    seed: int = 20260815,
) -> PowerEnvelope:
    """Monte Carlo power for a direction-dependent publication-selection test.

    This is the MD11 / MX14 design question: with the corpus we can actually assemble,
    what size of selection effect could we detect at all? A design that cannot detect a
    plausible effect produces an uninformative null rather than evidence of absence, and
    knowing that in advance is the point of running this.

    Clustering matters here. Studies sharing a dependency family are correlated, so the
    effective sample is smaller than the record count. n_dependency_families drives a
    design effect that shrinks it.
    """

    if n_studies <= 0:
        raise ValueError("n_studies must be positive")
    if not 0 < baseline_publication_probability < 1:
        raise ValueError("baseline_publication_probability must be in (0,1)")
    if odds_ratio <= 0:
        raise ValueError("odds_ratio must be positive")
    if not 0 < proportion_exposed < 1:
        raise ValueError("proportion_exposed must be in (0,1)")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0,1)")
    if replicates <= 0:
        raise ValueError("replicates must be positive")

    families = n_dependency_families or n_studies
    if families <= 0 or families > n_studies:
        raise ValueError("n_dependency_families must be in (0, n_studies]")

    mean_cluster_size = n_studies / families
    deff = design_effect(max(1.0, mean_cluster_size), intraclass_correlation)
    effective_n = n_studies / deff

    p0 = baseline_publication_probability
    odds0 = p0 / (1 - p0)
    p1 = (odds0 * odds_ratio) / (1 + odds0 * odds_ratio)

    n_exposed = max(1, int(round(effective_n * proportion_exposed)))
    n_control = max(1, int(round(effective_n * (1 - proportion_exposed))))

    rng = _rng(seed)
    exposed_events = rng.binomial(n_exposed, p1, size=replicates)
    control_events = rng.binomial(n_control, p0, size=replicates)

    prop_exposed = exposed_events / n_exposed
    prop_control = control_events / n_control
    pooled = (exposed_events + control_events) / (n_exposed + n_control)
    standard_error = np.sqrt(pooled * (1 - pooled) * (1 / n_exposed + 1 / n_control))
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(standard_error > 0, (prop_exposed - prop_control) / standard_error, 0.0)

    critical = NormalDist().inv_cdf(1 - alpha / 2)
    power = float(np.mean(np.abs(z) > critical))

    warnings: list[str] = []
    if effective_n < 200:
        warnings.append("VERY_LIMITED_EFFECTIVE_SAMPLE")
    if power < 0.80:
        warnings.append("UNDERPOWERED_A_NULL_HERE_IS_NOT_EVIDENCE_OF_ABSENCE")
    if deff > 2:
        warnings.append("SUBSTANTIAL_CLUSTERING_EFFECTIVE_SAMPLE_MUCH_SMALLER_THAN_RECORD_COUNT")

    return PowerEnvelope(
        assumptions={
            "n_studies": n_studies,
            "baseline_publication_probability": p0,
            "odds_ratio": odds_ratio,
            "proportion_exposed": proportion_exposed,
            "n_dependency_families": families,
            "intraclass_correlation": intraclass_correlation,
            "alpha": alpha,
            "seed": seed,
        },
        replicates=replicates,
        power=power,
        effective_n=effective_n,
        design_effect_value=deff,
        warnings=warnings,
    )


def minimum_detectable_odds_ratio(
    *,
    n_studies: int,
    baseline_publication_probability: float,
    target_power: float = 0.80,
    search_ceiling: float = 12.0,
    tolerance: float = 0.01,
    **kwargs: object,
) -> tuple[float | None, PowerEnvelope | None]:
    """Smallest odds ratio reaching target_power, by bisection.

    Returns (None, None) when even search_ceiling cannot reach the target: that is the
    informative answer, meaning the design cannot detect an effect of any plausible size.
    """

    if not 0 < target_power < 1:
        raise ValueError("target_power must be in (0,1)")

    def power_at(ratio: float) -> PowerEnvelope:
        return simulate_selection_power(
            n_studies=n_studies,
            baseline_publication_probability=baseline_publication_probability,
            odds_ratio=ratio,
            **kwargs,  # type: ignore[arg-type]
        )

    ceiling = power_at(search_ceiling)
    if ceiling.power < target_power:
        return None, None

    low, high = 1.0, search_ceiling
    best = ceiling
    while high - low > tolerance:
        middle = (low + high) / 2
        envelope = power_at(middle)
        if envelope.power >= target_power:
            high, best = middle, envelope
        else:
            low = middle
    return high, best


def e_value(
    observed_ratio: float,
    *,
    confidence_limit: float | None = None,
) -> SensitivityBound:
    """VanderWeele-Ding E-value: minimum joint confounder association to explain a result.

    An E-value of 2.1 means an unmeasured confounder would need to be associated with both
    exposure and outcome by a risk ratio of at least 2.1, beyond every measured covariate,
    to reduce the observed association to null. Small E-values mean fragile findings.

    This is the honest use of simulation-adjacent methods on an observational design: it
    bounds how much a result could be an artefact, without inventing any data.
    """

    if observed_ratio <= 0:
        raise ValueError("observed_ratio must be positive")

    def bound(ratio: float) -> float:
        if ratio < 1:
            ratio = 1 / ratio
        if math.isclose(ratio, 1.0):
            return 1.0
        return ratio + math.sqrt(ratio * (ratio - 1))

    primary = bound(observed_ratio)

    limit_value: float | None = None
    if confidence_limit is not None:
        if confidence_limit <= 0:
            raise ValueError("confidence_limit must be positive")
        crosses_null = (observed_ratio > 1 and confidence_limit <= 1) or (
            observed_ratio < 1 and confidence_limit >= 1
        )
        limit_value = 1.0 if crosses_null else bound(confidence_limit)

    if primary < 1.5:
        reading = "FRAGILE: modest unmeasured confounding would explain this away."
    elif primary < 3:
        reading = "MODERATE: plausible confounders of ordinary strength could explain this."
    else:
        reading = "ROBUST to weak confounding; strong specific confounders remain possible."

    return SensitivityBound(
        assumptions={"observed_ratio": observed_ratio, "confidence_limit": confidence_limit or 0.0},
        observed_ratio=observed_ratio,
        e_value=primary,
        e_value_for_ci_limit=limit_value,
        interpretation=reading,
    )
