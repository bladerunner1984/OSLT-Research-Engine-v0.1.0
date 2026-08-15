from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import ProvenanceRecord
from oslt_research.evidence.provenance import sha256_text
from oslt_research.ontology.admission import admit_entity, admit_relation
from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    InstitutionalRelation,
    RelationType,
    SystemDomain,
)

from .ocds import parse_ocds_date


#: A fourth register, and the only current source of a tie that crosses from outside
#: government into policy formation.
DEPENDENCY_FAMILY = "register:uk-parliament-written-evidence"


@dataclass(frozen=True)
class EvidenceGraphFragment:
    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    submissions_seen: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)


class ParliamentWrittenEvidenceConnector:
    """Organisation-to-committee advisory ties from UK Parliament written evidence.

    Every other register in this project produces one shape of tie: money moving between
    two bodies. This produces a different one - an organisation putting a case to a body
    that makes policy - which is what MD15 needs before cross-system diffusion can even be
    tested. A graph of nothing but payments is one mechanism repeated.

    Individual submitters are skipped. The propositions concern institutional mechanism,
    and a named private individual is neither an institution nor something this project
    should be building a graph of.

    Witness organisations are typed SystemDomain.UNKNOWN. The API does not say whether a
    submitter is a charity, a royal college, a company or a university, and assigning a
    domain by guesswork would manufacture the cross-system spread the coupling test exists
    to detect. Domain arrives only when the same body is resolved against a register that
    actually types it.

    Requires no API key.
    """

    source_name = "UKParliamentWrittenEvidence"
    connector_version = "1"
    base_url = "https://committees-api.parliament.uk/api/WrittenEvidence"

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 60.0):
        self._client = client
        self.timeout = timeout

    def _fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            response = client.get(
                self.base_url, params=params, headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        finally:
            if self._client is None:
                client.close()

    @staticmethod
    def _organisation_entity(
        name: str, provenance: ProvenanceRecord, submitter_type: str
    ) -> InstitutionalEntity:
        return admit_entity(
            InstitutionalEntity(
                entity_id=f"PWE-ORG-{sha256_text(name.strip().casefold())[:16].upper()}",
                canonical_name=name.strip(),
                roles=[EntityRole.OTHER],
                system_domain=SystemDomain.UNKNOWN,
                jurisdiction="UK",
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
                metadata={"submitter_type": submitter_type, "domain_undetermined": True},
            )
        )

    @staticmethod
    def _committee_entity(
        committee: dict[str, Any], provenance: ProvenanceRecord
    ) -> InstitutionalEntity:
        name = str(committee.get("name") or "").strip()
        return admit_entity(
            InstitutionalEntity(
                entity_id=f"PWE-CTTE-{committee.get('id')}",
                canonical_name=name,
                roles=[EntityRole.GOVERNMENT_DEPARTMENT],
                system_domain=SystemDomain.POLICY,
                jurisdiction="UK",
                identifiers={"parliament_committee_id": str(committee.get("id"))},
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
                metadata={"house": committee.get("house") or ""},
            )
        )

    def harvest_submissions(
        self,
        *,
        take: int = 50,
        skip: int = 0,
        committee_id: int | None = None,
    ) -> EvidenceGraphFragment:
        params: dict[str, Any] = {"take": min(take, 100), "skip": skip}
        if committee_id is not None:
            params["CommitteeId"] = committee_id

        payload = self._fetch(params)
        raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
        submissions = payload.get("items") or []

        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}

        def skip_reason(reason: str) -> None:
            skips[reason] = skips.get(reason, 0) + 1

        for submission in submissions:
            submitted_on = parse_ocds_date(submission.get("publicationDate"))
            if submitted_on is None:
                skip_reason("SUBMISSION_UNDATED")
                continue
            if submission.get("anonymous"):
                skip_reason("ANONYMOUS_SUBMISSION")
                continue

            submission_id = str(submission.get("submissionId") or submission.get("id") or "")
            provenance = ProvenanceRecord(
                source_id="DS_UK_PARLIAMENT_WRITTEN_EVIDENCE",
                source_uri=f"{self.base_url}/{submission_id}" if submission_id else self.base_url,
                published_at=str(submission.get("publicationDate") or ""),
                field_or_document_locator=str(submission.get("internalReference") or ""),
                checksum_sha256=raw_hash,
                access_class=AccessClass.OPEN,
                licence_or_approval="OPEN_PARLIAMENT_LICENCE_V3",
                transformation_ids=["WRITTEN_EVIDENCE_TO_ADVISORY_RELATION_V1"],
                codebook_or_schema_ref="committees-api:WrittenEvidence:v1",
            )

            committees = [
                self._committee_entity(item, provenance)
                for item in submission.get("committees") or []
                if item.get("id") and (item.get("name") or "").strip()
            ]
            if not committees:
                skip_reason("NO_COMMITTEE_ON_SUBMISSION")
                continue
            for committee in committees:
                entities.setdefault(committee.entity_id, committee)

            organisation_names: list[tuple[str, str]] = []
            for witness in submission.get("witnesses") or []:
                submitter_type = str(witness.get("submitterType") or "")
                names = [
                    str(org.get("name") or "").strip()
                    for org in witness.get("organisations") or []
                    if str(org.get("name") or "").strip()
                ]
                if not names:
                    # Individual submitters are out of scope by design, not by oversight.
                    skip_reason("INDIVIDUAL_OR_UNNAMED_SUBMITTER")
                    continue
                organisation_names.extend((name, submitter_type) for name in names)

            for name, submitter_type in organisation_names:
                organisation = self._organisation_entity(name, provenance, submitter_type)
                entities.setdefault(organisation.entity_id, organisation)
                for committee in committees:
                    if organisation.entity_id == committee.entity_id:
                        continue
                    key = f"{submission_id}|{organisation.entity_id}|{committee.entity_id}"
                    relations.append(
                        admit_relation(
                            InstitutionalRelation(
                                relation_id=f"PWER-{sha256_text(key)[:20].upper()}",
                                source_entity_id=organisation.entity_id,
                                target_entity_id=committee.entity_id,
                                relation_type=RelationType.ADVISES,
                                valid_from=submitted_on,
                                provenance=provenance,
                                source_status=SourceStatus.VERIFIED,
                                dependency_family=DEPENDENCY_FAMILY,
                                metadata={
                                    "submission_id": submission_id,
                                    "inquiry": str(
                                        (submission.get("committeeBusiness") or {}).get("title")
                                        or ""
                                    ),
                                    "submitter_type": submitter_type,
                                },
                            )
                        )
                    )

        return EvidenceGraphFragment(
            entities=list(entities.values()),
            relations=relations,
            submissions_seen=len(submissions),
            skip_reasons=skips,
        )
