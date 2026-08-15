from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from oslt_research.governance.authority import AuthorityLevel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    REJECTED = "REJECTED"


class AIMethodologicalReview(BaseModel):
    """A model's review of method or code. Never a governance decision.

    Pinned to A5_MODEL_PROPOSAL. This is a genuinely useful artefact - a model is good at
    finding an unhandled branch, an unstated assumption, a metric that does not measure
    what it claims - and it should be recorded and acted on. What it cannot do is
    authorise a release.

    Three things in this repository say so independently: the authority lattice separates
    A5_MODEL_PROPOSAL from A2_HUMAN_GOVERNANCE_DECISION; the constitution bars
    `prestige_citation_count_and_model_agreement_not_truth_scores`; and every synthesis
    emits MODEL_AGREEMENT_HAS_ZERO_EVIDENTIAL_WEIGHT. A model review standing in for the
    human gate would make the engine print that warning and then rely on the thing it
    warns about.

    The practical reason matters more than the constitutional one: models share failure
    modes. A reviewer that reasons the same way as the author agrees with the author,
    confidently, including when both are wrong.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1, description="What was reviewed")
    model_name: str = Field(min_length=1)
    prompt_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    findings: list[str] = Field(default_factory=list)
    concerns_raised: list[str] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=utc_now)

    @property
    def authority_level(self) -> AuthorityLevel:
        return AuthorityLevel.A5_MODEL_PROPOSAL

    @property
    def can_authorise_release(self) -> bool:
        """Always False. Present so the answer is explicit rather than implied."""

        return False


class HumanReviewRecord(BaseModel):
    """An accountable person's governance decision on a specific claim.

    Carries A2_HUMAN_GOVERNANCE_DECISION. The required fields are the ones that make it
    accountable rather than ceremonial: who reviewed it, in what capacity, on what date,
    and what they decided. A reference with no name attached is not a review.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str = Field(min_length=1)
    claim_or_result_ref: str = Field(min_length=1)
    reviewer_name: str = Field(min_length=2)
    reviewer_role: str = Field(min_length=2, description="Capacity in which they reviewed")
    decision: ReviewDecision
    reviewed_on: date
    conditions: list[str] = Field(default_factory=list)
    triggers_considered: list[str] = Field(default_factory=list)
    ai_reviews_consulted: list[str] = Field(
        default_factory=list,
        description="AIMethodologicalReview ids that informed but did not make this decision",
    )

    @property
    def authority_level(self) -> AuthorityLevel:
        return AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION

    @property
    def can_authorise_release(self) -> bool:
        return self.decision in {
            ReviewDecision.APPROVED,
            ReviewDecision.APPROVED_WITH_CONDITIONS,
        }
