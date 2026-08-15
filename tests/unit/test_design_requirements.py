from __future__ import annotations

import pytest

from oslt_research.domain.enums import ClaimTier, EpistemicStatus
from oslt_research.governance.design_requirements import (
    TARGET_EFFECTS,
    requirement_for,
    requirements_for_blocked,
)
from oslt_research.governance.feasibility import PropositionFeasibility, Reachability


def blocked(reachability: Reachability, proposition_id: str = "P1") -> PropositionFeasibility:
    return PropositionFeasibility(
        proposition_id=proposition_id,
        model_family="FAMILY_A",
        domain="A domain",
        reachability=reachability,
        temporal_requirement="longitudinal; exposure must precede outcome",
        maximum_claim_state="LIMITED_CAUSAL_EVIDENCE",
    )


def open_testable_item() -> PropositionFeasibility:
    return PropositionFeasibility(
        proposition_id="OK1",
        model_family="FAMILY_A",
        domain="A domain",
        reachability=Reachability.OPEN_TESTABLE,
    )


def test_requirement_is_pinned_to_simulation_only():
    """Pricing a study is not evidence about anyone in it."""

    requirement = requirement_for(blocked(Reachability.NEEDS_PRIMARY_COLLECTION), replicates=200)
    assert requirement.epistemic_status is EpistemicStatus.SIMULATION
    assert requirement.claim_tier is ClaimTier.SIMULATION_ONLY
    assert "not evidence about any population" in requirement.disclosure


def test_smaller_effects_need_larger_samples():
    requirement = requirement_for(blocked(Reachability.NEEDS_PRIMARY_COLLECTION), replicates=200)
    sizes = [requirement.participants_required[f"OR_{effect}"] for effect in TARGET_EFFECTS]
    assert sizes == sorted(sizes, reverse=True)
    assert sizes[0] > sizes[-1] * 5


def test_primary_collection_requires_ethics_and_consent():
    requirement = requirement_for(blocked(Reachability.NEEDS_PRIMARY_COLLECTION), replicates=200)
    governance = " ".join(requirement.governance_needed)
    assert "ethics" in governance and "consent" in governance
    assert "prospective cohort" in requirement.design_needed


def test_individual_level_requires_a_data_access_agreement_not_consent():
    requirement = requirement_for(blocked(Reachability.NEEDS_INDIVIDUAL_LEVEL), replicates=200)
    governance = " ".join(requirement.governance_needed)
    assert "data access agreement" in governance
    assert "cross-section cannot establish ordering" in requirement.follow_up_note


def test_restricted_access_notes_follow_up_may_be_unavailable():
    requirement = requirement_for(blocked(Reachability.NEEDS_RESTRICTED_ACCESS), replicates=200)
    assert "secure environment" in requirement.design_needed
    assert "licence" in " ".join(requirement.governance_needed)


def test_higher_attrition_inflates_the_required_sample():
    low = requirement_for(
        blocked(Reachability.NEEDS_PRIMARY_COLLECTION), attrition_fraction=0.1, replicates=200
    )
    high = requirement_for(
        blocked(Reachability.NEEDS_PRIMARY_COLLECTION), attrition_fraction=0.5, replicates=200
    )
    assert high.participants_required["OR_1.3"] > low.participants_required["OR_1.3"]


def test_clustering_inflates_the_required_sample():
    flat = requirement_for(blocked(Reachability.NEEDS_PRIMARY_COLLECTION), replicates=200)
    clustered = requirement_for(
        blocked(Reachability.NEEDS_PRIMARY_COLLECTION),
        cluster_size=20,
        intraclass_correlation=0.05,
        replicates=200,
    )
    assert clustered.participants_required["OR_1.3"] > flat.participants_required["OR_1.3"]


def test_only_blocked_propositions_are_priced():
    results = [blocked(Reachability.NEEDS_PRIMARY_COLLECTION), open_testable_item()]
    priced = requirements_for_blocked(results, replicates=200)
    assert [item.proposition_id for item in priced] == ["P1"]


def test_a_shared_cohort_is_smaller_than_the_sum_of_separate_ones():
    """The propositions share a design, so they can share participants.

    Pricing them separately overstates the cost by more than an order of magnitude, which
    is the difference between an unfundable programme and one cohort study.
    """

    results = [
        blocked(Reachability.NEEDS_PRIMARY_COLLECTION, f"P{index}") for index in range(25)
    ]
    priced = requirements_for_blocked(results, replicates=200)
    separate = sum(item.participants_required["OR_1.3"] for item in priced)
    shared = max(item.participants_required["OR_1.3"] for item in priced)
    assert shared * 10 < separate
