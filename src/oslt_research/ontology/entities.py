from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from oslt_research.domain.enums import SourceStatus
from oslt_research.domain.models import ProvenanceRecord


class SystemDomain(StrEnum):
    """The social system an entity primarily operates in.

    MD15 (structural coupling) predicts cross-system diffusion between *independent*
    nodes. Recording the domain is what allows a coupling claim to be distinguished
    from movement inside a single system.
    """

    ACADEMIC = "ACADEMIC"
    POLICY = "POLICY"
    ADVOCACY = "ADVOCACY"
    CLINICAL = "CLINICAL"
    REGULATORY = "REGULATORY"
    PHILANTHROPIC = "PHILANTHROPIC"
    DIGITAL = "DIGITAL"
    COMMERCIAL = "COMMERCIAL"
    #: Domain genuinely not determinable from the source. Never counted towards
    #: cross-system spread: guessing a domain would fabricate the diffusion MD15 tests for.
    UNKNOWN = "UNKNOWN"


class EntityRole(StrEnum):
    """Role an entity plays in a mechanism, not an identity attribute.

    The registry propositions are about institutional function. Roles are typed so a
    released finding can speak about 'philanthropic funder -> advocacy organisation'
    without the claim depending on which named body occupied the role.
    """

    PUBLIC_FUNDER = "PUBLIC_FUNDER"
    PHILANTHROPIC_FUNDER = "PHILANTHROPIC_FUNDER"
    COMMISSIONER = "COMMISSIONER"
    PROVIDER = "PROVIDER"
    ADVOCACY_ORGANISATION = "ADVOCACY_ORGANISATION"
    PROFESSIONAL_BODY = "PROFESSIONAL_BODY"
    GUIDELINE_BODY = "GUIDELINE_BODY"
    REGULATOR = "REGULATOR"
    ACADEMIC_BODY = "ACADEMIC_BODY"
    PUBLISHER = "PUBLISHER"
    GOVERNMENT_DEPARTMENT = "GOVERNMENT_DEPARTMENT"
    #: A human being holding an office or controlling interest. Distinguished from
    #: OTHER so that a personnel node is never mistaken for an unclassified organisation.
    #: Being a person is not by itself evidence of anything; the tie is.
    NATURAL_PERSON = "NATURAL_PERSON"
    OTHER = "OTHER"


class RelationType(StrEnum):
    FUNDS = "FUNDS"
    GRANTS_TO = "GRANTS_TO"
    COMMISSIONS = "COMMISSIONS"
    CONTRACTS_WITH = "CONTRACTS_WITH"
    SUBCONTRACTS_TO = "SUBCONTRACTS_TO"
    ISSUES_GUIDANCE_TO = "ISSUES_GUIDANCE_TO"
    ADVISES = "ADVISES"
    ADOPTS_POLICY_FROM = "ADOPTS_POLICY_FROM"
    AFFILIATED_WITH = "AFFILIATED_WITH"
    COORDINATES_WITH = "COORDINATES_WITH"
    #: A named person holds a directorship/secretaryship at an organisation
    #: (Companies House officer appointment). Distinct from AFFILIATED_WITH, which
    #: carries no statement about office.
    HOLDS_OFFICE_AT = "HOLDS_OFFICE_AT"
    #: A person or body exercises significant control over an organisation
    #: (Companies House PSC register).
    CONTROLS = "CONTROLS"


#: Identifier namespaces strong enough to merge two records into one entity.
#:
#: `ch_officer_id` and `ch_psc_id` are register-issued identifiers minted by Companies
#: House, not names. Admitting them lets one human being appearing at two companies
#: become one node -- which WIDENS what can count as a bridge and therefore makes the
#: MX09 disposition EASIER to overturn, not harder. It admits no name-based merge:
#: `strong_identifiers()` reads identifier namespaces only, and two people with
#: identical names but different officer ids remain two entities at this tier.
#: The two namespaces are mutually non-interchangeable: an officer id never equals a
#: PSC id, so a director is never silently fused with a PSC record.
STRONG_IDENTIFIER_NAMESPACES = frozenset(
    {
        "companies_house",
        "charity_number",
        "ror",
        "grid",
        "oc_id",
        "lei",
        "ch_officer_id",
        "ch_psc_id",
    }
)


def normalise_name(name: str) -> str:
    """Fold an organisation name for weak matching.

    Deliberately conservative: casefold, strip punctuation and drop common legal and
    stopword suffixes. Weak matches never merge entities on their own.
    """

    cleaned = "".join(character if character.isalnum() else " " for character in name)
    dropped = {
        "the", "ltd", "limited", "llp", "plc", "inc", "cic", "trust",
        "foundation", "charity", "charitable", "uk", "and",
    }
    tokens = [token for token in cleaned.casefold().split() if token and token not in dropped]
    return " ".join(tokens)


class InstitutionalEntity(BaseModel):
    """A role-typed organisational node carrying its own provenance."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    roles: list[EntityRole] = Field(min_length=1)
    system_domain: SystemDomain
    jurisdiction: str = Field(min_length=1)
    identifiers: dict[str, str] = Field(default_factory=dict)
    provenance: ProvenanceRecord
    source_status: SourceStatus = SourceStatus.UNVERIFIED
    dependency_family: str = Field(min_length=1)
    admitted: bool = False
    admission_failures: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def strong_identifiers(self) -> set[tuple[str, str]]:
        return {
            (namespace, value.strip().casefold())
            for namespace, value in self.identifiers.items()
            if namespace in STRONG_IDENTIFIER_NAMESPACES and value.strip()
        }

    def normalised_name(self) -> str:
        return normalise_name(self.canonical_name)


class InstitutionalRelation(BaseModel):
    """A typed, dated, independently-sourced edge between two entities.

    Every edge carries its own provenance and dependency family. Two edges asserted by
    the same document share a family and therefore cannot corroborate one another.
    """

    model_config = ConfigDict(extra="forbid")

    relation_id: str = Field(min_length=1)
    source_entity_id: str = Field(min_length=1)
    target_entity_id: str = Field(min_length=1)
    relation_type: RelationType
    valid_from: date | None = None
    valid_to: date | None = None
    amount_gbp: float | None = Field(default=None, ge=0)
    provenance: ProvenanceRecord
    source_status: SourceStatus = SourceStatus.UNVERIFIED
    dependency_family: str = Field(min_length=1)
    admitted: bool = False
    admission_failures: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_interval_and_self_loop(self) -> "InstitutionalRelation":
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot precede valid_from")
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("relation cannot be a self-loop")
        return self

    def is_dated(self) -> bool:
        return self.valid_from is not None

    def precedes(self, outcome: date) -> bool:
        """True only when the tie is dated and demonstrably starts before `outcome`.

        Undated edges return False. MD10 requires temporally ordered transfer, so an
        edge with no start date cannot contribute to a precedence claim.
        """

        return self.valid_from is not None and self.valid_from < outcome
