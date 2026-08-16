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


# ----------------------------------------------------------------- documented claims
#
# `assess_release` takes a KernelResult, because the release standard is written for
# results the engine produced. Most of what this project has actually asserted in public
# lives in markdown, produced by a script, with no KernelResult behind it at all. Those
# assertions are the ones at risk of overclaiming, so they need to reach the same gate.
#
# The rule below is the whole point: a documented claim with no persisted result behind it
# is REFUSED, not waved through with a synthesised result. Manufacturing a KernelResult to
# satisfy the gate would defeat the gate.


class ClaimTierNotDeclaredError(ValueError):
    """Raised when a claim is submitted without a tier and the caller wanted a tier back.

    There is no sensible default tier. Every candidate is wrong in a different direction:
    the lowest tier passes prose that should have been challenged at the tier the author
    actually meant, and the highest tier fails everything and trains the reader to ignore
    it. So an undeclared tier is a refusal, and the refusal names itself.
    """


@dataclass(frozen=True)
class ClaimSubmission:
    """One assertion this project has made in prose, with where its tier came from.

    `declared_tier` is `None` when the source document states no tier. That is recorded and
    refused rather than filled in, because the gap is the finding: a document making
    substantive claims without declaring what tier it is claiming at has not been through
    this control, and no scan of its wording can tell you whether it passed.
    """

    claim_ref: str
    source_document: str
    wording: str
    declared_tier: ClaimTier | None
    tier_source: str
    result_id: str | None = None
    lanes_searched: frozenset[EvidenceLane] = frozenset()


@dataclass(frozen=True)
class DocumentedClaimAssessment:
    claim_ref: str
    source_document: str
    declared_tier: ClaimTier | None
    tier_source: str
    released: bool
    failures: list[str] = field(default_factory=list)
    wording_check: WordingCheck | None = None
    advisory_tier: ClaimTier | None = None
    advisory_prohibited_hits: list[str] = field(default_factory=list)
    claim: ReleasedClaim | None = None

    def as_record(self) -> dict[str, object]:
        return {
            "claim_ref": self.claim_ref,
            "source_document": self.source_document,
            "declared_tier": self.declared_tier.value if self.declared_tier else None,
            "tier_source": self.tier_source,
            "released": self.released,
            "failures": list(self.failures),
            "wording_acceptable": (
                self.wording_check.acceptable if self.wording_check else None
            ),
            "prohibited_hits": (
                list(self.wording_check.prohibited_hits) if self.wording_check else []
            ),
            "advisory_tier": self.advisory_tier.value if self.advisory_tier else None,
            "advisory_prohibited_hits": list(self.advisory_prohibited_hits),
            "claim_id": self.claim.claim_id if self.claim else None,
        }


def assess_documented_claim(
    submission: ClaimSubmission,
    *,
    result: KernelResult | None = None,
    evidence: list[EvidenceObject] | None = None,
    human_review: HumanReviewRecord | AIMethodologicalReview | str | None = None,
    advisory_tier: ClaimTier | None = None,
) -> DocumentedClaimAssessment:
    """Put a documented assertion through the release gate, refusing on every gap.

    Three distinct outcomes, kept distinct on purpose:

    * **tier undeclared** - refused with ``CLAIM_TIER_NOT_DECLARED``. A wording scan may
      still be run at ``advisory_tier`` and is reported separately, clearly marked as
      advisory, so it can never be mistaken for a verdict the claim actually cleared.
    * **tier declared, no persisted result** - the wording check is a real verdict at the
      declared tier, and release is refused with ``NO_PERSISTED_RESULT_FOR_CLAIM``.
    * **tier declared and a result exists** - the full nine-gate ``assess_release`` runs.
    """

    failures: list[str] = []
    wording_check: WordingCheck | None = None
    advisory_hits: list[str] = []

    if submission.declared_tier is None:
        failures.append("CLAIM_TIER_NOT_DECLARED")
        if advisory_tier is not None:
            advisory_hits = check_wording(submission.wording, advisory_tier).prohibited_hits
        return DocumentedClaimAssessment(
            claim_ref=submission.claim_ref,
            source_document=submission.source_document,
            declared_tier=None,
            tier_source=submission.tier_source,
            released=False,
            failures=failures,
            advisory_tier=advisory_tier,
            advisory_prohibited_hits=advisory_hits,
        )

    wording_check = check_wording(submission.wording, submission.declared_tier)
    if not wording_check.acceptable:
        failures.append(f"WORDING_EXCEEDS_CLAIM_TIER:{','.join(wording_check.prohibited_hits)}")

    if result is None:
        failures.append("NO_PERSISTED_RESULT_FOR_CLAIM")
        return DocumentedClaimAssessment(
            claim_ref=submission.claim_ref,
            source_document=submission.source_document,
            declared_tier=submission.declared_tier,
            tier_source=submission.tier_source,
            released=False,
            failures=failures,
            wording_check=wording_check,
        )

    if result.claim_tier is not submission.declared_tier:
        failures.append(
            f"DECLARED_TIER_DISAGREES_WITH_RESULT:{submission.declared_tier.value}"
            f"!={result.claim_tier.value}"
        )

    decision = assess_release(
        result=result,
        evidence=evidence or [],
        wording=submission.wording,
        human_review=human_review,
        counterevidence_lanes_searched=set(submission.lanes_searched),
    )
    for failure in decision.failures:
        if failure not in failures:
            failures.append(failure)

    return DocumentedClaimAssessment(
        claim_ref=submission.claim_ref,
        source_document=submission.source_document,
        declared_tier=submission.declared_tier,
        tier_source=submission.tier_source,
        released=decision.released and not failures,
        failures=failures,
        wording_check=wording_check,
        claim=decision.claim if decision.released and not failures else None,
    )
