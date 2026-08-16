from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from oslt_research.domain.enums import AuthorityLevel


#: Value recorded on a run manifest that was NOT bound to a frozen preregistration.
#:
#: A sentinel rather than ``None`` because an absent preregistration must be legible in the
#: store as an assertion ("this run was not preregistered") rather than as a missing field,
#: which reads identically to "nobody wired it up" - the exact ambiguity the wiring audit
#: found everywhere else.
NOT_PREREGISTERED = "NOT_PREREGISTERED"


PROTECTED_TYPES = {
    "SCIENTIFIC_CONSTITUTION",
    "CONSENT_DECISION",
    "ETHICS_DECISION",
    "LEGAL_BASIS_DECISION",
    "PREREGISTERED_SPECIFICATION",
    "RELEASE_DECISION",
}


class AuthorityError(RuntimeError):
    """Raised when a lower-authority actor attempts an impermissible mutation."""


@dataclass(frozen=True)
class AuthorityRecord:
    object_id: str
    object_type: str
    authority: AuthorityLevel
    value: Any


@dataclass(frozen=True)
class AuthorityPatch:
    object_id: str
    object_type: str
    proposer_authority: AuthorityLevel
    value: Any
    explicit_human_authorisation: bool = False


def apply_authority_patch(
    existing: AuthorityRecord | None,
    patch: AuthorityPatch,
) -> AuthorityRecord:
    """Apply one mutation through the canonical authority gate.

    The rule is intentionally simple and centralised: lower authority cannot overwrite higher
    authority. Protected object types additionally require explicit human authorisation unless the
    proposer is already A0/A1/A2.
    """

    if existing and patch.object_id != existing.object_id:
        raise AuthorityError("OBJECT_ID_MISMATCH")
    if existing and patch.object_type != existing.object_type:
        raise AuthorityError("OBJECT_TYPE_MISMATCH")
    if existing and patch.proposer_authority < existing.authority:
        raise AuthorityError("LOWER_AUTHORITY_OVERWRITE")

    if patch.object_type in PROTECTED_TYPES:
        sufficiently_high = patch.proposer_authority >= AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION
        if not sufficiently_high and not patch.explicit_human_authorisation:
            raise AuthorityError("PROTECTED_TYPE_REQUIRES_HUMAN_AUTHORISATION")

    return AuthorityRecord(
        object_id=patch.object_id,
        object_type=patch.object_type,
        authority=patch.proposer_authority,
        value=patch.value,
    )


def is_protected(object_type: str) -> bool:
    """Whether a mutation to this object type needs human authorisation to pass the lattice."""

    return object_type in PROTECTED_TYPES
