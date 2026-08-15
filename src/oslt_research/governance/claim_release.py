from __future__ import annotations

import re
from dataclasses import dataclass, field

from oslt_research.domain.enums import ClaimTier, EpistemicStatus, EvidenceLane
from oslt_research.domain.models import (
    CertaintyVector,
    EvidenceObject,
    KernelResult,
    ReleasedClaim,
)
from oslt_research.evidence.provenance import canonical_json_hash
from oslt_research.governance.review_records import AIMethodologicalReview, HumanReviewRecord


#: Wording permitted and forbidden at each tier. The prohibitions are the operative
#: half: a claim tier that does not constrain language is decorative, because the
#: overstatement happens in the sentence, not in the metadata.
TIER_WORDING: dict[ClaimTier, tuple[tuple[str, ...], tuple[str, ...]]] = {
    ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY: (
        ("the records show", "we observed", "in this corpus", "descriptively"),
        ("causes", "caused by", "leads to", "drives", "because of", "explains",
         "predicts", "associated with", "linked to", "effect of", "impact of",
         "proves", "demonstrates that"),
    ),
    ClaimTier.ASSOCIATION_ONLY: (
        ("associated with", "correlated with", "co-occurs with", "in this sample"),
        ("causes", "caused by", "leads to", "drives", "because of", "the effect of",
         "responsible for", "proves", "demonstrates that", "explains why"),
    ),
    ClaimTier.LIMITED_CAUSAL_EVIDENCE: (
        ("is consistent with a causal contribution", "may contribute to",
         "provides limited evidence that", "under the stated design"),
        ("proves", "demonstrates that", "establishes that", "definitively",
         "conclusively", "shows that X causes"),
    ),
    ClaimTier.MODERATE_TRIANGULATED_CAUSAL_EVIDENCE: (
        ("triangulated evidence indicates", "moderate evidence that",
         "converging designs suggest"),
        ("proves", "definitively", "conclusively", "beyond doubt"),
    ),
    ClaimTier.HIGH_TRIANGULATED_CAUSAL_EVIDENCE: (
        ("strong triangulated evidence that", "robust across designs"),
        ("proves", "beyond doubt", "certain", "irrefutable"),
    ),
    ClaimTier.THEORY_DEPENDENT_INTERPRETATION: (
        ("on this theoretical reading", "interpreted within this framework"),
        ("proves", "demonstrates that", "shows objectively", "the data show"),
    ),
    ClaimTier.SIMULATION_ONLY: (
        ("under the stated assumptions the model implies",
         "in simulation", "the design would detect"),
        ("we found", "the evidence shows", "in reality", "observed",
         "proves", "demonstrates that", "causes"),
    ),
}

#: Lanes that must have been searched before any claim is released. The constitution
#: makes counterevidence mandatory, so a claim built without looking is not releasable
#: however strong its supporting evidence looks.
REQUIRED_COUNTEREVIDENCE_LANES = (
    EvidenceLane.CONTRADICT,
    EvidenceLane.RIVAL,
    EvidenceLane.NULL,
)


@dataclass(frozen=True)
class ReleaseDecision:
    released: bool
    failures: list[str] = field(default_factory=list)
    claim: ReleasedClaim | None = None


@dataclass(frozen=True)
class WordingCheck:
    acceptable: bool
    prohibited_hits: list[str] = field(default_factory=list)
    tier: ClaimTier = ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY


def wording_for(tier: ClaimTier) -> tuple[list[str], list[str]]:
    permitted, prohibited = TIER_WORDING[tier]
    return list(permitted), list(prohibited)


def check_wording(text: str, tier: ClaimTier) -> WordingCheck:
    """Scan drafted prose for language the claim tier does not license.

    Intended for the film and public-communication path, where the gap between what was
    established and what gets narrated is where overstatement enters.
    """

    _, prohibited = wording_for(tier)
    hits = [
        phrase
        for phrase in prohibited
        if re.search(rf"\b{re.escape(phrase)}", text, re.I)
    ]
    return WordingCheck(acceptable=not hits, prohibited_hits=hits, tier=tier)


