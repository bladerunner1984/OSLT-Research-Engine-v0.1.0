from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable

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

#: 360Giving is a *philanthropic* grants register, published by the grant-makers
#: themselves rather than by government. That makes it independent of both the
#: procurement feeds and of UKRI Gateway to Research: UKRI supplies public research
#: funding, this supplies charitable-trust funding. MD15 needs a connected component
#: spanning more than one funding system, so these edges cannot share a family with
#: `register:ukri-gateway-to-research`.
DEPENDENCY_FAMILY = "register:360giving"

#: The registry of every published 360Giving dataset. It is a *static* document: it
#: accepts no query parameters and performs no server-side search, so every filter this
#: connector offers is applied client-side after download. That is stated explicitly in
#: each record's `retrieval_query` so a reader can never mistake a local filter for a
#: server-honoured one.
REGISTRY_URL = "https://registry.threesixtygiving.org/data.json"

#: Field names carrying the date the grant was *awarded*. `dateModified` /
#: `Last Modified` are deliberately absent: they record when the publisher last touched
#: the row, which can post-date the award by years. Reading a maintenance timestamp as
#: an award date would silently fabricate the temporal ordering MD10 tests.
_AWARD_DATE_KEYS = ("awarddate", "award date")
_END_DATE_KEYS = ("planned dates:end date", "actual dates:end date")

#: Org-id prefixes used across UK 360Giving data. The three charity regulators each get
#: their own prefix; all three populate the same `charity_number` namespace because
#: `STRONG_IDENTIFIER_NAMESPACES` resolves entities on that key.
_CHARITY_PREFIXES = ("GB-CHC-", "GB-SC-", "GB-NIC-", "GB-EDU-")
_COMPANY_PREFIXES = ("GB-COH-",)

SKIP_UNDATED = "GRANT_UNDATED"
SKIP_FUNDER_MISSING = "FUNDER_MISSING"
SKIP_RECIPIENT_MISSING = "RECIPIENT_MISSING"
SKIP_SELF_LOOP = "FUNDER_IS_RECIPIENT"
SKIP_FILTERED = "CLIENT_SIDE_FILTER_EXCLUDED"


def parse_grant_date(value: Any) -> date | None:
    """Parse a 360Giving date, or None when it cannot be placed in time.

    Publishers emit ISO-8601 (with or without a time part) and, less often, UK
    `DD/MM/YYYY`. Day-first is tried before month-first because the register is UK data;
    an ambiguous `03/04/2020` read month-first would move the award by a month.

    Returning None rather than raising is what lets the caller *skip* the grant.
    `assess_relation_admission` refuses an undated edge anyway, so admitting one would
    only put a permanently-failing row into the graph.
    """

    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    head = text.split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def identifiers_from_org(org: dict[str, Any]) -> dict[str, str]:
    """Pull strong identifiers out of a 360Giving organisation block.

    Two routes are merged because publishers use either or both: an explicit
    `charityNumber` / `companyNumber` field, and the org-id prefix convention
    (`GB-CHC-1234567`, `GB-COH-01234567`). Only `charity_number` and `companies_house`
    are emitted under those exact keys, because those are the namespaces
    `STRONG_IDENTIFIER_NAMESPACES` will merge two records on -- writing a guess into one
    of them would silently fuse two different organisations.
    """

    identifiers: dict[str, str] = {}
    org_id = _text(org.get("id"))
    if org_id:
        identifiers["threesixtygiving_org_id"] = org_id
        upper = org_id.upper()
        for prefix in _CHARITY_PREFIXES:
            if upper.startswith(prefix):
                identifiers["charity_number"] = org_id[len(prefix) :]
                break
        for prefix in _COMPANY_PREFIXES:
            if upper.startswith(prefix):
                identifiers["companies_house"] = org_id[len(prefix) :]
                break
    charity = _text(org.get("charityNumber"))
    if charity:
        identifiers["charity_number"] = charity
    company = _text(org.get("companyNumber"))
    if company:
        identifiers["companies_house"] = company
    return {key: value for key, value in identifiers.items() if value}


def _entity_id(org: dict[str, Any], identifiers: dict[str, str]) -> str:
    """Stable node id, preferring a published identifier over a name hash.

    A name hash is only a fallback. It is never written into a strong-identifier
    namespace, so two same-named organisations still cannot be merged on it alone.
    """

    org_id = _text(org.get("id"))
    if org_id:
        return f"360G-{org_id}"
    charity = identifiers.get("charity_number")
    if charity:
        return f"360G-GB-CHC-{charity}"
    return f"360G-NAME-{sha256_text(_text(org.get('name')).casefold())[:16].upper()}"


