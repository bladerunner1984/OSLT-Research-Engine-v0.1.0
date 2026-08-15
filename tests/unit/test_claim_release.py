from __future__ import annotations

from datetime import date

import pytest

from oslt_research.domain.enums import AccessClass, ClaimTier, EvidenceLane
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.provenance import admit_evidence
from oslt_research.governance.review_records import (
    AIMethodologicalReview,
    HumanReviewRecord,
    ReviewDecision,
)
from oslt_research.governance.claim_release import (
    REQUIRED_COUNTEREVIDENCE_LANES,
    assess_release,
    check_wording,
    wording_for,
)


ALL_LANES = set(REQUIRED_COUNTEREVIDENCE_LANES)


def make_evidence(evidence_id: str, admitted: bool = True) -> EvidenceObject:
    from oslt_research.domain.enums import SourceStatus

    item = EvidenceObject(
        evidence_id=evidence_id,
        title="A study",
        provenance=ProvenanceRecord(
            source_id="SRC",
            source_uri=f"https://example.org/{evidence_id}",
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        source_status=SourceStatus.VERIFIED if admitted else SourceStatus.UNVERIFIED,
        dependency_family="fam-1",
    )
    return admit_evidence(item)


APPROVED_REVIEW = HumanReviewRecord(
    review_id="HR-2026-001",
    claim_or_result_ref="KR-1",
    reviewer_name="A Methodologist",
    reviewer_role="Independent statistical reviewer",
    decision=ReviewDecision.APPROVED,
    reviewed_on=date(2026, 8, 15),
)


def release(result_factory, **overrides):
    defaults = dict(
        result=result_factory(),
        evidence=[make_evidence("EV-KR-1")],
        wording="Referral counts are associated with service capacity in this sample.",
        human_review=APPROVED_REVIEW,
        counterevidence_lanes_searched=ALL_LANES,
    )
    defaults.update(overrides)
    return assess_release(**defaults)


# ----------------------------------------------------------------- tier wording


def test_causal_language_is_prohibited_at_association_only():
    check = check_wording("Service capacity causes referral growth", ClaimTier.ASSOCIATION_ONLY)
    assert not check.acceptable
    assert "causes" in check.prohibited_hits


def test_association_language_is_prohibited_at_descriptive_only():
    check = check_wording(
        "Referrals were associated with capacity", ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY
    )
    assert not check.acceptable


def test_empirical_language_is_prohibited_at_simulation_only():
    """A simulation may not say 'we found' - it did not find anything about the world."""

    check = check_wording("We found a large selection effect", ClaimTier.SIMULATION_ONLY)
    assert not check.acceptable
    assert "we found" in check.prohibited_hits


def test_every_tier_defines_both_permitted_and_prohibited_wording():
    for tier in ClaimTier:
        permitted, prohibited = wording_for(tier)
        assert permitted and prohibited


def test_acceptable_wording_passes():
    assert check_wording(
        "Referrals were associated with capacity in this sample", ClaimTier.ASSOCIATION_ONLY
    ).acceptable


# --------------------------------------------------------------- release gating


def test_clean_case_releases_a_claim(result_factory):
    decision = release(result_factory)
    assert decision.released, decision.failures
    claim = decision.claim
    assert claim is not None
    assert claim.release_manifest_hash and len(claim.release_manifest_hash) == 64
    assert claim.permitted_phrases and claim.prohibited_phrases
    assert "assigns no cause to any individual" in claim.uncertainty_disclosure


def test_unsearched_counterevidence_lanes_block_release(result_factory):
    decision = release(result_factory, counterevidence_lanes_searched={EvidenceLane.NULL})
    assert not decision.released
    assert any("COUNTEREVIDENCE_LANES_NOT_SEARCHED" in f for f in decision.failures)
    assert decision.claim is None


def test_no_counterevidence_search_at_all_blocks_release(result_factory):
    decision = release(result_factory, counterevidence_lanes_searched=set())
    assert not decision.released
    assert any("CONTRADICT" in f and "RIVAL" in f for f in decision.failures)


def test_missing_human_review_reference_blocks_release(result_factory):
    decision = release(result_factory, human_review=None)
    assert not decision.released
    assert "HUMAN_REVIEW_RECORD_MISSING" in decision.failures


def test_wording_above_the_tier_blocks_release(result_factory):
    decision = release(
        result_factory, wording="Service capacity causes the rise in referrals."
    )
    assert not decision.released
    assert any("WORDING_EXCEEDS_CLAIM_TIER" in f for f in decision.failures)


def test_unresolvable_evidence_ids_block_release(result_factory):
    decision = release(result_factory, evidence=[make_evidence("SOMETHING-ELSE")])
    assert not decision.released
    assert any("EVIDENCE_IDS_NOT_RESOLVABLE" in f for f in decision.failures)


def test_unadmitted_evidence_blocks_release(result_factory):
    decision = release(
        result_factory,
        evidence=[make_evidence("EV-KR-1"), make_evidence("EV-BAD", admitted=False)],
    )
    assert not decision.released
    assert any("UNADMITTED_EVIDENCE_PRESENT" in f for f in decision.failures)


def test_all_failures_are_reported_together_not_just_the_first(result_factory):
    decision = release(
        result_factory,
        wording="This proves capacity causes referrals.",
        human_review=None,
        counterevidence_lanes_searched=set(),
    )
    assert not decision.released
    assert len(decision.failures) >= 3


def test_release_manifest_hash_changes_with_wording(result_factory):
    first = release(result_factory, wording="Referrals were associated with capacity.")
    second = release(result_factory, wording="Referrals correlated with capacity here.")
    assert first.released and second.released
    assert first.claim.release_manifest_hash != second.claim.release_manifest_hash


def test_uncertainty_disclosure_names_the_limiting_dimension(
    result_factory, certainty_factory
):
    weak = certainty_factory(0.8, transportability=0.11)
    decision = release(result_factory, result=result_factory(certainty=weak))
    assert decision.released, decision.failures
    assert "transportability" in decision.claim.uncertainty_disclosure
    assert "0.11" in decision.claim.uncertainty_disclosure


# ------------------------------------------------- the human gate cannot be faked


def test_ai_review_cannot_satisfy_the_human_gate(result_factory):
    """Model agreement has zero evidential weight; the engine says so on every run."""

    ai = AIMethodologicalReview(
        review_id="AI-1",
        subject_ref="KR-1",
        model_name="some-model",
        prompt_hash="b" * 64,
        findings=["looks sound to me"],
    )
    decision = release(result_factory, human_review=ai)
    assert not decision.released
    assert "AI_REVIEW_CANNOT_SATISFY_HUMAN_REVIEW_GATE" in decision.failures
    assert ai.can_authorise_release is False


def test_a_bare_string_is_no_longer_accepted(result_factory):
    """The last gate used to be clearable by typing anything into it."""

    decision = release(result_factory, human_review="codex-review-123")
    assert not decision.released
    assert "HUMAN_REVIEW_REFERENCE_NOT_A_REVIEW_RECORD" in decision.failures


def test_a_rejected_human_review_blocks_release(result_factory):
    rejected = HumanReviewRecord(
        review_id="HR-2",
        claim_or_result_ref="KR-1",
        reviewer_name="A Methodologist",
        reviewer_role="Independent statistical reviewer",
        decision=ReviewDecision.REJECTED,
        reviewed_on=date(2026, 8, 15),
    )
    decision = release(result_factory, human_review=rejected)
    assert not decision.released
    assert "HUMAN_REVIEW_DECISION_REJECTED" in decision.failures


def test_approval_with_conditions_permits_release(result_factory):
    conditional = HumanReviewRecord(
        review_id="HR-3",
        claim_or_result_ref="KR-1",
        reviewer_name="A Methodologist",
        reviewer_role="Independent statistical reviewer",
        decision=ReviewDecision.APPROVED_WITH_CONDITIONS,
        reviewed_on=date(2026, 8, 15),
        conditions=["state the limiting dimension in any public wording"],
    )
    assert release(result_factory, human_review=conditional).released


def test_authority_levels_differ_by_three_steps():
    ai = AIMethodologicalReview(review_id="AI-1", subject_ref="x", model_name="m",
                                prompt_hash="c" * 64)
    human = HumanReviewRecord(review_id="HR-1", claim_or_result_ref="x",
                              reviewer_name="A Person", reviewer_role="Reviewer",
                              decision=ReviewDecision.APPROVED, reviewed_on=date(2026, 8, 15))
    assert human.authority_level > ai.authority_level
