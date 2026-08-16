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

from .ocds import identifiers_from_party, index_parties, parse_ocds_date


#: DS071 in the source register (added 2026-08). Above-threshold notices only, so this
#: is not a census of public spending.
SOURCE_ID = "DS071"


#: A publication pipeline distinct from Contracts Finder, so ties evidenced by both
#: registers sit in two families and can corroborate one another.
DEPENDENCY_FAMILY = "register:find-a-tender-ocds"


@dataclass(frozen=True)
class TenderGraphFragment:
    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    releases_seen: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)


class FindATenderConnector:
    """Dated buyer-to-supplier awards from the UK Find a Tender OCDS feed.

    Find a Tender splits award detail across two blocks: awards[] names the suppliers,
    while contracts[] carries dateSigned and value, joined on awardID. An award with no
    matching contract has no date and is skipped rather than admitted undated.

    Requires no API key.
    """

    source_name = "FindATender"
    connector_version = "1"
    base_url = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"

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
        party: dict[str, Any] | None,
        party_id: str | None,
        name: str,
        role: EntityRole,
        domain: SystemDomain,
        provenance: ProvenanceRecord,
    ) -> InstitutionalEntity:
        identifiers = identifiers_from_party(party, party_id)
        stable = (
            identifiers.get("companies_house")
            or identifiers.get("charity_number")
            or party_id
            or sha256_text(name)[:12]
        )
        return admit_entity(
            InstitutionalEntity(
                entity_id=f"FTS-{stable}",
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
        limit: int = 100,
        updated_from: str | None = None,
        updated_to: str | None = None,
    ) -> TenderGraphFragment:
        params: dict[str, Any] = {"limit": min(limit, 100), "stages": "award"}
        if updated_from:
            params["updatedFrom"] = updated_from
        if updated_to:
            params["updatedTo"] = updated_to

        payload = self._fetch(params)
        raw_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))

        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}
        releases = payload.get("releases") or []

        def skip(reason: str) -> None:
            skips[reason] = skips.get(reason, 0) + 1

        for release in releases:
            ocid = str(release.get("ocid") or release.get("id") or "")
            parties = index_parties(release)
            buyer = release.get("buyer") or {}
            buyer_name = (buyer.get("name") or "").strip()
            if not buyer_name:
                skip("BUYER_NAME_MISSING")
                continue

            # contracts[] carries the date and value; awards[] carries the suppliers.
            contracts_by_award: dict[str, dict[str, Any]] = {}
            for contract in release.get("contracts") or []:
                award_id = str(contract.get("awardID") or "")
                if award_id and award_id not in contracts_by_award:
                    contracts_by_award[award_id] = contract

            provenance = ProvenanceRecord(
                source_id="DS_FIND_A_TENDER",
                source_uri=f"{self.base_url}?ocid={ocid}" if ocid else self.base_url,
                published_at=release.get("date"),
                field_or_document_locator=ocid,
                checksum_sha256=raw_hash,
                access_class=AccessClass.OPEN,
                licence_or_approval="OGL_v3_FIND_A_TENDER",
                transformation_ids=["OCDS_AWARD_CONTRACT_TO_INSTITUTIONAL_RELATION_V1"],
                codebook_or_schema_ref=f"ocds:{payload.get('version', 'unknown')}",
            )

            buyer_entity = self._entity(
                parties.get(str(buyer.get("id"))),
                buyer.get("id"),
                buyer_name,
                EntityRole.COMMISSIONER,
                SystemDomain.POLICY,
                provenance,
            )
            entities.setdefault(buyer_entity.entity_id, buyer_entity)

            for award in release.get("awards") or []:
                award_id = str(award.get("id") or "")
                contract = contracts_by_award.get(award_id) or {}
                signed = parse_ocds_date(contract.get("dateSigned")) or parse_ocds_date(
                    award.get("date")
                )
                if signed is None:
                    skip("AWARD_UNDATED_NO_MATCHING_CONTRACT")
                    continue

                period = award.get("contractPeriod") or contract.get("period") or {}
                end = parse_ocds_date(period.get("endDate"))
                if end is not None and end < signed:
                    end = None

                value_block = contract.get("value") or award.get("value") or {}
                amount = value_block.get("amount")
                currency = value_block.get("currency")

                for supplier in award.get("suppliers") or []:
                    supplier_name = (supplier.get("name") or "").strip()
                    if not supplier_name:
                        skip("SUPPLIER_NAME_MISSING")
                        continue
                    supplier_entity = self._entity(
                        parties.get(str(supplier.get("id"))),
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

                    relation_key = f"{ocid}|{award_id}|{supplier_entity.entity_id}"
                    relations.append(
                        admit_relation(
                            InstitutionalRelation(
                                relation_id=f"FTSR-{sha256_text(relation_key)[:20].upper()}",
                                source_entity_id=buyer_entity.entity_id,
                                target_entity_id=supplier_entity.entity_id,
                                relation_type=RelationType.CONTRACTS_WITH,
                                valid_from=signed,
                                valid_to=end,
                                amount_gbp=(
                                    float(amount)
                                    if amount is not None and currency in (None, "GBP")
                                    else None
                                ),
                                provenance=provenance,
                                source_status=SourceStatus.VERIFIED,
                                dependency_family=DEPENDENCY_FAMILY,
                                metadata={
                                    "ocid": ocid,
                                    "award_id": award_id,
                                    "currency": currency or "",
                                    "tender_title": (release.get("tender") or {}).get("title", ""),
                                },
                            )
                        )
                    )

        return TenderGraphFragment(
            entities=list(entities.values()),
            relations=relations,
            releases_seen=len(releases),
            skip_reasons=skips,
        )