def _first_org(value: Any) -> dict[str, Any]:
    """360Giving models funder/recipient as an array; take the first usable member."""

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and _text(item.get("name")):
                return item
    return {}


def _lookup(row: dict[str, str], *candidates: str) -> str:
    """Case-insensitive CSV column read.

    Real publishers disagree on capitalisation of the same standard column ("Award Date"
    vs "Award date", "Amount Awarded" vs "Amount awarded"). Matching case-sensitively
    would silently drop the award date for whole publishers, and every one of those
    grants would then be skipped as undated -- a data loss that looks like a data gap.
    """

    folded = {key.strip().casefold(): value for key, value in row.items() if key}
    for candidate in candidates:
        found = folded.get(candidate.strip().casefold())
        if found is not None and str(found).strip():
            return str(found).strip()
    return ""


def grants_from_csv(text: str) -> list[dict[str, Any]]:
    """Reshape a 360Giving CSV export into the same dicts the JSON format uses.

    Normalising to one internal shape keeps a single mapping path, so a fix to date or
    identifier handling cannot apply to one serialisation and miss the other.
    """

    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    grants: list[dict[str, Any]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        recipient = {
            "id": _lookup(row, "Recipient Org:Identifier"),
            "name": _lookup(row, "Recipient Org:Name"),
            "charityNumber": _lookup(row, "Recipient Org:Charity Number"),
            "companyNumber": _lookup(row, "Recipient Org:Company Number"),
        }
        funder = {
            "id": _lookup(row, "Funding Org:Identifier"),
            "name": _lookup(row, "Funding Org:Name"),
            "charityNumber": _lookup(row, "Funding Org:Charity Number"),
            "companyNumber": _lookup(row, "Funding Org:Company Number"),
        }
        amount = _lookup(row, "Amount Awarded")
        grants.append(
            {
                "id": _lookup(row, "Identifier"),
                "title": _lookup(row, "Title"),
                "description": _lookup(row, "Description"),
                "currency": _lookup(row, "Currency") or "GBP",
                "amountAwarded": amount,
                "awardDate": _lookup(row, *_AWARD_DATE_KEYS),
                "_endDate": _lookup(row, *_END_DATE_KEYS),
                "fundingOrganization": [funder],
                "recipientOrganization": [recipient],
            }
        )
    return grants


def grants_from_json(payload: Any) -> list[dict[str, Any]]:
    """Pull the grant list out of a 360Giving JSON package."""

    if isinstance(payload, dict):
        found = payload.get("grants")
        if isinstance(found, list):
            return [item for item in found if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _end_date(grant: dict[str, Any]) -> date | None:
    """End of the funded period, from whichever serialisation supplied it."""

    direct = parse_grant_date(grant.get("_endDate"))
    if direct is not None:
        return direct
    planned = grant.get("plannedDates")
    if isinstance(planned, list):
        for item in planned:
            if isinstance(item, dict):
                parsed = parse_grant_date(item.get("endDate"))
                if parsed is not None:
                    return parsed
    return None


def _amount_gbp(grant: dict[str, Any]) -> float | None:
    """Award value, but only when the publisher states the currency is GBP.

    `amount_gbp` is a typed field. Copying a EUR or USD award into it would make the
    number wrong rather than missing, and nothing downstream could detect that.
    """

    if _text(grant.get("currency")).upper() not in ("", "GBP"):
        return None
    raw = grant.get("amountAwarded")
    try:
        amount = float(str(raw).replace(",", "").replace("£", "").strip())
    except (TypeError, ValueError):
        return None
    return amount if amount >= 0 else None


@dataclass(frozen=True)
class DatasetRef:
    """One publisher dataset advertised by the 360Giving registry."""

    publisher_name: str
    publisher_prefix: str
    title: str
    download_url: str
    #: When the publisher last *touched the file*. Never an award date -- it is carried
    #: as provenance about the document, and never reaches `valid_from`.
    modified: str = ""
    licence: str = ""


@dataclass(frozen=True)
class GrantGraphFragment:
    """Entities and edges harvested from one 360Giving dataset.

    `skip_reasons` is reported rather than swallowed: the count of grants dropped as
    undated is the single most important quality signal for this source, and hiding it
    would make a thin harvest look like a complete one.
    """

    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    grants_seen: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)


class ThreeSixtyGivingConnector:
    """Dated philanthropic funder-to-recipient grant edges from 360Giving.

    **Source shape.** 360Giving does not operate a queryable grants API. GrantNav's
    `search.json` sits behind a proof-of-work browser challenge and
    `api.threesixtygiving.org` serves 404 on every path. What *is* openly available is
    the dataset registry at `registry.threesixtygiving.org/data.json`, which lists every
    published dataset together with the publisher's own download URL; those files are
    360Giving Standard JSON or CSV and are fetched directly from the publisher.

    **No server-side search exists.** Both `publisher_contains` and `title_contains`
    are applied *after* download, in this process. That is recorded in every
    `retrieval_query` string, because a filter the reader believes was honoured by a
    server -- when in fact the server ignored it -- silently changes what the resulting
    sample is a sample *of*.

    **Recipient domain is not inferred.** 360Giving states a recipient's name and
    registration numbers but never its sector. Recipients are therefore emitted as
    `SystemDomain.UNKNOWN` / `EntityRole.OTHER`. Guessing "charity number implies
    advocacy" would manufacture exactly the philanthropic-to-advocacy coupling this
    engine exists to detect independently. Resolution to a typed domain is a separate
    join on `charity_number` / `companies_house`, which is why those are extracted.
    """

    source_name = "ThreeSixtyGiving"
    connector_version = "1"
    registry_url = REGISTRY_URL

    def __init__(self, *, client: httpx.Client | None = None, timeout: float = 60.0):
        self._client = client
        self.timeout = timeout

    # ------------------------------------------------------------------ transport

    def _get(self, url: str) -> httpx.Response:
        client = self._client or httpx.Client(timeout=self.timeout, follow_redirects=True)
        try:
            response = client.get(url, headers={"Accept": "application/json, text/csv, */*"})
            response.raise_for_status()
            return response
        finally:
            if self._client is None:
                client.close()

    # -------------------------------------------------------------------- registry

    def fetch_registry(
        self,
        *,
        publisher_contains: str | None = None,
        formats: Iterable[str] = ("json", "csv"),
    ) -> list[DatasetRef]:
        """List datasets from the registry, filtered client-side.

        `formats` defaults to the two machine-readable serialisations. The bulk of the
        register is published as `.xlsx`, which is deliberately not parsed here: a
        spreadsheet reader is a different trust surface and would be a silent third
        mapping path.
        """

        payload = self._get(self.registry_url).json()
        wanted = tuple(f".{suffix.lower().lstrip('.')}" for suffix in formats)
        needle = (publisher_contains or "").strip().casefold()

        datasets: list[DatasetRef] = []
        for record in payload if isinstance(payload, list) else []:
            if not isinstance(record, dict):
                continue
            publisher = record.get("publisher") or {}
            name = _text(publisher.get("name"))
            if needle and needle not in name.casefold():
                continue
            for distribution in record.get("distribution") or []:
                if not isinstance(distribution, dict):
                    continue
                url = _text(distribution.get("downloadURL"))
                if not url or not url.split("?")[0].lower().endswith(wanted):
                    continue
                datasets.append(
                    DatasetRef(
                        publisher_name=name,
                        publisher_prefix=_text(publisher.get("prefix")),
                        title=_text(distribution.get("title")) or _text(record.get("title")),
                        download_url=url,
                        modified=_text(record.get("modified")),
                        licence=_text(record.get("license_name")) or _text(record.get("license")),
                    )
                )
        return datasets

    # -------------------------------------------------------------------- harvest

    def harvest_dataset(
        self,
        dataset: DatasetRef,
        *,
        title_contains: str | None = None,
        max_grants: int = 500,
    ) -> GrantGraphFragment:
        """Harvest one publisher dataset into dated FUNDS edges."""

        response = self._get(dataset.download_url)
        body = response.text
        raw_hash = sha256_text(body)
        if dataset.download_url.split("?")[0].lower().endswith(".csv"):
            grants = grants_from_csv(body)
        else:
            try:
                grants = grants_from_json(json.loads(body))
            except (json.JSONDecodeError, ValueError):
                grants = []

        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}

        def skip(reason: str) -> None:
            skips[reason] = skips.get(reason, 0) + 1

        needle = (title_contains or "").strip().casefold()
        retrieval_query = (
            f"registry dataset {dataset.download_url}; "
            f"publisher/title filters applied CLIENT-SIDE (source has no query API)"
        )

        for grant in grants[: max(max_grants, 0)]:
            haystack = f"{_text(grant.get('title'))} {_text(grant.get('description'))}".casefold()
            if needle and needle not in haystack:
                skip(SKIP_FILTERED)
                continue

            award_date = parse_grant_date(grant.get("awardDate"))
            if award_date is None:
                # Refused by `assess_relation_admission` as RELATION_UNDATED. Skipping
                # keeps the graph free of edges that merely look as though they count.
                skip(SKIP_UNDATED)
                continue

            funder = _first_org(grant.get("fundingOrganization"))
            recipient = _first_org(grant.get("recipientOrganization"))
            if not funder:
                skip(SKIP_FUNDER_MISSING)
                continue
            if not recipient:
                skip(SKIP_RECIPIENT_MISSING)
                continue

            funder_ids = identifiers_from_org(funder)
            recipient_ids = identifiers_from_org(recipient)
            funder_key = _entity_id(funder, funder_ids)
            recipient_key = _entity_id(recipient, recipient_ids)
            if funder_key == recipient_key:
                # The relation model forbids self-loops, and a grant-maker funding its
                # own record is uninformative rather than an error worth raising.
                skip(SKIP_SELF_LOOP)
                continue

            locator = _text(grant.get("id")) or f"{funder_key}->{recipient_key}@{award_date}"
            provenance = ProvenanceRecord(
                source_id="DS_360GIVING_REGISTRY",
                source_uri=dataset.download_url,
                # The publisher's file-modified stamp, kept as a property of the
                # *document*. It is never read as an award date.
                published_at=dataset.modified or None,
                retrieval_query=retrieval_query,
                field_or_document_locator=locator,
                checksum_sha256=raw_hash,
                access_class=AccessClass.OPEN,
                licence_or_approval=dataset.licence or "360GIVING_PUBLISHER_OPEN_LICENCE",
                transformation_ids=["THREESIXTYGIVING_GRANT_TO_INSTITUTIONAL_RELATION_V1"],
                codebook_or_schema_ref="360giving:standard/grant",
            )

            funder_entity = admit_entity(
                InstitutionalEntity(
                    entity_id=funder_key,
                    canonical_name=_text(funder.get("name")),
                    roles=[EntityRole.PHILANTHROPIC_FUNDER],
                    system_domain=SystemDomain.PHILANTHROPIC,
                    jurisdiction="UK",
                    identifiers=funder_ids,
                    provenance=provenance,
                    source_status=SourceStatus.VERIFIED,
                    dependency_family=DEPENDENCY_FAMILY,
                    metadata={
                        "node_kind": "organisation",
                        "publisher_prefix": dataset.publisher_prefix,
                    },
                )
            )
            recipient_entity = admit_entity(
                InstitutionalEntity(
                    entity_id=recipient_key,
                    canonical_name=_text(recipient.get("name")),
                    roles=[EntityRole.OTHER],
                    # 360Giving publishes no sector for the recipient. See the class
                    # docstring: an inferred domain would fabricate the coupling.
                    system_domain=SystemDomain.UNKNOWN,
                    jurisdiction="UK",
                    identifiers=recipient_ids,
                    provenance=provenance,
                    source_status=SourceStatus.VERIFIED,
                    dependency_family=DEPENDENCY_FAMILY,
                    metadata={
                        "node_kind": "organisation",
                        "domain_source": "NOT_STATED_BY_SOURCE",
                    },
                )
            )
            entities.setdefault(funder_entity.entity_id, funder_entity)
            entities.setdefault(recipient_entity.entity_id, recipient_entity)

            end = _end_date(grant)
            if end is not None and end < award_date:
                end = None

            relations.append(
                admit_relation(
                    InstitutionalRelation(
                        relation_id=f"TSGR-{sha256_text(f'{dataset.download_url}|{locator}')[:20].upper()}",
                        source_entity_id=funder_entity.entity_id,
                        target_entity_id=recipient_entity.entity_id,
                        relation_type=RelationType.FUNDS,
                        valid_from=award_date,
                        valid_to=end,
                        amount_gbp=_amount_gbp(grant),
                        provenance=provenance,
                        source_status=SourceStatus.VERIFIED,
                        dependency_family=DEPENDENCY_FAMILY,
                        metadata={
                            "grant_id": _text(grant.get("id")),
                            "grant_title": _text(grant.get("title")),
                            "currency": _text(grant.get("currency")).upper() or "GBP",
                            "publisher_name": dataset.publisher_name,
                            "dataset_title": dataset.title,
                            "date_field_used": "awardDate",
                        },
                    )
                )
            )

        return GrantGraphFragment(
            entities=list(entities.values()),
            relations=relations,
            grants_seen=len(grants),
            skip_reasons=skips,
        )
