from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from oslt_research.domain.enums import AccessClass, EpistemicStatus, EvidenceLane, SourceStatus
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.provenance import admit_evidence, sha256_text


def make_evidence(access=AccessClass.OPEN, *, status=SourceStatus.VERIFIED, licence=None):
    content = "evidence content"
    return EvidenceObject(
        evidence_id="EV-1",
        proposition_ids=["MD11"],
        lane=EvidenceLane.SUPPORT,
        source_status=status,
        epistemic_status=EpistemicStatus.OBSERVATION,
        title="Title",
        content=content,
        provenance=ProvenanceRecord(
            source_id="DS033",
            source_uri="https://example.test/1",
            retrieved_at=datetime.now(timezone.utc),
            checksum_sha256="a" * 64,
            access_class=access,
            licence_or_approval=licence,
        ),
        dependency_family="doi:10.1/example",
        metadata={"content_sha256": sha256_text(content)},
    )


def test_open_verified_evidence_is_admitted():
    admitted = admit_evidence(make_evidence())
    assert admitted.admitted
    assert admitted.admission_failures == []


def test_unverified_source_is_rejected():
    rejected = admit_evidence(make_evidence(status=SourceStatus.UNVERIFIED))
    assert not rejected.admitted
    assert "SOURCE_STATUS_UNVERIFIED" in rejected.admission_failures


def test_licensed_and_tre_require_approval():
    licensed = admit_evidence(make_evidence(AccessClass.LICENSED))
    assert "LICENCE_OR_APPROVAL_MISSING" in licensed.admission_failures
    tre = admit_evidence(make_evidence(AccessClass.TRE_SDE))
    assert "TRE_APPROVAL_MISSING" in tre.admission_failures


def test_tre_raw_payload_fails_model_validation():
    item = make_evidence(AccessClass.TRE_SDE, licence="APPROVED")
    with pytest.raises(ValidationError, match="TRE/SDE raw person-level payload"):
        EvidenceObject(**{**item.model_dump(), "raw_person_level_payload_included": True})


def test_content_hash_mismatch_is_rejected():
    item = make_evidence().model_copy(update={"metadata": {"content_sha256": "0" * 64}})
    rejected = admit_evidence(item)
    assert "CONTENT_HASH_MISMATCH" in rejected.admission_failures
