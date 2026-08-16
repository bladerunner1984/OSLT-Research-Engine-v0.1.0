"""Tests for the Companies House officers/PSC connector.

Every test here corresponds to a way this connector could quietly manufacture an MD15
positive: a name-based merge, a dropped open-ended appointment, a misread date field, a
failed request read as an absence, or a discarded pagination parameter. No live network.
"""

from __future__ import annotations

from datetime import date

import httpx

from oslt_research.connectors.companies_house_officers import (
    DEPENDENCY_FAMILY,
    OFFICER_ID_NAMESPACE,
    OFFICER_RELATION_TYPE,
    PSC_ID_NAMESPACE,
    CompaniesHouseOfficersConnector,
    missing_ontology_members,
    officer_id_from_links,
    parse_ch_date,
    psc_id_from_links,
)
from oslt_research.ontology.entities import RelationType

API_KEY = "test-key-not-a-real-credential"


# --------------------------------------------------------------------------- helpers


def officer_item(
    *,
    name: str,
    officer_id: str | None,
    appointed_on: str | None = "2018-09-24",
    resigned_on: str | None = None,
    role: str = "director",
    etag: str | None = None,
) -> dict:
    item: dict = {
        "name": name,
        "officer_role": role,
        "appointed_on": appointed_on,
        "resigned_on": resigned_on,
        "etag": etag or name,
        "date_of_birth": {"month": 9, "year": 1974},
        "nationality": "British",
        "links": {"self": "/company/00000001/appointments/x"},
    }
    if officer_id:
        item["links"]["officer"] = {"appointments": f"/officers/{officer_id}/appointments"}
    return item


def officer_page(items: list[dict], *, total: int | None = None) -> dict:
    return {
        "kind": "officer-list",
        "items": items,
        "items_per_page": 35,
        "start_index": 0,
        "total_results": len(items) if total is None else total,
        "active_count": len(items),
        "resigned_count": 0,
    }


def psc_page(items: list[dict]) -> dict:
    return {"items": items, "items_per_page": 35, "start_index": 0, "total_results": len(items)}


def empty_page() -> dict:
    return {"items": [], "items_per_page": 35, "start_index": 0, "total_results": 0}


def connector_from(handler) -> CompaniesHouseOfficersConnector:
    transport = httpx.MockTransport(handler)
    return CompaniesHouseOfficersConnector(
        api_key=API_KEY,
        client=httpx.Client(transport=transport),
        min_interval_seconds=0.0,
    )


def routed(routes: dict[str, object]) -> CompaniesHouseOfficersConnector:
    """Route by URL substring; anything unrouted is an empty page, PSC included."""

    def handler(request: httpx.Request) -> httpx.Response:
        for fragment, body in routes.items():
            if fragment in str(request.url):
                if isinstance(body, int):
                    return httpx.Response(body, json={"error": "x"})
                return httpx.Response(200, json=body)
        return httpx.Response(200, json=empty_page())

    return connector_from(handler)


# --------------------------------------------------------------------------- parsing


def test_parse_ch_date_handles_absent_and_malformed():
    assert parse_ch_date("2018-09-24") == date(2018, 9, 24)
    assert parse_ch_date(None) is None
    assert parse_ch_date("") is None
    assert parse_ch_date("not-a-date") is None


def test_officer_id_extracted_only_from_the_links_path():
    assert officer_id_from_links(officer_item(name="A", officer_id="abc123")) == "abc123"
    assert officer_id_from_links(officer_item(name="A", officer_id=None)) is None
    assert officer_id_from_links({"links": {"officer": {"appointments": "/nope/x"}}}) is None
    assert officer_id_from_links({}) is None


def test_psc_id_extracted_from_self_link():
    item = {"links": {"self": "/company/1/persons-with-significant-control/individual/PSC1"}}
    assert psc_id_from_links(item) == "PSC1"
    assert psc_id_from_links({}) is None


# ------------------------------------------------------------------- identity / merge


