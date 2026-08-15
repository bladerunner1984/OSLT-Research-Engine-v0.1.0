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

from .ocds import identifiers_from_party, parse_ocds_date


#: One register, one dependency family. Two ties evidenced only by Contracts Finder are
#: not independent of each other, however many rows they occupy.
DEPENDENCY_FAMILY = "register:contracts-finder-ocds"


@dataclass(frozen=True)
class ContractGraphFragment:
    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    releases_seen: int = 0
    releases_skipped: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)


class ContractsFinderConnector:
    """Dated buyer-to-supplier contract awards from the UK Contracts Finder OCDS feed.

    This is the primary-register route into the ontology layer. Unlike a secondary
    compilation, every edge arrives with an award date, a contract period, a value and a
    statutory publisher, which is what admission requires: an undated or unverified edge
    cannot support MD10 or MD15 and is refused.

    Requires no API key.

    This endpoint has NO server-side text search. Verified against the live API: keyword,
    keywords, searchCriteria.keyword and q all return byte-identical results to sending no
    parameter at all. It returns the most recent notices and nothing else. The connector
    therefore refuses to accept a search term it cannot honour, and offers client-side
    `title_contains` instead - which filters only the page already retrieved and is not a
    search of the register. Topic scoping here needs date paging plus local filtering, and
    the caller has to know that.
    """

    source_name = "ContractsFinder"
    connector_version = "1"
    base_url = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"

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
    def _entity(
        party_id: str | None,
        name: str,
        role: EntityRole,
        domain: SystemDomain,
        provenance: ProvenanceRecord,
    ) -> InstitutionalEntity:
        identifiers = identifiers_from_party(None, party_id)
        stable = identifiers.get("companies_house") or party_id or sha256_text(name)[:12]
        return admit_entity(
            InstitutionalEntity(
                entity_id=f"CF-{stable}",
                canonical_name=name.strip(),
                roles=[role],
                system_domain=domain,
                jurisdiction="UK",
                identifiers=identifiers,
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
            )
        )

    def harvest_awards(
        self,
        *,
        title_contains: str | None = None,
        published_from: str | None = None,
        published_to: str | None = None,
        limit: int = 100,
    ) -> ContractGraphFragment:
        """Harvest award notices.

        `title_contains` filters the retrieved page locally, case-insensitively. It is not
        a register search: notices outside the page fetched are never seen. Named for what
        it does rather than what a caller might hope it does.
        """

        params: dict[str, Any] = {"limit": min(limit, 100), "stages": "award"}
        if published_from:
            params["publishedFrom"] = published_from
        if published_to:
            params["publishedTo"] = published_to

        payload = self._fetch(params)
        raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))

        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}
        releases = payload.get("releases") or []

        def skip(reason: str) -> None:
            skips[reason] = skips.get(reason, 0) + 1

        needle = (title_contains or "").strip().casefold()
        for release in releases:
            if needle:
                title = str((release.get("tender") or {}).get("title") or "")
                if needle not in title.casefold():
                    skip("TITLE_FILTER_EXCLUDED")
                    continue
            ocid = release.get("ocid") or release.get("id") or ""
            buyer = release.get("buyer") or {}
            buyer_name = (buyer.get("name") or "").strip()
            if not buyer_name:
                skip("BUYER_NAME_MISSING")
                continue

            provenance = ProvenanceRecord(
                source_id="DS_CONTRACTS_FINDER",
                source_uri=f"{self.base_url}?ocid={ocid}" if ocid else self.base_url,
                published_at=release.get("date"),
                retrieval_query=title_contains or "",
                field_or_document_locator=str(ocid),
                checksum_sha256=raw_hash,
                access_class=AccessClass.OPEN,
                licence_or_approval="OGL_v3_CONTRACTS_FINDER",
                transformation_ids=["OCDS_AWARD_TO_INSTITUTIONAL_RELATION_V1"],
                codebook_or_schema_ref=f"ocds:{payload.get('version', 'unknown')}",
            )

            buyer_entity = self._entity(
                buyer.get("id"),
                buyer_name,
                EntityRole.COMMISSIONER,
                SystemDomain.POLICY,
                provenance,
            )
            entities.setdefault(buyer_entity.entity_id, buyer_entity)

            for award in release.get("awards") or []:
                award_date = parse_ocds_date(award.get("date"))
                period = award.get("contractPeriod") or {}
                start = parse_ocds_date(period.get("startDate")) or award_date
                end = parse_ocds_date(period.get("endDate"))
                if start is None:
                    skip("AWARD_UNDATED")
                    continue
                if end is not None and end < start:
                    end = None
                value = (award.get("value") or {}).get("amount")
                currency = (award.get("value") or {}).get("currency")

                for supplier in award.get("suppliers") or []:
                    supplier_name = (supplier.get("name") or "").strip()
                    if not supplier_name:
                        skip("SUPPLIER_NAME_MISSING")
                        continue
                    supplier_entity = self._entity(
                        supplier.get("id"),
                        supplier_name,
                        EntityRole.PROVIDER,
                        SystemDomain.COMMERCIAL,
                        provenance,
                    )
                    entities.setdefault(supplier_entity.entity_id, supplier_entity)
                    if supplier_entity.entity_id == buyer_entity.entity_id:
                        skip("SELF_AWARD")
                        continue

                    award_key = str(award.get("id") or "")
                    relation_key = f"{ocid}|{award_key}|{supplier_entity.entity_id}"
                    relations.append(
                        admit_relation(
                            InstitutionalRelation(
                                relation_id=f"CFR-{sha256_text(relation_key)[:20].upper()}",
                                source_entity_id=buyer_entity.entity_id,
                                target_entity_id=supplier_entity.entity_id,
                                relation_type=RelationType.CONTRACTS_WITH,
                                valid_from=start,
                                valid_to=end,
                                amount_gbp=(
                                    float(value)
                                    if value is not None and currency in (None, "GBP")
                                    else None
                                ),
                                provenance=provenance,
                                source_status=SourceStatus.VERIFIED,
                                dependency_family=DEPENDENCY_FAMILY,
                                metadata={
                                    "ocid": str(ocid),
                                    "award_id": str(award.get("id") or ""),
                                    "currency": currency or "",
                                    "tender_title": (release.get("tender") or {}).get("title", ""),
                                },
                            )
                        )
                    )

        return ContractGraphFragment(
            entities=list(entities.values()),
            relations=relations,
            releases_seen=len(releases),
            releases_skipped=sum(skips.values()),
            skip_reasons=skips,
        )
