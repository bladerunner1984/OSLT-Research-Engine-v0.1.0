from __future__ import annotations

from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.evidence.provenance import AdmissionDecision

from .entities import InstitutionalEntity, InstitutionalRelation


def _provenance_failures(provenance, source_status: SourceStatus) -> list[str]:
    failures: list[str] = []
    if source_status == SourceStatus.UNVERIFIED:
        failures.append("SOURCE_STATUS_UNVERIFIED")
    if not provenance.source_uri:
        failures.append("SOURCE_URI_MISSING")
    if not provenance.checksum_sha256:
        failures.append("CHECKSUM_MISSING")
    if provenance.access_class in {AccessClass.LICENSED, AccessClass.PARTICIPANT_SECURE}:
        if not provenance.licence_or_approval:
            failures.append("LICENCE_OR_APPROVAL_MISSING")
    if provenance.access_class == AccessClass.TRE_SDE:
        failures.append("TRE_SDE_SOURCE_PROHIBITED_FOR_ONTOLOGY")
    return failures


def assess_entity_admission(entity: InstitutionalEntity) -> AdmissionDecision:
    failures = _provenance_failures(entity.provenance, entity.source_status)
    if not entity.dependency_family:
        failures.append("DEPENDENCY_FAMILY_MISSING")
    return AdmissionDecision(admitted=not failures, failures=failures)


def assess_relation_admission(relation: InstitutionalRelation) -> AdmissionDecision:
    """Admission for a typed edge.

    Beyond the shared provenance checks, an undated edge is refused. MD10 and MD15 are
    both temporal-ordering claims, so an edge that cannot be placed in time can never
    support them and must not sit in the graph looking as though it could.
    """

    failures = _provenance_failures(relation.provenance, relation.source_status)
    if not relation.dependency_family:
        failures.append("DEPENDENCY_FAMILY_MISSING")
    if not relation.is_dated():
        failures.append("RELATION_UNDATED")
    return AdmissionDecision(admitted=not failures, failures=failures)


def admit_entity(entity: InstitutionalEntity) -> InstitutionalEntity:
    decision = assess_entity_admission(entity)
    return entity.model_copy(
        update={"admitted": decision.admitted, "admission_failures": decision.failures}
    )


def admit_relation(relation: InstitutionalRelation) -> InstitutionalRelation:
    decision = assess_relation_admission(relation)
    return relation.model_copy(
        update={"admitted": decision.admitted, "admission_failures": decision.failures}
    )
