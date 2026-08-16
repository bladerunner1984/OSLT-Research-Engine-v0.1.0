from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    AccessClass,
    AuthorityLevel,
    ClaimTier,
    EpistemicStatus,
    EvidenceLane,
    FalsifierStatus,
    FindingDirection,
    LaneCodingMethod,
    ModelFamily,
    SourceStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScopeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    construct_name: str = Field(alias="construct", serialization_alias="construct", min_length=1)
    population: str = Field(min_length=1)
    period: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    estimand: str = Field(min_length=1)

    def comparison_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.construct_name.strip().casefold(),
            self.population.strip().casefold(),
            self.period.strip().casefold(),
            self.jurisdiction.strip().casefold(),
            self.estimand.strip().casefold(),
        )


class ProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    retrieved_at: datetime = Field(default_factory=utc_now)
    published_at: str | None = None
    source_version: str | None = None
    retrieval_query: str | None = None
    field_or_document_locator: str | None = None
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    access_class: AccessClass = AccessClass.OPEN
    licence_or_approval: str | None = None
    transformation_ids: list[str] = Field(default_factory=list)
    codebook_or_schema_ref: str | None = None


class LaneCoding(BaseModel):
    """Provenance for a record's EvidenceLane: who coded it, how sure, and on what cues.

    The lane alone is not enough. A lane set by a regex screening pass carries
    A5_MODEL_PROPOSAL authority and is a proposal; a lane set by a named human coder
    carries A2_HUMAN_GOVERNANCE_DECISION and is a decision. Collapsing the two would
    silently corrupt the inter-rater-reliability machinery, which compares coders and
    therefore has to be able to tell them apart.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    method: LaneCodingMethod
    confidence: float = Field(ge=0, le=1)
    matched_signals: list[str] = Field(default_factory=list)
    rationale: str = ""
    requires_human_adjudication: bool = True
    coder_ref: str | None = Field(
        default=None,
        description="Classifier version or the human coder's name; unattributed coding is not a code",
    )
    coded_at: datetime = Field(default_factory=utc_now)

    @property
    def authority_level(self) -> AuthorityLevel:
        """A classifier proposes; only a human coder decides."""

        if self.method is LaneCodingMethod.HUMAN_CODER:
            return AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION
        if self.method is LaneCodingMethod.SOURCE_DECLARED:
            return AuthorityLevel.A3_VERIFIED_EVIDENCE_COMPUTATION
        return AuthorityLevel.A5_MODEL_PROPOSAL

    @property
    def is_verified_code(self) -> bool:
        return self.method is LaneCodingMethod.HUMAN_CODER


class EvidenceObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    proposition_ids: list[str] = Field(default_factory=list)
    lane: EvidenceLane = EvidenceLane.UNCLASSIFIED
    lane_coding: LaneCoding | None = None
    source_status: SourceStatus = SourceStatus.UNVERIFIED
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVATION
    title: str = Field(min_length=1)
    content: str = ""
    provenance: ProvenanceRecord
    dependency_family: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_person_level_payload_included: bool = False
    admitted: bool = False
    admission_failures: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def protect_controlled_data_boundary(self) -> "EvidenceObject":
        if (
            self.provenance.access_class == AccessClass.TRE_SDE
            and self.raw_person_level_payload_included
        ):
            raise ValueError("TRE/SDE raw person-level payload cannot cross into OSLT")
        return self


class HypothesisProposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposition_id: str
    model_family: ModelFamily
    domain: str
    statement: str
    prediction: str
    falsifier: str
    required_workstreams: list[str]
    primary_outcome_construct: str
    temporal_requirement: str
    maximum_claim_state: ClaimTier
    status: str


class CertaintyVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statistical_precision: float = Field(ge=0, le=1)
    measurement_validity: float = Field(ge=0, le=1)
    temporal_ordering: float = Field(ge=0, le=1)
    causal_identification: float = Field(ge=0, le=1)
    confounding_control: float = Field(ge=0, le=1)
    selection_bias_control: float = Field(ge=0, le=1)
    missing_data_robustness: float = Field(ge=0, le=1)
    specification_stability: float = Field(ge=0, le=1)
    source_independence: float = Field(ge=0, le=1)
    cross_method_convergence: float = Field(ge=0, le=1)
    replication: float = Field(ge=0, le=1)
    transportability: float = Field(ge=0, le=1)
    publication_selection_control: float = Field(ge=0, le=1)
    provenance_completeness: float = Field(ge=0, le=1)
    theory_independence: float = Field(ge=0, le=1)
    explanatory_contribution: float = Field(ge=0, le=1)

    def minimum(self) -> tuple[str, float]:
        values = self.model_dump()
        name = min(values, key=values.__getitem__)
        return name, float(values[name])

    def mean(self) -> float:
        values = list(self.model_dump().values())
        return float(sum(values) / len(values))


class KernelResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str
    run_id: str
    proposition_id: str
    kernel_name: str
    model_family: ModelFamily
    scope: ScopeContext
    finding_direction: FindingDirection
    epistemic_status: EpistemicStatus
    effect_estimate: float | None = None
    uncertainty: str
    certainty: CertaintyVector
    evidence_ids: list[str]
    counterevidence_ids: list[str] = Field(default_factory=list)
    dependency_families: list[str] = Field(default_factory=list)
    falsifier_status: FalsifierStatus = FalsifierStatus.NOT_TESTED
    model_impacts: dict[str, float] = Field(default_factory=dict)
    claim_tier: ClaimTier
    narrative: str
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("model_impacts")
    @classmethod
    def validate_impacts(cls, value: dict[str, float]) -> dict[str, float]:
        for family, impact in value.items():
            if family not in {member.value for member in ModelFamily}:
                raise ValueError(f"unknown model family in model_impacts: {family}")
            if impact < -1 or impact > 1:
                raise ValueError("model impact must be between -1 and 1")
        return value


class ContradictionAssessment(BaseModel):
    left_result_id: str
    right_result_id: str
    classification: str
    explanation: str


class SynthesisOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    synthesis_id: str
    run_id: str
    included_result_ids: list[str]
    excluded_result_ids: list[str]
    comparative_support_index: dict[str, float]
    leading_models: list[str]
    unresolved_contradictions: list[ContradictionAssessment]
    limiting_dimension: str
    limiting_score: float = Field(ge=0, le=1)
    claim_tier: ClaimTier
    bounded_conclusion: str
    human_review_required: bool
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    objective: str
    proposition_ids: list[str]
    preregistration_ref: str | None = None
    repository_commit: str
    constitution_hash: str
    configuration_hashes: dict[str, str]
    registry_hashes: dict[str, str]
    data_or_corpus_hashes: dict[str, str]
    connector_versions: dict[str, str]
    model_gateway: str
    model_versions: dict[str, str] = Field(default_factory=dict)
    prompt_hashes: dict[str, str] = Field(default_factory=dict)
    environment: dict[str, str] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class FilmSceneRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str
    narrated_claim: str
    released_claim_id: str
    evidence_ids: list[str]
    counterevidence_ids: list[str]
    certainty_label: str
    permitted_wording: list[str]
    prohibited_wording: list[str]
    uncertainty_disclosure: str
    human_review_reference: str
    visual_source_ids: list[str] = Field(default_factory=list)


class ReleasedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    proposition_id: str
    wording: str
    epistemic_status: EpistemicStatus
    claim_tier: ClaimTier
    evidence_ids: list[str]
    counterevidence_ids: list[str]
    dependency_families: list[str]
    certainty: CertaintyVector
    permitted_phrases: list[str]
    prohibited_phrases: list[str]
    uncertainty_disclosure: str
    human_review_reference: str
    release_manifest_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