def assess_release(
    *,
    result: KernelResult,
    evidence: list[EvidenceObject],
    wording: str,
    human_review: HumanReviewRecord | AIMethodologicalReview | str | None = None,
    counterevidence_lanes_searched: set[EvidenceLane] | None = None,
) -> ReleaseDecision:
    """Assemble a ReleasedClaim, or refuse and say which of the nine gates failed.

    Implements docs/governance/CLAIM_RELEASE_STANDARD.md. Refusal is the default: every
    gate must be positively satisfied, and a missing counterevidence search or an absent
    human review reference blocks release regardless of how good the evidence is.
    """

    failures: list[str] = []
    searched = counterevidence_lanes_searched or set()

    # 1-2. proposition, scope, evidence ids and dependency families
    if not result.proposition_id:
        failures.append("PROPOSITION_ID_MISSING")
    if not result.evidence_ids:
        failures.append("EVIDENCE_IDS_MISSING")
    if not result.dependency_families:
        failures.append("DEPENDENCY_FAMILIES_MISSING")

    known = {item.evidence_id for item in evidence}
    dangling = [item for item in result.evidence_ids if item not in known]
    if dangling:
        failures.append(f"EVIDENCE_IDS_NOT_RESOLVABLE:{len(dangling)}")

    unadmitted = [item.evidence_id for item in evidence if not item.admitted]
    if unadmitted:
        failures.append(f"UNADMITTED_EVIDENCE_PRESENT:{len(unadmitted)}")

    # 3. counterevidence and null-lane search status
    missing_lanes = [lane.value for lane in REQUIRED_COUNTEREVIDENCE_LANES if lane not in searched]
    if missing_lanes:
        failures.append(f"COUNTEREVIDENCE_LANES_NOT_SEARCHED:{','.join(missing_lanes)}")

    # 5. certainty vector and limiting dimension
    limiting_name, limiting_score = result.certainty.minimum()

    # 7. approved wording within the tier
    check = check_wording(wording, result.claim_tier)
    if not check.acceptable:
        failures.append(f"WORDING_EXCEEDS_CLAIM_TIER:{','.join(check.prohibited_hits)}")

    # 9. human review where triggered.
    #
    # A bare string used to satisfy this, which meant the last gate in the system could be
    # cleared by typing anything into it. It now requires a HumanReviewRecord carrying a
    # named reviewer, their capacity and a decision. An AIMethodologicalReview is refused
    # by type: a model review is A5_MODEL_PROPOSAL and this gate needs
    # A2_HUMAN_GOVERNANCE_DECISION.
    human_review_reference = ""
    if isinstance(human_review, AIMethodologicalReview):
        failures.append("AI_REVIEW_CANNOT_SATISFY_HUMAN_REVIEW_GATE")
    elif isinstance(human_review, HumanReviewRecord):
        if not human_review.can_authorise_release:
            failures.append(f"HUMAN_REVIEW_DECISION_{human_review.decision.value}")
        else:
            human_review_reference = human_review.review_id
    elif isinstance(human_review, str) and human_review.strip():
        failures.append("HUMAN_REVIEW_REFERENCE_NOT_A_REVIEW_RECORD")
    else:
        failures.append("HUMAN_REVIEW_RECORD_MISSING")

    if failures:
        return ReleaseDecision(released=False, failures=failures)

    permitted, prohibited = wording_for(result.claim_tier)
    manifest = {
        "proposition_id": result.proposition_id,
        "result_id": result.result_id,
        "run_id": result.run_id,
        "scope": result.scope.model_dump(mode="json"),
        "claim_tier": result.claim_tier.value,
        "epistemic_status": result.epistemic_status.value,
        "evidence_ids": sorted(result.evidence_ids),
        "counterevidence_ids": sorted(result.counterevidence_ids),
        "dependency_families": sorted(result.dependency_families),
        "certainty": result.certainty.model_dump(),
        "wording": wording,
        "human_review_reference": human_review_reference,
    }

    claim = ReleasedClaim(
        claim_id=f"CLAIM-{result.result_id}",
        proposition_id=result.proposition_id,
        wording=wording,
        epistemic_status=result.epistemic_status,
        claim_tier=result.claim_tier,
        evidence_ids=result.evidence_ids,
        counterevidence_ids=result.counterevidence_ids,
        dependency_families=result.dependency_families,
        certainty=result.certainty,
        permitted_phrases=permitted,
        prohibited_phrases=prohibited,
        uncertainty_disclosure=(
            f"Claim tier {result.claim_tier.value}. The limiting certainty dimension is "
            f"{limiting_name} at {limiting_score:.2f}; the weakest dimension governs the "
            f"tier and strength elsewhere cannot compensate for it. Evidence rests on "
            f"{len(result.dependency_families)} dependency famil"
            f"{'y' if len(result.dependency_families) == 1 else 'ies'}. "
            "This is a population-level research object and assigns no cause to any "
            "individual."
        ),
        human_review_reference=human_review_reference,
        release_manifest_hash=canonical_json_hash(manifest),
    )
    return ReleaseDecision(released=True, claim=claim)
