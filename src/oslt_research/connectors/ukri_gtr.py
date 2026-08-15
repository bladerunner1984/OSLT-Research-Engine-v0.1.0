from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
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


#: A research-funding register, publicationally independent of the two procurement
#: feeds (Contracts Finder, Find a Tender). It is also a genuinely different *tie type*:
#: a grant is not a purchase. MD15 requires a connected component built from more than
#: one relation type, so a graph carrying only CONTRACTS_WITH edges can never test it.
DEPENDENCY_FAMILY = "register:ukri-gateway-to-research"

#: Reason codes recorded when a project's recipient organisation cannot be established.
#: These are surfaced rather than suppressed: an unresolved recipient changes what the
#: edge means, so a reader must be able to see how many edges are in that condition.
RECIPIENT_UNRESOLVED_LOOKUP_DISABLED = "LOOKUP_DISABLED"
RECIPIENT_UNRESOLVED_LOOKUP_FAILED = "LOOKUP_FAILED"
RECIPIENT_UNRESOLVED_NO_RESOURCE_URL = "NO_RESOURCE_URL"
RECIPIENT_UNRESOLVED_NO_LEAD_ORGANISATION = "NO_LEAD_ORGANISATION_IN_PAYLOAD"


def epoch_millis_to_date(value: Any) -> date | None:
    """Convert a GtR epoch-milliseconds timestamp to a UTC date, or None.

    GtR expresses `fund.start` / `fund.end` as integer milliseconds. Returning None
    rather than raising lets the caller skip an undated grant, which is the only honest
    option: `assess_relation_admission` refuses undated edges, and an edge that cannot
    be placed in time can never support MD10 or MD15.
    """

    if value is None or isinstance(value, bool):
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).date()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def clean_text(value: Any) -> str:
    """Unescape and trim a GtR text field.

    GtR returns HTML entities inside JSON string values (project titles arrive as
    "Analytics &amp; Content"). Storing the raw entity would corrupt every downstream
    display and any name-based comparison.
    """

    if not isinstance(value, str):
        return ""
    return html.unescape(value).strip()


def _https(url: str) -> str:
    """GtR advertises its own resourceUrls over plain http; follow them over TLS."""

    return url.replace("http://", "https://", 1) if url.startswith("http://") else url


