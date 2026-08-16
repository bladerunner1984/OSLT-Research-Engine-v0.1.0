"""Companies House officers and persons with significant control (PSC).

WHY THIS EXISTS
---------------
`docs/COUPLING_READJUDICATION.md` favours MX09 (isolated processes) over MD15
(structural coupling) on the loaded graph: not one connected component mixes relation
types. The re-adjudication names its own first bound - **no board or personnel overlap
data is loaded**. Two organisations with no funding or contract edge between them may
still share a director or a controlling person, and that is precisely the tie MD15 would
predict. This connector exists to make MX09 falsifiable, not to decorate it.

WHAT IT WILL AND WILL NOT ASSERT
--------------------------------
Only "who holds which role at which organisation, and between which dates". Nothing is
retained that a coupling test does not need: no date of birth (see below), no address,
no nationality, no occupation. Directorships and significant control are published so
they can be scrutinised; that mandate covers the appointment, not the person.

Two people are the same person here only when Companies House says so with its own
identifier. Three MD15 positives in this project died on name-based merges, which is why
`assess_coupling` runs at STRONG_IDENTIFIER. Names are carried for display and are never
a join key.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
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

from .companies_house import DEFAULT_MIN_INTERVAL_SECONDS, CompaniesHouseResolver


#: DS074 in the source register (added 2026-08). Appointments and control for UK
#: companies only. A shared director is a structural tie, not evidence of coordination.
SOURCE_ID = "DS074"

#: One register, one dependency family. An officer edge and a PSC edge both come from
#: the Companies House register, so they can never corroborate each other.
DEPENDENCY_FAMILY = "register:companies-house-officers-psc"

#: Real relation types, added to the ontology for this purpose. An officer appointment
#: is HOLDS_OFFICE_AT; significant control is CONTROLS. The precise semantics still
#: travel in relation metadata under `tie_semantics`.
OFFICER_RELATION_TYPE = RelationType.HOLDS_OFFICE_AT
CONTROL_RELATION_TYPE = RelationType.CONTROLS

#: Identifier namespaces minted here. Both are now members of
#: `STRONG_IDENTIFIER_NAMESPACES`, so `assess_coupling(..., STRONG_IDENTIFIER)` will
#: merge two person records that share one. `entity_id` is still derived from the
#: identifier, so equal ids collapse regardless of the resolver's opinion.
OFFICER_ID_NAMESPACE = "ch_officer_id"
PSC_ID_NAMESPACE = "ch_psc_id"

#: Reported by `missing_ontology_members()` rather than invented locally. Now empty:
#: every member this connector needed was added to `ontology/entities.py`.
MISSING_ONTOLOGY_MEMBERS: tuple[str, ...] = ()

#: Field meanings, established against the live API rather than assumed. Any date-looking
#: field in this project has been wrong six times; these are the four that matter.
DATE_FIELD_SEMANTICS = {
    "appointed_on": (
        "Date the appointment began. Absent on some pre-digitisation records; an "
        "appointment with no start date stays in the fragment but fails admission with "
        "RELATION_UNDATED rather than being silently dropped."
    ),
    "resigned_on": (
        "Date the appointment ENDED. ABSENT MEANS THE OFFICER IS CURRENTLY IN OFFICE - "
        "it is an open interval, not a missing value, and must never null out the edge."
    ),
    "notified_on": (
        "Date the company NOTIFIED Companies House of the PSC. It is a filing date, not "
        "the date control began; control may long predate it. Used as valid_from because "
        "it is the only dated fact published, and labelled as such in metadata."
    ),
    "ceased_on": (
        "Date the PSC ceased to be a PSC. Absent, with `ceased` false or absent, means "
        "the control is current."
    ),
}


def parse_ch_date(value: Any) -> date | None:
    """Parse a Companies House `YYYY-MM-DD`. Returns None for absent or unparseable."""

    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def officer_id_from_links(item: dict[str, Any]) -> str | None:
    """Extract the Companies House officer id from `links.officer.appointments`.

    This is the ONLY admissible join key for a human across companies. The path is
    `/officers/{officer_id}/appointments`. If it is absent the record simply cannot be
    joined, and it is counted as unjoinable rather than fudged with a name.
    """

    links = item.get("links")
    if not isinstance(links, dict):
        return None
    officer = links.get("officer")
    if not isinstance(officer, dict):
        return None
    path = officer.get("appointments")
    if not isinstance(path, str):
        return None
    parts = [segment for segment in path.split("/") if segment]
    if len(parts) >= 2 and parts[0] == "officers":
        return parts[1]
    return None


def psc_id_from_links(item: dict[str, Any]) -> str | None:
    """Extract the PSC id from `links.self`.

    Verified live: PSC entries carry NO officer id. A PSC id lives in a different
    namespace from an officer id and the two are NOT interchangeable, so an individual
    PSC is never merged with a director even when the names look identical.
    """

    links = item.get("links")
    if not isinstance(links, dict):
        return None
    path = links.get("self")
    if not isinstance(path, str):
        return None
    parts = [segment for segment in path.split("/") if segment]
    return parts[-1] if parts else None


@dataclass(frozen=True)
class PageResult:
    """One paginated fetch, including the reason it stopped.

    `outcome` distinguishes the three states a caller must not conflate: data returned,
    the register returned an empty list (which is NOT proof of no officers - an unknown
    company number also returns 200 with an empty list), and the request failed
    (unknown, and never "none").
    """

    items: list[dict[str, Any]] = field(default_factory=list)
    total_results: int | None = None
    outcome: str = "OK"
    pages_fetched: int = 0
    pagination_honoured: bool | None = None
    raw_hash: str = ""

    @property
    def available(self) -> bool:
        return self.outcome in {"OK", "EMPTY_UNCONFIRMED"}


@dataclass(frozen=True)
class PersonnelFragment:
    """Entities, edges, and the counts needed to state the bounds of the result."""

    entities: list[InstitutionalEntity] = field(default_factory=list)
    relations: list[InstitutionalRelation] = field(default_factory=list)
    companies_requested: list[str] = field(default_factory=list)
    companies_unavailable: dict[str, str] = field(default_factory=dict)
    companies_empty_unconfirmed: list[str] = field(default_factory=list)
    officer_records_seen: int = 0
    officer_records_joined: int = 0
    officer_records_unjoinable: int = 0
    psc_individual_records: int = 0
    psc_corporate_records: int = 0
    psc_records_unjoinable: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)
    pagination_honoured: bool | None = None

    def shared_officers(self) -> dict[str, list[str]]:
        """Officer entity ids appearing at more than one organisation.

        This is the MD15-relevant output: an overlap here is a candidate cross-register
        bridge. It is computed only over edges whose person side was joined on a
        Companies House identifier, so a name coincidence cannot produce one.
        """

        by_person: dict[str, list[str]] = {}
        for relation in self.relations:
            if not relation.source_entity_id.startswith("CHO-"):
                continue
            targets = by_person.setdefault(relation.source_entity_id, [])
            if relation.target_entity_id not in targets:
                targets.append(relation.target_entity_id)
        return {person: orgs for person, orgs in by_person.items() if len(orgs) > 1}

    def summary(self) -> dict[str, Any]:
        return {
            "companies_requested": len(self.companies_requested),
            "companies_unavailable": dict(self.companies_unavailable),
            "companies_empty_unconfirmed": list(self.companies_empty_unconfirmed),
            "officer_records_seen": self.officer_records_seen,
            "officer_records_joined_on_strong_identifier": self.officer_records_joined,
            "officer_records_unjoinable": self.officer_records_unjoinable,
            "psc_individual_records": self.psc_individual_records,
            "psc_corporate_records": self.psc_corporate_records,
            "psc_records_unjoinable": self.psc_records_unjoinable,
            "entities": len(self.entities),
            "relations": len(self.relations),
            "shared_officers": len(self.shared_officers()),
            "pagination_honoured": self.pagination_honoured,
            "skip_reasons": dict(self.skip_reasons),
        }


def missing_ontology_members() -> tuple[str, ...]:
    """Ontology members this connector wanted and did not silently invent elsewhere."""

    return MISSING_ONTOLOGY_MEMBERS


class CompaniesHouseOfficersConnector:
    """Officer and PSC appointments as dated, role-typed edges.

    Auth, base URL and throttling are the existing `CompaniesHouseResolver` pattern,
    reused rather than re-implemented: HTTP Basic with the API key as username and an
    empty password, key from `OSLT_COMPANIES_HOUSE_API_KEY`, and a minimum interval
    between requests applied from the FIRST call. The register allows 600 requests per
    five minutes; an unthrottled run earlier in this project cost a day of access, so
    the pacing is not optional and is not applied only after a 429.
    """

    source_name = "CompaniesHouseOfficers"
    connector_version = "1"
    base_url = CompaniesHouseResolver.base_url

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: httpx.Client | None = None,
        timeout: float = 45.0,
        min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
    ):
        # Delegating construction keeps exactly one place where the key is read and one
        # place where the throttle is defined. The key is never logged or echoed.
        self._auth = CompaniesHouseResolver(
            api_key=api_key,
            client=client,
            timeout=timeout,
            min_interval_seconds=min_interval_seconds,
        )
        self._client = client
        self.timeout = timeout

    # ------------------------------------------------------------------ transport

    def _get(self, path: str, params: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._auth._throttle()
            response = client.get(
                f"{self.base_url}{path}",
                params=params,
                auth=(self._auth.api_key, ""),
                headers={"Accept": "application/json"},
            )
            if response.status_code != 200:
                return response.status_code, None
            return 200, response.json()
        finally:
            if self._client is None:
                client.close()

    def _paginate(self, path: str, *, page_size: int = 35, max_items: int = 200) -> PageResult:
        """Fetch pages via `items_per_page` / `start_index`, verifying they are honoured.

        Two connectors in this project accepted a paging parameter the API silently
        discarded, producing page one repeated. So the second page is compared with the
        first: if a genuinely different `start_index` returns the same items, paging is
        recorded as NOT honoured and the run stops rather than multiplying duplicates.
        """

        collected: list[dict[str, Any]] = []
        total: int | None = None
        pages = 0
        honoured: bool | None = None
        first_signature: tuple[str, ...] | None = None
        start_index = 0

        while len(collected) < max_items:
            status, payload = self._get(
                path, {"items_per_page": page_size, "start_index": start_index}
            )
            if status != 200 or payload is None:
                if pages == 0:
                    # A failed request is unknown, never an absence.
                    return PageResult(outcome=f"UNAVAILABLE_HTTP_{status}")
                return PageResult(
                    items=collected,
                    total_results=total,
                    outcome=f"PARTIAL_HTTP_{status}",
                    pages_fetched=pages,
                    pagination_honoured=honoured,
                    raw_hash=sha256_text(json.dumps(collected, sort_keys=True, default=str)),
                )

            items = payload.get("items")
            items = items if isinstance(items, list) else []
            if isinstance(payload.get("total_results"), int):
                total = payload["total_results"]
            pages += 1
            signature = tuple(str(item.get("etag") or item.get("name") or "") for item in items)

            if pages == 1:
                first_signature = signature
            elif signature and signature == first_signature:
                honoured = False
                break
            elif honoured is None:
                honoured = True

            if not items:
                break
            collected.extend(items)
            start_index += page_size
            if total is not None and len(collected) >= total:
                break

        outcome = "OK" if collected else "EMPTY_UNCONFIRMED"
        return PageResult(
            items=collected[:max_items],
            total_results=total,
            outcome=outcome,
            pages_fetched=pages,
            pagination_honoured=honoured,
            raw_hash=sha256_text(json.dumps(collected[:max_items], sort_keys=True, default=str)),
        )

    # ------------------------------------------------------------------ endpoints

    def fetch_officers(self, company_number: str, **kwargs: Any) -> PageResult:
        """`GET /company/{company_number}/officers`.

        Caution verified live: an UNKNOWN company number returns 200 with an empty list,
        not 404. So an empty result is `EMPTY_UNCONFIRMED`, never "this company has no
        officers".
        """

        return self._paginate(f"/company/{company_number.strip().upper()}/officers", **kwargs)

    def fetch_psc(self, company_number: str, **kwargs: Any) -> PageResult:
        """`GET /company/{company_number}/persons-with-significant-control`."""

        return self._paginate(
            f"/company/{company_number.strip().upper()}/persons-with-significant-control",
            **kwargs,
        )

    def fetch_appointments(self, officer_id: str, **kwargs: Any) -> PageResult:
        """`GET /officers/{officer_id}/appointments` - the reverse index.

        This is the endpoint that actually finds overlap: it returns every company an
        officer id is appointed to, so one request per person replaces a scan of every
        company. Each item carries `appointed_to.company_number`, a strong identifier
        for the organisation side of the edge.
        """

        return self._paginate(f"/officers/{officer_id.strip()}/appointments", **kwargs)

    # ------------------------------------------------------------------ mapping

    def _provenance(self, locator: str, raw_hash: str, uri_path: str) -> ProvenanceRecord:
        return ProvenanceRecord(
            source_id="DS_COMPANIES_HOUSE_OFFICERS",
            source_uri=f"{self.base_url}{uri_path}",
            retrieval_query=locator,
            field_or_document_locator=locator,
            checksum_sha256=raw_hash or sha256_text(locator),
            access_class=AccessClass.OPEN,
            licence_or_approval="OGL_v3_COMPANIES_HOUSE",
            transformation_ids=["CH_APPOINTMENT_TO_INSTITUTIONAL_RELATION_V1"],
            codebook_or_schema_ref="companies-house:public-data-api:officers+psc",
        )

    def _organisation(
        self, company_number: str, name: str, provenance: ProvenanceRecord
    ) -> InstitutionalEntity:
        number = company_number.strip().upper()
        return admit_entity(
            InstitutionalEntity(
                entity_id=f"CH-{number}",
                canonical_name=name.strip() or number,
                roles=[EntityRole.OTHER],
                system_domain=SystemDomain.UNKNOWN,
                jurisdiction="UK",
                identifiers={"companies_house": number},
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
            )
        )

    def _person(
        self,
        *,
        prefix: str,
        namespace: str,
        identifier: str,
        name: str,
        officer_role: str,
        provenance: ProvenanceRecord,
    ) -> InstitutionalEntity:
        """A role-typed person node.

        Deliberately thin. `date_of_birth` is dropped entirely: Companies House publishes
        only month and year, on purpose, and this connector neither reconstructs a full
        date nor uses it as a matching key - so it has no reason to hold it at all.
        """

        return admit_entity(
            InstitutionalEntity(
                entity_id=f"{prefix}-{identifier}",
                canonical_name=name.strip() or identifier,
                roles=[EntityRole.NATURAL_PERSON],
                system_domain=SystemDomain.UNKNOWN,
                jurisdiction="UK",
                identifiers={namespace: identifier},
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
                metadata={
                    "entity_kind": "NATURAL_PERSON",
                    "officer_role": officer_role,
                    "identity_basis": "COMPANIES_HOUSE_IDENTIFIER",
                    "name_is_not_a_join_key": True,
                },
            )
        )

    def _appointment_relation(
        self,
        *,
        person_id: str,
        organisation_id: str,
        valid_from: date | None,
        valid_to: date | None,
        officer_role: str,
        tie_semantics: str,
        relation_type: RelationType,
        locator: str,
        provenance: ProvenanceRecord,
        extra: dict[str, Any] | None = None,
    ) -> InstitutionalRelation:
        metadata: dict[str, Any] = {
            "tie_semantics": tie_semantics,
            "officer_role": officer_role,
            # No end date means the appointment is OPEN, i.e. current. It does not mean
            # the date is missing, and it must not drop the edge.
            "current": valid_to is None,
            "date_field_semantics": DATE_FIELD_SEMANTICS,
        }
        metadata.update(extra or {})

        # Observed live: a PSC record can carry `ceased_on` EARLIER than `notified_on`,
        # because notified_on is the date the company filed, not the date control began -
        # a body can cease to be a PSC before the filing catches up. The same shape
        # appears on a few officer records. Neither date is wrong; the INTERVAL is
        # unusable, and choosing one of them as the start would invent a fact.
        #
        # So the edge is emitted UNDATED, with both source dates preserved in metadata.
        # `assess_relation_admission` then refuses it with RELATION_UNDATED. This is the
        # same treatment an appointment with no `appointed_on` already receives: the tie
        # stays visible in the fragment and countable in the coverage report, but it can
        # never contribute to a temporal-precedence claim. It is NOT silently dropped.
        if valid_from is not None and valid_to is not None and valid_to < valid_from:
            metadata["interval_inverted_at_source"] = {
                "source_valid_from": valid_from.isoformat(),
                "source_valid_to": valid_to.isoformat(),
                "treatment": (
                    "emitted undated; fails admission with RELATION_UNDATED rather than "
                    "picking a start date the register does not assert"
                ),
            }
            valid_from = None
            valid_to = None
            metadata["current"] = False

        return admit_relation(
            InstitutionalRelation(
                relation_id=f"CHAPP-{sha256_text(locator)[:16]}",
                source_entity_id=person_id,
                target_entity_id=organisation_id,
                relation_type=relation_type,
                valid_from=valid_from,
                valid_to=valid_to,
                provenance=provenance,
                source_status=SourceStatus.VERIFIED,
                dependency_family=DEPENDENCY_FAMILY,
                metadata=metadata,
            )
        )

    # ------------------------------------------------------------------ harvest

    def harvest_company(
        self,
        company_number: str,
        *,
        company_name: str = "",
        include_psc: bool = True,
        page_size: int = 35,
        max_items: int = 200,
    ) -> PersonnelFragment:
        """Officers (and optionally PSC) for one company as entities and dated edges."""

        number = company_number.strip().upper()
        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}
        unavailable: dict[str, str] = {}
        empty: list[str] = []
        seen = joined = unjoinable = 0
        psc_individual = psc_corporate = psc_unjoinable = 0

        def skip(reason: str) -> None:
            skips[reason] = skips.get(reason, 0) + 1

        officers = self.fetch_officers(number, page_size=page_size, max_items=max_items)
        if not officers.available:
            # Unknown, not an absence. No "zero officers" is implied anywhere downstream.
            unavailable[number] = officers.outcome
        else:
            if officers.outcome == "EMPTY_UNCONFIRMED":
                empty.append(number)
            org_provenance = self._provenance(
                f"company/{number}/officers", officers.raw_hash, f"/company/{number}/officers"
            )
            organisation = self._organisation(number, company_name, org_provenance)
            entities[organisation.entity_id] = organisation

            for item in officers.items:
                seen += 1
                officer_id = officer_id_from_links(item)
                if not officer_id:
                    unjoinable += 1
                    skip("OFFICER_ID_ABSENT_NOT_JOINABLE_BY_NAME")
                    continue
                joined += 1
                role = str(item.get("officer_role") or "")
                locator = f"company/{number}/officer/{officer_id}/{item.get('appointed_on')}"
                provenance = self._provenance(
                    locator, officers.raw_hash, f"/company/{number}/officers"
                )
                person = self._person(
                    prefix="CHO",
                    namespace=OFFICER_ID_NAMESPACE,
                    identifier=officer_id,
                    name=str(item.get("name") or ""),
                    officer_role=role,
                    provenance=provenance,
                )
                entities.setdefault(person.entity_id, person)
                relations.append(
                    self._appointment_relation(
                        person_id=person.entity_id,
                        organisation_id=organisation.entity_id,
                        valid_from=parse_ch_date(item.get("appointed_on")),
                        valid_to=parse_ch_date(item.get("resigned_on")),
                        officer_role=role,
                        tie_semantics="PERSONNEL_APPOINTMENT_OFFICER",
                        relation_type=OFFICER_RELATION_TYPE,
                        locator=locator,
                        provenance=provenance,
                    )
                )

        if include_psc:
            psc = self.fetch_psc(number, page_size=page_size, max_items=max_items)
            if not psc.available:
                unavailable[f"{number}:psc"] = psc.outcome
            else:
                psc_path = f"/company/{number}/persons-with-significant-control"
                organisation = entities.get(f"CH-{number}") or self._organisation(
                    number,
                    company_name,
                    self._provenance(f"company/{number}/psc", psc.raw_hash, psc_path),
                )
                entities.setdefault(organisation.entity_id, organisation)

                for item in psc.items:
                    kind = str(item.get("kind") or "")
                    identification = item.get("identification")
                    identification = identification if isinstance(identification, dict) else {}
                    registration = str(identification.get("registration_number") or "").strip()
                    is_corporate = "corporate" in kind or "legal-person" in kind

                    if is_corporate:
                        psc_corporate += 1
                        if not registration:
                            # A foreign or unregistered corporate PSC has no strong
                            # identifier. Matching it by name would be exactly the move
                            # that killed three earlier positives.
                            psc_unjoinable += 1
                            skip("PSC_CORPORATE_WITHOUT_REGISTRATION_NUMBER")
                            continue
                        controller_id = f"CH-{registration.upper()}"
                        prefix_ns: tuple[str, str] | None = None
                    else:
                        psc_individual += 1
                        psc_id = psc_id_from_links(item)
                        if not psc_id:
                            psc_unjoinable += 1
                            skip("PSC_ID_ABSENT_NOT_JOINABLE_BY_NAME")
                            continue
                        controller_id = f"CHP-{psc_id}"
                        prefix_ns = ("CHP", PSC_ID_NAMESPACE)

                    if controller_id == organisation.entity_id:
                        skip("PSC_SELF_REFERENCE")
                        continue

                    locator = f"company/{number}/psc/{controller_id}"
                    provenance = self._provenance(locator, psc.raw_hash, psc_path)
                    if prefix_ns is None:
                        controller = self._organisation(
                            registration, str(item.get("name") or ""), provenance
                        )
                    else:
                        controller = self._person(
                            prefix=prefix_ns[0],
                            namespace=prefix_ns[1],
                            identifier=controller_id.split("-", 1)[1],
                            name=str(item.get("name") or ""),
                            officer_role="person-with-significant-control",
                            provenance=provenance,
                        )
                    entities.setdefault(controller.entity_id, controller)

                    relations.append(
                        self._appointment_relation(
                            person_id=controller.entity_id,
                            organisation_id=organisation.entity_id,
                            valid_from=parse_ch_date(item.get("notified_on")),
                            valid_to=parse_ch_date(item.get("ceased_on")),
                            officer_role="person-with-significant-control",
                            tie_semantics="SIGNIFICANT_CONTROL",
                            relation_type=CONTROL_RELATION_TYPE,
                            locator=locator,
                            provenance=provenance,
                            extra={
                                "natures_of_control": list(item.get("natures_of_control") or []),
                                "valid_from_is_notification_date": True,
                                "ceased_flag": bool(item.get("ceased")),
                                # PSC ids are a different namespace from officer ids and
                                # are never merged with a director record.
                                "psc_identity_not_joinable_to_officer_id": prefix_ns is not None,
                            },
                        )
                    )

        return PersonnelFragment(
            entities=list(entities.values()),
            relations=relations,
            companies_requested=[number],
            companies_unavailable=unavailable,
            companies_empty_unconfirmed=empty,
            officer_records_seen=seen,
            officer_records_joined=joined,
            officer_records_unjoinable=unjoinable,
            psc_individual_records=psc_individual,
            psc_corporate_records=psc_corporate,
            psc_records_unjoinable=psc_unjoinable,
            skip_reasons=skips,
            pagination_honoured=officers.pagination_honoured,
        )

    def harvest_officer_appointments(
        self, officer_id: str, *, page_size: int = 35, max_items: int = 200
    ) -> PersonnelFragment:
        """Every appointment of ONE officer id - the cheapest route to overlap.

        One request per person, versus one per company. Given the 600-per-five-minutes
        budget, this is the form a coupling probe should use.
        """

        result = self.fetch_appointments(officer_id, page_size=page_size, max_items=max_items)
        if not result.available:
            return PersonnelFragment(
                companies_unavailable={f"officer:{officer_id}": result.outcome},
                pagination_honoured=result.pagination_honoured,
            )

        entities: dict[str, InstitutionalEntity] = {}
        relations: list[InstitutionalRelation] = []
        skips: dict[str, int] = {}
        companies: list[str] = []
        seen = joined = unjoinable = 0

        for item in result.items:
            seen += 1
            appointed_to = item.get("appointed_to")
            appointed_to = appointed_to if isinstance(appointed_to, dict) else {}
            number = str(appointed_to.get("company_number") or "").strip().upper()
            if not number:
                unjoinable += 1
                skips["APPOINTED_TO_COMPANY_NUMBER_ABSENT"] = (
                    skips.get("APPOINTED_TO_COMPANY_NUMBER_ABSENT", 0) + 1
                )
                continue
            joined += 1
            companies.append(number)
            role = str(item.get("officer_role") or "")
            locator = f"officers/{officer_id}/appointments/{number}/{item.get('appointed_on')}"
            provenance = self._provenance(
                locator, result.raw_hash, f"/officers/{officer_id}/appointments"
            )
            person = self._person(
                prefix="CHO",
                namespace=OFFICER_ID_NAMESPACE,
                identifier=officer_id,
                name=str(item.get("name") or ""),
                officer_role=role,
                provenance=provenance,
            )
            entities.setdefault(person.entity_id, person)
            organisation = self._organisation(
                number, str(appointed_to.get("company_name") or ""), provenance
            )
            entities.setdefault(organisation.entity_id, organisation)
            relations.append(
                self._appointment_relation(
                    person_id=person.entity_id,
                    organisation_id=organisation.entity_id,
                    valid_from=parse_ch_date(item.get("appointed_on")),
                    valid_to=parse_ch_date(item.get("resigned_on")),
                    officer_role=role,
                    tie_semantics="PERSONNEL_APPOINTMENT_OFFICER",
                    relation_type=OFFICER_RELATION_TYPE,
                    locator=locator,
                    provenance=provenance,
                    extra={"company_status": str(appointed_to.get("company_status") or "")},
                )
            )

        return PersonnelFragment(
            entities=list(entities.values()),
            relations=relations,
            companies_requested=companies,
            officer_records_seen=seen,
            officer_records_joined=joined,
            officer_records_unjoinable=unjoinable,
            skip_reasons=skips,
            pagination_honoured=result.pagination_honoured,
        )

    def harvest_companies(
        self, company_numbers: Iterable[str], **kwargs: Any
    ) -> PersonnelFragment:
        """Harvest several companies and merge, deduplicating on entity id.

        Deduplication is by entity id, which is derived from the Companies House
        identifier - so it is an identifier join, not a name join, even though the
        implementation looks like a dictionary.
        """

        return merge_fragments(
            self.harvest_company(number, **kwargs) for number in company_numbers
        )


def merge_fragments(fragments: Iterable[PersonnelFragment]) -> PersonnelFragment:
    """Combine fragments, deduplicating entities and relations on their derived ids."""

    entities: dict[str, InstitutionalEntity] = {}
    relations: dict[str, InstitutionalRelation] = {}
    requested: list[str] = []
    unavailable: dict[str, str] = {}
    empty: list[str] = []
    skips: dict[str, int] = {}
    seen = joined = unjoinable = 0
    psc_individual = psc_corporate = psc_unjoinable = 0
    honoured: bool | None = None

    for fragment in fragments:
        for entity in fragment.entities:
            entities.setdefault(entity.entity_id, entity)
        for relation in fragment.relations:
            relations.setdefault(relation.relation_id, relation)
        requested.extend(fragment.companies_requested)
        unavailable.update(fragment.companies_unavailable)
        empty.extend(fragment.companies_empty_unconfirmed)
        for reason, count in fragment.skip_reasons.items():
            skips[reason] = skips.get(reason, 0) + count
        seen += fragment.officer_records_seen
        joined += fragment.officer_records_joined
        unjoinable += fragment.officer_records_unjoinable
        psc_individual += fragment.psc_individual_records
        psc_corporate += fragment.psc_corporate_records
        psc_unjoinable += fragment.psc_records_unjoinable
        if fragment.pagination_honoured is False:
            honoured = False
        elif fragment.pagination_honoured is True and honoured is None:
            honoured = True

    return PersonnelFragment(
        entities=list(entities.values()),
        relations=list(relations.values()),
        companies_requested=requested,
        companies_unavailable=unavailable,
        companies_empty_unconfirmed=empty,
        officer_records_seen=seen,
        officer_records_joined=joined,
        officer_records_unjoinable=unjoinable,
        psc_individual_records=psc_individual,
        psc_corporate_records=psc_corporate,
        psc_records_unjoinable=psc_unjoinable,
        skip_reasons=skips,
        pagination_honoured=honoured,
    )