def test_two_officers_with_the_same_name_are_two_entities():
    """The whole risk in one test: 'J Smith' at two companies is not one person."""

    page = officer_page(
        [
            officer_item(name="SMITH, J", officer_id="ID-ONE", etag="a"),
            officer_item(name="SMITH, J", officer_id="ID-TWO", etag="b"),
        ]
    )
    fragment = routed({"/officers": page}).harvest_company("00000001", include_psc=False)
    people = [e for e in fragment.entities if e.entity_id.startswith("CHO-")]
    assert {p.entity_id for p in people} == {"CHO-ID-ONE", "CHO-ID-TWO"}


def test_same_officer_id_across_companies_collapses_to_one_entity():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/company/00000001/officers" in url:
            return httpx.Response(
                200,
                json=officer_page([officer_item(name="BETHELL, Melissa", officer_id="SHARED")]),
            )
        if "/company/00000002/officers" in url:
            # A different published name form for the same identifier.
            return httpx.Response(
                200, json=officer_page([officer_item(name="Melissa BETHELL", officer_id="SHARED")])
            )
        return httpx.Response(200, json=empty_page())

    fragment = connector_from(handler).harvest_companies(
        ["00000001", "00000002"], include_psc=False
    )
    assert len([e for e in fragment.entities if e.entity_id.startswith("CHO-")]) == 1
    assert fragment.shared_officers() == {"CHO-SHARED": ["CH-00000001", "CH-00000002"]}


def test_officer_without_an_id_is_counted_unjoinable_not_matched_by_name():
    page = officer_page(
        [
            officer_item(name="WITH ID", officer_id="ID-ONE", etag="a"),
            officer_item(name="NO ID", officer_id=None, etag="b"),
        ]
    )
    fragment = routed({"/officers": page}).harvest_company("00000001", include_psc=False)
    assert fragment.officer_records_seen == 2
    assert fragment.officer_records_joined == 1
    assert fragment.officer_records_unjoinable == 1
    assert fragment.skip_reasons["OFFICER_ID_ABSENT_NOT_JOINABLE_BY_NAME"] == 1
    assert len(fragment.relations) == 1


def test_person_entity_keeps_no_date_of_birth_or_nationality():
    page = officer_page([officer_item(name="SMITH, J", officer_id="ID-ONE")])
    fragment = routed({"/officers": page}).harvest_company("00000001", include_psc=False)
    person = next(e for e in fragment.entities if e.entity_id == "CHO-ID-ONE")
    blob = person.model_dump_json()
    assert "date_of_birth" not in blob
    assert "1974" not in blob
    assert "nationality" not in blob
    assert person.identifiers == {OFFICER_ID_NAMESPACE: "ID-ONE"}


# ------------------------------------------------------------------------ date fields


def test_absent_resignation_means_current_not_missing():
    page = officer_page([officer_item(name="A", officer_id="ID-ONE", resigned_on=None)])
    fragment = routed({"/officers": page}).harvest_company("00000001", include_psc=False)
    relation = fragment.relations[0]
    assert relation.valid_from == date(2018, 9, 24)
    assert relation.valid_to is None
    assert relation.metadata["current"] is True
    assert relation.admitted is True


def test_resignation_date_closes_the_interval():
    page = officer_page(
        [officer_item(name="A", officer_id="ID-ONE", appointed_on="2010-01-01",
                      resigned_on="2015-06-30")]
    )
    relation = routed({"/officers": page}).harvest_company(
        "00000001", include_psc=False
    ).relations[0]
    assert (relation.valid_from, relation.valid_to) == (date(2010, 1, 1), date(2015, 6, 30))
    assert relation.metadata["current"] is False


def test_appointment_with_no_start_date_survives_but_fails_admission():
    page = officer_page([officer_item(name="A", officer_id="ID-ONE", appointed_on=None)])
    relation = routed({"/officers": page}).harvest_company(
        "00000001", include_psc=False
    ).relations[0]
    assert relation.valid_from is None
    assert relation.admitted is False
    assert "RELATION_UNDATED" in relation.admission_failures


