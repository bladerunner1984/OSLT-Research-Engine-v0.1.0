import pytest

from oslt_research.domain.enums import AuthorityLevel
from oslt_research.governance.authority import (
    AuthorityError,
    AuthorityPatch,
    AuthorityRecord,
    apply_authority_patch,
)


def test_higher_authority_can_update_lower_authority():
    existing = AuthorityRecord("x", "ANALYSIS", AuthorityLevel.A5_MODEL_PROPOSAL, {"a": 1})
    patch = AuthorityPatch("x", "ANALYSIS", AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION, {"a": 2})
    updated = apply_authority_patch(existing, patch)
    assert updated.value == {"a": 2}
    assert updated.authority == AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION


def test_lower_authority_cannot_overwrite_human_decision():
    existing = AuthorityRecord(
        "x", "ANALYSIS", AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION, {"a": 1}
    )
    patch = AuthorityPatch("x", "ANALYSIS", AuthorityLevel.A5_MODEL_PROPOSAL, {"a": 2})
    with pytest.raises(AuthorityError, match="LOWER_AUTHORITY_OVERWRITE"):
        apply_authority_patch(existing, patch)


def test_protected_type_requires_human_authorisation():
    patch = AuthorityPatch(
        "constitution",
        "SCIENTIFIC_CONSTITUTION",
        AuthorityLevel.A5_MODEL_PROPOSAL,
        {"rule": "changed"},
    )
    with pytest.raises(AuthorityError, match="PROTECTED_TYPE_REQUIRES_HUMAN_AUTHORISATION"):
        apply_authority_patch(None, patch)


def test_explicit_human_authorisation_allows_protected_proposal():
    patch = AuthorityPatch(
        "constitution",
        "SCIENTIFIC_CONSTITUTION",
        AuthorityLevel.A5_MODEL_PROPOSAL,
        {"rule": "proposed"},
        explicit_human_authorisation=True,
    )
    assert apply_authority_patch(None, patch).value == {"rule": "proposed"}


def test_mismatched_id_and_type_fail():
    existing = AuthorityRecord("x", "ANALYSIS", AuthorityLevel.A5_MODEL_PROPOSAL, {})
    with pytest.raises(AuthorityError, match="OBJECT_ID_MISMATCH"):
        apply_authority_patch(
            existing, AuthorityPatch("y", "ANALYSIS", AuthorityLevel.A5_MODEL_PROPOSAL, {})
        )
    with pytest.raises(AuthorityError, match="OBJECT_TYPE_MISMATCH"):
        apply_authority_patch(
            existing, AuthorityPatch("x", "OTHER", AuthorityLevel.A5_MODEL_PROPOSAL, {})
        )
