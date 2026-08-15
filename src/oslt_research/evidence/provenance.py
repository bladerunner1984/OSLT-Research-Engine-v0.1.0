from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import EvidenceObject


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


def canonical_json_hash(payload: Any) -> str:
    serialised = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_text(serialised)


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    failures: list[str]


def assess_evidence_admission(evidence: EvidenceObject) -> AdmissionDecision:
    failures: list[str] = []
    provenance = evidence.provenance

    if evidence.source_status == SourceStatus.UNVERIFIED:
        failures.append("SOURCE_STATUS_UNVERIFIED")
    if not provenance.source_uri:
        failures.append("SOURCE_URI_MISSING")
    if not provenance.checksum_sha256:
        failures.append("CHECKSUM_MISSING")
    if provenance.access_class in {AccessClass.LICENSED, AccessClass.PARTICIPANT_SECURE}:
        if not provenance.licence_or_approval:
            failures.append("LICENCE_OR_APPROVAL_MISSING")
    if provenance.access_class == AccessClass.TRE_SDE:
        if not provenance.licence_or_approval:
            failures.append("TRE_APPROVAL_MISSING")
        if evidence.raw_person_level_payload_included:
            failures.append("TRE_RAW_PERSON_LEVEL_PAYLOAD_PROHIBITED")
    if not evidence.dependency_family:
        failures.append("DEPENDENCY_FAMILY_MISSING")
    if evidence.content:
        actual = sha256_text(evidence.content)
        declared_content_hash = evidence.metadata.get("content_sha256")
        if declared_content_hash and actual != declared_content_hash:
            failures.append("CONTENT_HASH_MISMATCH")

    return AdmissionDecision(admitted=not failures, failures=failures)


def admit_evidence(evidence: EvidenceObject) -> EvidenceObject:
    decision = assess_evidence_admission(evidence)
    return evidence.model_copy(
        update={"admitted": decision.admitted, "admission_failures": decision.failures}
    )
