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


#: DS030 in the source register, as ``DEPENDENCY_FAMILY`` below already notes.
SOURCE_ID = "DS030"


#: DS030 in the source register. A fifth register and, more importantly, the only
#: ISSUES_GUIDANCE_TO source in the project.
DEPENDENCY_FAMILY = "register:govuk-publications"

#: Document types that constitute a body issuing guidance, as opposed to reporting or
#: announcing. A press release is not guidance and must not be counted as one.
GUIDANCE_DOCUMENT_TYPES = frozenset(
    {"guidance", "statutory_guidance", "detailed_guide", "regulation", "notice"}
)


@dataclass(frozen=True)
class GuidanceGraphFragment:
    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    documents_seen: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)


class GovUkGuidanceConnector:
    """Dated guidance-issuance ties from the GOV.UK Search API.

    The coupling test kept returning MX09 partly because every edge in the graph was a
    payment or a submission, and a component built from one tie type is one mechanism
    repeated. This supplies the third kind: a named body issuing dated guidance on a
    topic, which is what MD10 and MD15 describe when they talk about diffusion into
    policy.

    Chosen over the NICE syndication API because that requires a licence agreement and a
    cyber security certificate, while this needs no key at all. It covers a different
    thing - government guidance rather than clinical guidelines - but for propositions
    about diffusion BETWEEN institutions, guidance issuance is the more direct measure.

    Requires no API key.
    """

    source_name = "GovUkGuidance"
    connector_version = "1"
    base_url = "https://www.gov.uk/api/search.json"

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
    def _issuer(organisation: dict[str, Any], provenance: ProvenanceRecord) -> InstitutionalEntity:
        slug = str(organisation.get("slug") or "").strip()
        title = str(organisation.get("title") or "").strip()
        return admit_entity(
            InstitutionalEntity(
                entity_id=f"GOVUK-ORG-{slug or sha256_text(title)[:12]}",
                canonical_name=title,
                roles=[EntityRole.GUIDELINE_BODY],
                system_domain=SystemDomain.POLICY,
                jurisdiction="UK",
                identifiers={"govuk_organisation_slug": slug} if slug else {},
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
            )
        )

    @staticmethod
    def _topic(title: str, link: str, provenance: ProvenanceRecord) -> InstitutionalEntity:
        # The guidance document itself is the target of the tie. It is not an institution,
        # so it carries UNKNOWN and cannot widen cross-system spread on its own.
        return admit_entity(
            InstitutionalEntity(
                entity_id=f"GOVUK-DOC-{sha256_text(link)[:16].upper()}",
                canonical_name=title.strip(),
                roles=[EntityRole.OTHER],
                system_domain=SystemDomain.UNKNOWN,
                jurisdiction="UK",
                identifiers={"govuk_link": link},
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
                metadata={"is_document_not_institution": True},
            )
        )

    def harvest_guidance(
        self,
        *,
        query: str | None = None,
        organisation_slug: str | None = None,
        count: int = 50,
        start: int = 0,
    ) -> GuidanceGraphFragment:
        params: dict[str, Any] = {
            "count": min(count, 100),
            "start": start,
            "fields": "title,link,public_timestamp,organisations,content_store_document_type",
        }
        if query:
            params["q"] = query
        if organisation_slug:
            params["filter_organisations"] = organisation_slug

        payload = self._fetch(params)
        raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
        results = payload.get("results") or []

        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}

        def skip(reason: str) -> None:
            skips[reason] = skips.get(reason, 0) + 1

        for document in results:
            document_type = str(document.get("content_store_document_type") or "")
            if document_type not in GUIDANCE_DOCUMENT_TYPES:
                skip(f"NOT_GUIDANCE_{document_type or 'UNTYPED'}")
                continue

            issued_on = parse_ocds_date(document.get("public_timestamp"))
            if issued_on is None:
                skip("DOCUMENT_UNDATED")
                continue

            title = str(document.get("title") or "").strip()
            link = str(document.get("link") or "").strip()
            if not title or not link:
                skip("TITLE_OR_LINK_MISSING")
                continue

            organisations = [
                item for item in document.get("organisations") or []
                if isinstance(item, dict) and str(item.get("title") or "").strip()
            ]
            if not organisations:
                # Without an issuer there is no tie, only a document.
                skip("NO_ISSUING_ORGANISATION")
                continue

            provenance = ProvenanceRecord(
                source_id="DS030",
                source_uri=f"https://www.gov.uk{link}" if link.startswith("/") else link,
                published_at=str(document.get("public_timestamp") or ""),
                retrieval_query=query or organisation_slug or "",
                field_or_document_locator=link,
                checksum_sha256=raw_hash,
                access_class=AccessClass.OPEN,
                licence_or_approval="OGL_v3_GOVUK",
                transformation_ids=["GOVUK_PUBLICATION_TO_GUIDANCE_RELATION_V1"],
                codebook_or_schema_ref="govuk:search-api:v1",
            )

            target = self._topic(title, link, provenance)
            entities.setdefault(target.entity_id, target)

            for organisation in organisations:
                issuer = self._issuer(organisation, provenance)
                entities.setdefault(issuer.entity_id, issuer)
                if issuer.entity_id == target.entity_id:
                    continue
                key = f"{link}|{issuer.entity_id}"
                relations.append(
                    admit_relation(
                        InstitutionalRelation(
                            relation_id=f"GOVR-{sha256_text(key)[:20].upper()}",
                            source_entity_id=issuer.entity_id,
                            target_entity_id=target.entity_id,
                            relation_type=RelationType.ISSUES_GUIDANCE_TO,
                            valid_from=issued_on,
                            provenance=provenance,
                            source_status=SourceStatus.VERIFIED,
                            dependency_family=DEPENDENCY_FAMILY,
                            metadata={
                                "document_type": document_type,
                                "govuk_link": link,
                            },
                        )
                    )
                )

        return GuidanceGraphFragment(
            entities=list(entities.values()),
            relations=relations,
            documents_seen=len(results),
            skip_reasons=skips,
        )