def test_psc_notified_on_is_labelled_as_a_filing_date_not_a_start_of_control():
    item = {
        "name": "Example Holdings Limited",
        "kind": "corporate-entity-person-with-significant-control",
        "notified_on": "2023-09-12",
        "ceased": False,
        "identification": {"registration_number": "14785367"},
        "natures_of_control": ["ownership-of-shares-75-to-100-percent"],
        "links": {"self": "/company/00000001/persons-with-significant-control/c/PSCX"},
    }
    fragment = routed({"significant-control": psc_page([item])}).harvest_company("00000001")
    relation = next(
        r for r in fragment.relations if r.metadata["tie_semantics"] == "SIGNIFICANT_CONTROL"
    )
    assert relation.valid_from == date(2023, 9, 12)
    assert relation.valid_to is None
    assert relation.metadata["valid_from_is_notification_date"] is True


def test_psc_ceased_on_closes_the_control_interval():
    item = {
        "name": "Old Holdco Inc",
        "kind": "corporate-entity-person-with-significant-control",
        "notified_on": "2016-04-06",
        "ceased_on": "2018-04-06",
        "ceased": True,
        "identification": {"registration_number": "00099999"},
        "links": {"self": "/company/00000001/persons-with-significant-control/c/PSCY"},
    }
    fragment = routed({"significant-control": psc_page([item])}).harvest_company("00000001")
    relation = next(
        r for r in fragment.relations if r.metadata["tie_semantics"] == "SIGNIFICANT_CONTROL"
    )
    assert relation.valid_to == date(2018, 4, 6)
    assert relation.metadata["ceased_flag"] is True


# ------------------------------------------------------------------------------- PSC


def test_individual_psc_gets_its_own_namespace_and_is_never_an_officer_id():
    item = {
        "name": "Mr J Smith",
        "kind": "individual-person-with-significant-control",
        "notified_on": "2020-01-01",
        "links": {"self": "/company/00000001/persons-with-significant-control/individual/PSC1"},
    }
    fragment = routed({"significant-control": psc_page([item])}).harvest_company("00000001")
    person = next(e for e in fragment.entities if e.entity_id == "CHP-PSC1")
    assert person.identifiers == {PSC_ID_NAMESPACE: "PSC1"}
    assert OFFICER_ID_NAMESPACE not in person.identifiers
    assert fragment.psc_individual_records == 1


def test_corporate_psc_without_registration_number_is_unjoinable():
    item = {
        "name": "Groupay Inc",
        "kind": "corporate-entity-person-with-significant-control",
        "notified_on": "2016-04-06",
        "identification": {"legal_form": "Corporation"},
        "links": {"self": "/company/00000001/persons-with-significant-control/c/PSCZ"},
    }
    fragment = routed({"significant-control": psc_page([item])}).harvest_company("00000001")
    assert fragment.psc_corporate_records == 1
    assert fragment.psc_records_unjoinable == 1
    assert fragment.skip_reasons["PSC_CORPORATE_WITHOUT_REGISTRATION_NUMBER"] == 1
    assert not [
        r for r in fragment.relations if r.metadata["tie_semantics"] == "SIGNIFICANT_CONTROL"
    ]


def test_corporate_psc_of_itself_is_skipped_not_a_self_loop():
    item = {
        "name": "Itself Ltd",
        "kind": "corporate-entity-person-with-significant-control",
        "notified_on": "2020-01-01",
        "identification": {"registration_number": "00000001"},
        "links": {"self": "/company/00000001/persons-with-significant-control/c/PSCS"},
    }
    fragment = routed({"significant-control": psc_page([item])}).harvest_company("00000001")
    assert fragment.skip_reasons["PSC_SELF_REFERENCE"] == 1
    assert fragment.relations == []


# --------------------------------------------------------------- failure vs absence


def test_http_404_is_unavailable_not_zero_officers():
    fragment = routed({"/officers": 404}).harvest_company("00000001", include_psc=False)
    assert fragment.companies_unavailable == {"00000001": "UNAVAILABLE_HTTP_404"}
    assert fragment.companies_empty_unconfirmed == []
    assert fragment.entities == []


def test_http_429_is_unavailable_not_zero_officers():
    fragment = routed({"/officers": 429}).harvest_company("00000001", include_psc=False)
    assert fragment.companies_unavailable["00000001"] == "UNAVAILABLE_HTTP_429"