def projects_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull the project list out of a GtR search payload.

    The live search response nests the list at `projectsBean.projects`. Older/alternate
    GtR responses use `project` at either level, so all shapes are accepted; an
    unrecognised shape yields an empty list rather than an exception.
    """

    for container in (payload.get("projectsBean") or {}, payload):
        if not isinstance(container, dict):
            continue
        for key in ("projects", "project"):
            found = container.get(key)
            if isinstance(found, list):
                return [item for item in found if isinstance(item, dict)]
    return []


@dataclass(frozen=True)
class GrantGraphFragment:
    """Entities and edges harvested from one GtR search page.

    `recipients_resolved` / `recipients_unresolved` are reported alongside the edges so
    the proportion of edges whose target is a project placeholder rather than a real
    recipient organisation is visible without re-walking the relations.
    """

    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    projects_seen: int = 0
    recipients_resolved: int = 0
    recipients_unresolved: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)


class UkriGatewayToResearchConnector:
    """Dated funder-to-recipient grant ties from UKRI Gateway to Research.

    Requires no API key; GtR returns JSON only when `Accept: application/json` is sent.

    **Recipient resolution.** The projects search payload (`GET /api/projects?q=`) does
    *not* contain the recipient organisation -- it carries `fund.funder` and nothing on
    the receiving side. There is no `/api/organisations?q=` search endpoint (it 404s).
    The recipient is however recoverable exactly, without any name matching, by
    following each project's own `resourceUrl`
    (`/api/projects?ref=<grantReference>`), whose
    `projectOverview.projectComposition.leadResearchOrganisation` block carries the
    organisation's GtR UUID and name. That is an identifier-level join published by the
    source itself, so it is used when available.

    When resolution is switched off, or the lookup fails, or the payload has no lead
    organisation, the connector does **not** fall back to fuzzy matching. It instead
    models the *project* as the edge target and marks the edge
    `recipient_resolved=False` with a reason code, and types it GRANTS_TO rather than
    FUNDS so the weaker claim is distinguishable at the relation-type level and can be
    filtered out of any analysis that needs a real organisational dyad.
    """

    source_name = "UkriGatewayToResearch"
    connector_version = "1"
    base_url = "https://gtr.ukri.org/api/projects"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 60.0,
        resolve_recipients: bool = True,
    ):
        self._client = client
        self.timeout = timeout
        self.resolve_recipients = resolve_recipients

    # ------------------------------------------------------------------ transport

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET JSON from GtR.

        `params` is left as None when following a resourceUrl: httpx replaces the whole
        query string when params are supplied, which would strip the `?ref=` that makes
        the project-detail URL resolve at all.
        """

        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            response = client.get(url, params=params, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        finally:
            if self._client is None:
                client.close()

    def _lead_organisation(self, resource_url: str) -> tuple[dict[str, Any] | None, str]:
        """Follow a project's resourceUrl for its lead research organisation.

        Returns (organisation, unresolved_reason). A transport or decoding failure is
        caught and reported as an unresolved recipient rather than aborting the harvest:
        one dead project lookup must not discard a whole page of otherwise good edges.
        The search request itself is deliberately *not* wrapped this way -- a failed
        search means we have nothing, and that must surface.
        """

        if not resource_url:
            return None, RECIPIENT_UNRESOLVED_NO_RESOURCE_URL
        try:
            payload = self._get(_https(resource_url))
        except (httpx.HTTPError, json.JSONDecodeError, ValueError):
            return None, RECIPIENT_UNRESOLVED_LOOKUP_FAILED

        composition = ((payload.get("projectOverview") or {}).get("projectComposition")) or {}
        organisation = composition.get("leadResearchOrganisation")
        if not isinstance(organisation, dict):
            return None, RECIPIENT_UNRESOLVED_NO_LEAD_ORGANISATION
        if not organisation.get("id") or not clean_text(organisation.get("name")):
            return None, RECIPIENT_UNRESOLVED_NO_LEAD_ORGANISATION
        return organisation, ""

    # -------------------------------------------------------------------- mapping

    @staticmethod
    def _entity(
        *,
        entity_id: str,
        name: str,
        role: EntityRole,
        domain: SystemDomain,
        identifiers: dict[str, str],
        provenance: ProvenanceRecord,
        metadata: dict[str, Any] | None = None,
    ) -> InstitutionalEntity:
        return admit_entity(
            InstitutionalEntity(
                entity_id=entity_id,
                canonical_name=name,
                roles=[role],
                system_domain=domain,
                jurisdiction="UK",
                identifiers=identifiers,
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
                metadata=metadata or {},
            )
        )

    def harvest_grants(
        self,
        *,
        term: str,
        page: int = 1,
        page_size: int = 25,
    ) -> GrantGraphFragment:
        """Harvest one page of GtR projects into funder-side grant edges."""

        params: dict[str, Any] = {"q": term, "p": max(page, 1), "s": max(min(page_size, 100), 1)}
        payload = self._get(self.base_url, params)
        raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
        refreshed = (payload.get("headerData") or {}).get("lastRefreshDate")
        projects = projects_from_payload(payload)

        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}
        resolved_count = 0
        unresolved_count = 0

        def skip(reason: str) -> None:
            skips[reason] = skips.get(reason, 0) + 1

        for project in projects:
            fund = project.get("fund") or {}
            funder = fund.get("funder") or {}
            funder_id = str(funder.get("id") or "").strip()
            funder_name = clean_text(funder.get("name"))
            if not funder_id or not funder_name:
                skip("FUNDER_MISSING")
                continue

            start = epoch_millis_to_date(fund.get("start"))
            if start is None:
                # Admission would refuse this edge as RELATION_UNDATED; skipping keeps
                # the graph free of edges that merely look as though they could count.
                skip("GRANT_UNDATED")
                continue
            end = epoch_millis_to_date(fund.get("end"))
            if end is not None and end < start:
                end = None

            project_id = str(project.get("id") or "").strip()
            grant_reference = str(project.get("grantReference") or "").strip()
            resource_url = _https(str(project.get("resourceUrl") or "").strip())
            locator = grant_reference or project_id

            provenance = ProvenanceRecord(
                source_id="DS_UKRI_GATEWAY_TO_RESEARCH",
                source_uri=resource_url or self.base_url,
                published_at=refreshed,
                retrieval_query=f"q={term}&p={params['p']}&s={params['s']}",
                field_or_document_locator=locator,
                checksum_sha256=raw_hash,
                access_class=AccessClass.OPEN,
                licence_or_approval="OGL_v3_UKRI_GATEWAY_TO_RESEARCH",
                transformation_ids=["GTR_PROJECT_FUND_TO_INSTITUTIONAL_RELATION_V1"],
                codebook_or_schema_ref="gtr:api/projects",
            )

            funder_entity = self._entity(
                entity_id=f"GTR-{funder_id}",
                name=funder_name,
                role=EntityRole.PUBLIC_FUNDER,
                domain=SystemDomain.POLICY,
                identifiers={"gtr_organisation_id": funder_id},
                provenance=provenance,
                metadata={"node_kind": "organisation"},
            )
            entities.setdefault(funder_entity.entity_id, funder_entity)

            organisation: dict[str, Any] | None = None
            unresolved_reason = RECIPIENT_UNRESOLVED_LOOKUP_DISABLED
            if self.resolve_recipients:
                organisation, unresolved_reason = self._lead_organisation(resource_url)

            if organisation is not None:
                recipient_id = str(organisation["id"]).strip()
                target = self._entity(
                    entity_id=f"GTR-{recipient_id}",
                    name=clean_text(organisation.get("name")),
                    role=EntityRole.ACADEMIC_BODY,
                    domain=SystemDomain.ACADEMIC,
                    identifiers={"gtr_organisation_id": recipient_id},
                    provenance=provenance,
                    metadata={
                        "node_kind": "organisation",
                        "gtr_organisation_type_ind": organisation.get("typeInd") or "",
                        "region": (organisation.get("address") or {}).get("region") or "",
                    },
                )
                relation_type = RelationType.FUNDS
            else:
                # No recipient could be established from the register. Model the project
                # itself so the money still has a dated, typed destination -- but never
                # dressed up as an organisational tie.
                target = self._entity(
                    entity_id=f"GTR-PROJECT-{project_id or sha256_text(locator)[:12].upper()}",
                    name=clean_text(project.get("title")) or f"GtR project {locator}",
                    role=EntityRole.OTHER,
                    domain=SystemDomain.ACADEMIC,
                    identifiers={
                        key: value
                        for key, value in (
                            ("gtr_project_id", project_id),
                            ("gtr_grant_reference", grant_reference),
                        )
                        if value
                    },
                    provenance=provenance,
                    metadata={
                        "node_kind": "project",
                        "recipient_resolved": False,
                        "recipient_unresolved_reason": unresolved_reason,
                    },
                )
                relation_type = RelationType.GRANTS_TO

            if target.entity_id == funder_entity.entity_id:
                # GtR lists a handful of funders as their own lead organisation; the
                # relation model forbids self-loops and the tie is uninformative anyway.
                skip("FUNDER_IS_RECIPIENT")
                continue

            entities.setdefault(target.entity_id, target)
            if organisation is not None:
                resolved_count += 1
            else:
                unresolved_count += 1
                skip(f"RECIPIENT_UNRESOLVED_{unresolved_reason}")

            value = fund.get("valuePounds")
            amount = float(value) if isinstance(value, (int, float)) and value >= 0 else None

            relation_key = f"{locator}|{funder_entity.entity_id}|{target.entity_id}"
            relations.append(
                admit_relation(
                    InstitutionalRelation(
                        relation_id=f"GTRR-{sha256_text(relation_key)[:20].upper()}",
                        source_entity_id=funder_entity.entity_id,
                        target_entity_id=target.entity_id,
                        relation_type=relation_type,
                        valid_from=start,
                        valid_to=end,
                        amount_gbp=amount,
                        provenance=provenance,
                        source_status=SourceStatus.VERIFIED,
                        dependency_family=DEPENDENCY_FAMILY,
                        metadata={
                            "gtr_project_id": project_id,
                            "gtr_grant_reference": grant_reference,
                            "project_title": clean_text(project.get("title")),
                            "grant_category": clean_text(project.get("grantCategory")),
                            "fund_type": clean_text(fund.get("type")),
                            "recipient_resolved": organisation is not None,
                            "recipient_unresolved_reason": (
                                "" if organisation is not None else unresolved_reason
                            ),
                            "target_node_kind": (
                                "organisation" if organisation is not None else "project"
                            ),
                        },
                    )
                )
            )

        return GrantGraphFragment(
            entities=list(entities.values()),
            relations=relations,
            projects_seen=len(projects),
            recipients_resolved=resolved_count,
            recipients_unresolved=unresolved_count,
            skip_reasons=skips,
        )
