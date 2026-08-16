from __future__ import annotations

from dataclasses import dataclass, field

from oslt_research.domain.enums import ClaimTier, EpistemicStatus

from .feasibility import PropositionFeasibility, Reachability
from .sample_size import attainable_envelope, design_effect, two_group_standardised_mean_sample_per_arm
from .simulation import SIMULATION_DISCLOSURE, minimum_detectable_odds_ratio


#: Effect sizes worth powering for. Below OR 1.3 a study on this scale is usually
#: unaffordable; above OR 2.0 the effect would already be visible in service statistics.
TARGET_EFFECTS = (1.3, 1.5, 2.0)


@dataclass(frozen=True)
class DesignRequirement:
    """What a blocked proposition would actually cost to answer.

    This is the legitimate use of simulation against an unanswerable question: not
    inventing the answer, but pricing the study that could produce one. Every figure is a
    property of the design under stated assumptions, so the whole object is SIMULATION_ONLY
    and none of it is evidence about anyone.
    """

    proposition_id: str
    model_family: str
    domain: str
    reachability: Reachability
    design_needed: str
    minimum_detectable_or: float | None
    participants_required: dict[str, int] = field(default_factory=dict)
    follow_up_note: str = ""
    governance_needed: list[str] = field(default_factory=list)
    epistemic_status: EpistemicStatus = field(default=EpistemicStatus.SIMULATION, init=False)
    claim_tier: ClaimTier = field(default=ClaimTier.SIMULATION_ONLY, init=False)
    disclosure: str = field(default=SIMULATION_DISCLOSURE, init=False)


def _design_for(item: PropositionFeasibility) -> tuple[str, str, list[str]]:
    if item.reachability is Reachability.NEEDS_PRIMARY_COLLECTION:
        return (
            "prospective cohort with recruited participants",
            "baseline before exposure, then repeated measurement; length set by the "
            "outcome's natural history, not by convenience",
            [
                "research ethics committee favourable opinion",
                "informed consent process and participant information sheet",
                "data protection impact assessment and lawful basis",
                "sponsor and indemnity",
            ],
        )
    if item.reachability is Reachability.NEEDS_INDIVIDUAL_LEVEL:
        return (
            "record-linkage cohort from existing individual-level administrative data",
            "exposure must be observed before outcome for each individual; a cross-section "
            "cannot establish ordering however large",
            [
                "data access agreement with the custodian",
                "approved analysis specification and disclosure control",
                "secure environment (TRE/SDE) accreditation",
            ],
        )
    if item.reachability is Reachability.NEEDS_RESTRICTED_ACCESS:
        return (
            "analysis within a secure environment or under licence",
            "as permitted by the licence; often no individual follow-up available",
            [
                "licence or data sharing agreement",
                "approved analysis specification",
                "disclosure-checked outputs only",
            ],
        )
    if item.reachability is Reachability.NEEDS_PREDICTOR_SOURCE:
        # Not an access problem and not a design problem: the predictor exists somewhere,
        # it is simply not in this proposition's required set. The fix is registry work
        # plus a harvest, and pricing it as a cohort study would overstate it wildly.
        return (
            "open-data analysis, once a workstream carrying the named predictor is "
            "required and harvested",
            "no participant follow-up; the block is a missing predictor series, not access",
            [
                "registry amendment adding the workstream that carries the predictor",
                "pre-registration of the direction test before the predictor is harvested",
            ],
        )
    return ("open-data analysis", "no restriction", [])


def requirement_for(
    item: PropositionFeasibility,
    *,
    baseline_event_rate: float = 0.10,
    attrition_fraction: float = 0.25,
    cluster_size: float = 1.0,
    intraclass_correlation: float = 0.02,
    replicates: int = 600,
) -> DesignRequirement:
    """Price the study that would answer one blocked proposition.

    Defaults are deliberately unflattering: a quarter attrition over follow-up, and a
    baseline event rate low enough to be realistic for the outcomes in this registry. An
    optimistic assumption here would understate the cost of the study by an order of
    magnitude and make a plan look feasible that is not.
    """

    design, follow_up, governance = _design_for(item)
    deff = design_effect(max(1.0, cluster_size), intraclass_correlation)

    participants: dict[str, int] = {}
    for odds_ratio in TARGET_EFFECTS:
        # Two-proportion comparison, inflated for clustering and attrition, then rounded
        # up to the analysable-arm size the envelope will actually accept.
        effect_size = abs(odds_ratio - 1.0) / 2.0
        per_arm = two_group_standardised_mean_sample_per_arm(max(effect_size, 0.05))
        total = int(round(per_arm * 2 * deff / (1 - attrition_fraction)))
        participants[f"OR_{odds_ratio}"] = total

    largest = max(participants.values()) if participants else 0
    envelope = attainable_envelope(
        available_n=max(largest, 1),
        effective_parameters=8,
        outcome_events=int(largest * baseline_event_rate),
        design_effect_value=deff,
        attrition_fraction=attrition_fraction,
    )

    detectable, _ = minimum_detectable_odds_ratio(
        n_studies=max(int(envelope.effective_n), 2),
        baseline_publication_probability=baseline_event_rate,
        replicates=replicates,
    )

    return DesignRequirement(
        proposition_id=item.proposition_id,
        model_family=item.model_family,
        domain=item.domain,
        reachability=item.reachability,
        design_needed=design,
        minimum_detectable_or=detectable,
        participants_required=participants,
        follow_up_note=follow_up,
        governance_needed=governance,
    )


def requirements_for_blocked(
    census_results: list[PropositionFeasibility], **kwargs: float | int
) -> list[DesignRequirement]:
    return [
        requirement_for(item, **kwargs)  # type: ignore[arg-type]
        for item in census_results
        if not item.testable_now
    ]