def test_empty_officer_list_is_recorded_as_unconfirmed_not_as_no_officers():
    """Verified live: an unknown company number returns 200 with an empty list."""

    fragment = routed({}).harvest_company("99999999", include_psc=False)
    assert fragment.companies_empty_unconfirmed == ["99999999"]
    assert fragment.companies_unavailable == {}
    assert fragment.officer_records_seen == 0


# ------------------------------------------------------------------------ pagination


def test_pagination_is_followed_when_start_index_returns_different_items():
    def handler(request: httpx.Request) -> httpx.Response:
        if "significant-control" in str(request.url):
            return httpx.Response(200, json=empty_page())
        start = int(request.url.params.get("start_index", 0))
        first = officer_item(name="A", officer_id="ID-A", etag="a")
        second = officer_item(name="B", officer_id="ID-B", etag="b")
        items = [first] if start == 0 else ([second] if start == 1 else [])
        return httpx.Response(200, json={**officer_page(items, total=2), "start_index": start})

    connector = connector_from(handler)
    fragment = connector.harvest_company("00000001", include_psc=False, page_size=1)
    assert fragment.pagination_honoured is True
    assert fragment.officer_records_joined == 2
    assert {e.entity_id for e in fragment.entities if e.entity_id.startswith("CHO-")} == {
        "CHO-ID-A",
        "CHO-ID-B",
    }


def test_pagination_silently_discarded_is_detected_and_not_duplicated():
    """The failure two other connectors in this project shipped: page one, forever."""

    page = officer_page([officer_item(name="A", officer_id="ID-A", etag="a")], total=99)

    def handler(request: httpx.Request) -> httpx.Response:
        if "significant-control" in str(request.url):
            return httpx.Response(200, json=empty_page())
        return httpx.Response(200, json=page)

    fragment = connector_from(handler).harvest_company(
        "00000001", include_psc=False, page_size=1
    )
    assert fragment.pagination_honoured is False
    assert fragment.officer_records_seen == 1


def test_start_index_and_items_per_page_are_actually_sent():
    seen: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        return httpx.Response(200, json=empty_page())

    connector_from(handler).fetch_officers("00000001", page_size=7)
    assert seen[0]["items_per_page"] == "7"
    assert seen[0]["start_index"] == "0"


# ------------------------------------------------------------- appointments / shape


def test_officer_appointments_reverse_index_produces_one_person_many_orgs():
    payload = {
        "name": "Melissa BETHELL",
        "total_results": 2,
        "items_per_page": 35,
        "start_index": 0,
        "items": [
            {
                "name": "Melissa BETHELL",
                "officer_role": "director",
                "appointed_on": "2025-09-01",
                "resigned_on": None,
                "etag": "a",
                "appointed_to": {
                    "company_name": "ALPHA LIMITED",
                    "company_number": "01844327",
                    "company_status": "active",
                },
            },
            {
                "name": "Melissa BETHELL",
                "officer_role": "director",
                "appointed_on": "2024-01-31",
                "resigned_on": None,
                "etag": "b",
                "appointed_to": {
                    "company_name": "BETA LIMITED",
                    "company_number": "08038055",
                    "company_status": "active",
                },
            },
        ],
    }
    fragment = routed({"/appointments": payload}).harvest_officer_appointments("OFFICER-1")
    assert fragment.officer_records_joined == 2
    assert fragment.shared_officers() == {"CHO-OFFICER-1": ["CH-01844327", "CH-08038055"]}
    assert all(r.relation_type is OFFICER_RELATION_TYPE for r in fragment.relations)


def test_appointment_without_a_company_number_is_unjoinable():
    payload = {
        "items": [{"name": "X", "officer_role": "director", "appointed_on": "2020-01-01",
                   "etag": "a", "appointed_to": {"company_name": "NO NUMBER LTD"}}],
        "total_results": 1,
        "items_per_page": 35,
        "start_index": 0,
    }
    fragment = routed({"/appointments": payload}).harvest_officer_appointments("OFFICER-1")
    assert fragment.officer_records_unjoinable == 1
    assert fragment.relations == []


def test_appointments_failure_is_unavailable_not_empty():
    fragment = routed({"/appointments": 500}).harvest_officer_appointments("OFFICER-1")
    assert fragment.companies_unavailable == {"officer:OFFICER-1": "UNAVAILABLE_HTTP_500"}
    assert fragment.entities == []


# ---------------------------------------------------------------- ontology + wiring


def test_officer_edges_use_the_real_relation_type_with_no_substitution_note():
    page = officer_page([officer_item(name="A", officer_id="ID-ONE")])
    relation = routed({"/officers": page}).harvest_company(
        "00000001", include_psc=False
    ).relations[0]
    assert relation.relation_type is RelationType.HOLDS_OFFICE_AT
    assert relation.metadata["tie_semantics"] == "PERSONNEL_APPOINTMENT_OFFICER"
    assert "relation_type_is_a_substitute" not in relation.metadata


def test_missing_ontology_members_are_declared_not_invented():
    # Every member this connector needed has been added to the ontology, so the
    # declaration is now empty. It remains a live check: if a future connector change
    # needs a member that does not exist, it must be declared here, not invented.
    assert missing_ontology_members() == ()


def test_everything_shares_one_dependency_family():
    page = officer_page([officer_item(name="A", officer_id="ID-ONE")])
    fragment = routed({"/officers": page}).harvest_company("00000001", include_psc=False)
    assert {e.dependency_family for e in fragment.entities} == {DEPENDENCY_FAMILY}
    assert {r.dependency_family for r in fragment.relations} == {DEPENDENCY_FAMILY}


def test_organisation_carries_a_strong_companies_house_identifier():
    page = officer_page([officer_item(name="A", officer_id="ID-ONE")])
    fragment = routed({"/officers": page}).harvest_company(
        "00000001", company_name="Alpha Limited", include_psc=False
    )
    org = next(e for e in fragment.entities if e.entity_id == "CH-00000001")
    assert org.strong_identifiers() == {("companies_house", "00000001")}
    assert org.admitted is True


def test_request_uses_basic_auth_with_empty_password_and_never_leaks_the_key_into_the_url():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=empty_page())

    connector_from(handler).fetch_officers("00000001")
    request = captured[0]
    assert request.headers["Authorization"].startswith("Basic ")
    assert API_KEY not in str(request.url)


def test_summary_reports_the_join_counts_a_bounds_statement_needs():
    page = officer_page(
        [
            officer_item(name="A", officer_id="ID-A", etag="a"),
            officer_item(name="B", officer_id=None, etag="b"),
        ]
    )
    summary = routed({"/officers": page}).harvest_company(
        "00000001", include_psc=False
    ).summary()
    assert summary["officer_records_seen"] == 2
    assert summary["officer_records_joined_on_strong_identifier"] == 1
    assert summary["officer_records_unjoinable"] == 1


# ------------------------------------------------- identifier tier: no name merges
#
# `ch_officer_id` / `ch_psc_id` were added to STRONG_IDENTIFIER_NAMESPACES. That widens
# what can count as a bridge, which makes the MX09 disposition EASIER to overturn. It
# must NOT open a name-based merge: the whole disposition rests on the fact that every
# historical MD15 positive here died once name-only joins were disallowed.


def _person_entity(entity_id: str, name: str, officer_id: str):
    from oslt_research.domain.enums import AccessClass, SourceStatus
    from oslt_research.domain.models import ProvenanceRecord
    from oslt_research.ontology.entities import (
        EntityRole,
        InstitutionalEntity,
        SystemDomain,
    )

    return InstitutionalEntity(
        entity_id=entity_id,
        canonical_name=name,
        roles=[EntityRole.NATURAL_PERSON],
        system_domain=SystemDomain.UNKNOWN,
        jurisdiction="UK",
        identifiers={OFFICER_ID_NAMESPACE: officer_id},
        provenance=ProvenanceRecord(
            source_id="DS_COMPANIES_HOUSE_OFFICERS",
            source_uri="https://api.company-information.service.gov.uk/",
            retrieval_query=entity_id,
            field_or_document_locator=entity_id,
            checksum_sha256="0" * 64,
            access_class=AccessClass.OPEN,
            licence_or_approval="OGL_v3_COMPANIES_HOUSE",
            transformation_ids=["CH_APPOINTMENT_TO_INSTITUTIONAL_RELATION_V1"],
            codebook_or_schema_ref="companies-house:public-data-api:officers+psc",
        ),
        source_status=SourceStatus.VERIFIED,
        dependency_family=DEPENDENCY_FAMILY,
    )


def test_identical_names_with_different_officer_ids_never_merge_at_strong_identifier():
    from oslt_research.ontology.graph import InstitutionalOntologyGraph, ResolutionTier

    graph = InstitutionalOntologyGraph()
    graph.add_entity(_person_entity("CHO-ID-ONE", "JOHN ANDREW SMITH", "ID-ONE"))
    graph.add_entity(_person_entity("CHO-ID-TWO", "JOHN ANDREW SMITH", "ID-TWO"))

    merged = graph.resolve_duplicates(minimum_tier=ResolutionTier.STRONG_IDENTIFIER)
    assert merged == {}
    canonical, tally = graph._canonical_map(ResolutionTier.STRONG_IDENTIFIER)
    assert canonical["CHO-ID-ONE"] != canonical["CHO-ID-TWO"]
    assert tally == {}


def test_same_officer_id_collapses_even_when_names_differ():
    from oslt_research.ontology.graph import InstitutionalOntologyGraph, ResolutionTier

    graph = InstitutionalOntologyGraph()
    # Companies House prints the same person's name differently across filings.
    graph.add_entity(_person_entity("CHO-ID-ONE", "JOHN A SMITH", "ID-ONE"))
    graph.add_entity(_person_entity("CHO-ID-ONE-ALT", "SMITH, John Andrew", "ID-ONE"))

    merged = graph.resolve_duplicates(minimum_tier=ResolutionTier.STRONG_IDENTIFIER)
    assert list(merged.values()) == [["CHO-ID-ONE", "CHO-ID-ONE-ALT"]]
    canonical, tally = graph._canonical_map(ResolutionTier.STRONG_IDENTIFIER)
    assert canonical["CHO-ID-ONE"] == canonical["CHO-ID-ONE-ALT"]
    assert tally == {ResolutionTier.STRONG_IDENTIFIER.value: 1}


def test_officer_id_and_psc_id_are_not_interchangeable():
    """A director and a PSC with the same raw id string are still two namespaces."""
    from oslt_research.ontology.graph import InstitutionalOntologyGraph, ResolutionTier

    officer = _person_entity("CHO-SHARED", "A PERSON", "SHARED")
    psc = _person_entity("CHP-SHARED", "A PERSON", "SHARED")
    psc = psc.model_copy(update={"identifiers": {PSC_ID_NAMESPACE: "SHARED"}})

    graph = InstitutionalOntologyGraph()
    graph.add_entity(officer)
    graph.add_entity(psc)
    assert graph.resolve_duplicates(minimum_tier=ResolutionTier.STRONG_IDENTIFIER) == {}


def test_inverted_interval_is_emitted_undated_and_refused_not_dropped():
    """A PSC can cease before the company files the notification. Observed live.

    The edge must survive into the fragment (so it is counted and visible) while being
    refused admission, rather than being dropped or given an invented start date.
    """
    page = officer_page(
        [officer_item(name="A", officer_id="ID-ONE",
                      appointed_on="2020-05-01", resigned_on="2019-01-01")]
    )
    fragment = routed({"/officers": page}).harvest_company("00000001", include_psc=False)
    relation = fragment.relations[0]
    assert relation.valid_from is None and relation.valid_to is None
    assert relation.admitted is False
    assert "RELATION_UNDATED" in relation.admission_failures
    inverted = relation.metadata["interval_inverted_at_source"]
    assert inverted["source_valid_from"] == "2020-05-01"
    assert inverted["source_valid_to"] == "2019-01-01"
    assert relation.metadata["current"] is False
