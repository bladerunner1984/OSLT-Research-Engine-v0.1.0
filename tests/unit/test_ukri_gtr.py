from __future__ import annotations

from datetime import date

import httpx
import pytest

from oslt_research.connectors.ukri_gtr import (
    DEPENDENCY_FAMILY,
    RECIPIENT_UNRESOLVED_LOOKUP_DISABLED,
    RECIPIENT_UNRESOLVED_LOOKUP_FAILED,
    RECIPIENT_UNRESOLVED_NO_LEAD_ORGANISATION,
    UkriGatewayToResearchConnector,
    clean_text,
    epoch_millis_to_date,
    projects_from_payload,
)
from oslt_research.ontology.entities import EntityRole, RelationType, SystemDomain

FUNDER_ID = "12E03F45-B517-4D83-A182-3D142D1A471A"
ORG_ID = "6380BFC8-096F-4D6F-8151-869D08B3288F"
PROJECT_ID = "03E282E3-DFF0-4794-ADE0-00B1A7BA0ED8"
RESOURCE_URL = "http://gtr.ukri.org/api/projects?ref=710397"

# 2014-01-01 and 2015-03-30T23:00Z (a BST-local end date) in epoch milliseconds, as
# GtR publishes them. The end deliberately straddles UTC midnight to pin the timezone.
START_MS = 1388534400000
END_MS = 1427756400000


def project(**overrides) -> dict:
    """One project shaped exactly like the live `projectsBean.projects[]` entry."""

    base = {
        "id": PROJECT_ID,
        "resourceUrl": RESOURCE_URL,
        "title": "Mobile Analytics &amp; Predictive Content",
        "status": "Closed",
        "grantReference": "710397",
        "grantCategory": "GRD Proof of Concept",
        "fund": {
            "valuePounds": 90461,
            "start": START_MS,
            "end": END_MS,
            "funder": {
                "id": FUNDER_ID,
                "resourceUrl": f"http://gtr.ukri.org/api/organisation/{FUNDER_ID}",
                "name": "Innovate UK",
            },
            "type": "INCOME_ACTUAL",
        },
    }
    base.update(overrides)
    return base


def search_body(*projects: dict) -> dict:
    return {
        "headerData": {"lastRefreshDate": "06 Jul 2026"},
        "projectsBean": {"projects": list(projects)},
    }


def detail_body(organisation: dict | None) -> dict:
    composition: dict = {"project": {"id": PROJECT_ID}, "organisationRoles": []}
    if organisation is not None:
        composition["leadResearchOrganisation"] = organisation
    return {"projectOverview": {"projectComposition": composition}}


LEAD_ORGANISATION = {
    "id": ORG_ID,
    "resourceUrl": f"http://gtr.ukri.org/api/organisation/{ORG_ID}",
    "name": "University of Example &amp; Sons",
    "address": {"postCode": "W1T 6ED", "region": "London"},
    "typeInd": "P",
}


def connector_for(
    *projects: dict,
    detail: dict | None = None,
    detail_status: int = 200,
    resolve_recipients: bool = True,
    calls: list[httpx.Request] | None = None,
) -> UkriGatewayToResearchConnector:
    """Build a connector whose transport is a mock. No test may touch the network."""

    body = search_body(*projects)
    detail_payload = detail_body(LEAD_ORGANISATION) if detail is None else detail

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        if "ref=" in str(request.url):
            if detail_status != 200:
                return httpx.Response(detail_status, json={"error": "Not Found"})
            return httpx.Response(200, json=detail_payload)
        return httpx.Response(200, json=body)

    return UkriGatewayToResearchConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        resolve_recipients=resolve_recipients,
    )


# ---------------------------------------------------------------- shared helpers


@pytest.mark.parametrize(
    "value,expected",
    [
        (START_MS, date(2014, 1, 1)),
        (str(START_MS), date(2014, 1, 1)),
        (None, None),
        ("", None),
        ("nonsense", None),
        (True, None),
    ],
)
def test_epoch_millis_to_date(value, expected):
    assert epoch_millis_to_date(value) == expected


def test_clean_text_unescapes_gtr_html_entities():
    assert clean_text("  Analytics &amp; Content ") == "Analytics & Content"
    assert clean_text(None) == ""


def test_projects_from_payload_tolerates_shape_and_junk():
    assert len(projects_from_payload(search_body(project()))) == 1
    assert projects_from_payload({"projectsBean": {"project": [project()]}})
    assert projects_from_payload({"unexpected": 1}) == []


# ------------------------------------------------------- resolved recipient path


def test_resolved_recipient_produces_a_dated_funds_edge():
    fragment = connector_for(project()).harvest_grants()

    assert fragment.projects_seen == 1
    assert fragment.recipients_resolved == 1 and fragment.recipients_unresolved == 0
    assert len(fragment.relations) == 1

    relation = fragment.relations[0]
    assert relation.admitted is True
    assert relation.admission_failures == []
    assert relation.relation_type is RelationType.FUNDS
    assert relation.valid_from == date(2014, 1, 1)
    assert relation.valid_to == date(2015, 3, 30)
    assert relation.amount_gbp == pytest.approx(90461.0)
    assert relation.dependency_family == DEPENDENCY_FAMILY
    assert relation.metadata["recipient_resolved"] is True
    assert relation.metadata["target_node_kind"] == "organisation"
    assert relation.source_entity_id == f"GTR-{FUNDER_ID}"
    assert relation.target_entity_id == f"GTR-{ORG_ID}"


def test_funder_and_recipient_carry_the_required_roles_and_domains():
    fragment = connector_for(project()).harvest_grants()
    by_id = {entity.entity_id: entity for entity in fragment.entities}

    funder = by_id[f"GTR-{FUNDER_ID}"]
    assert funder.roles == [EntityRole.PUBLIC_FUNDER]
    assert funder.system_domain is SystemDomain.POLICY
    assert funder.canonical_name == "Innovate UK"
    assert funder.admitted is True

    recipient = by_id[f"GTR-{ORG_ID}"]
    assert recipient.roles == [EntityRole.ACADEMIC_BODY]
    assert recipient.system_domain is SystemDomain.ACADEMIC
    assert recipient.canonical_name == "University of Example & Sons"
    assert recipient.metadata["gtr_organisation_type_ind"] == "P"


def test_gtr_organisation_id_is_kept_weak_and_cannot_merge_entities():
    """A GtR UUID is not a register number, so it must not act as a strong identifier."""

    fragment = connector_for(project()).harvest_grants()
    recipient = next(e for e in fragment.entities if e.entity_id == f"GTR-{ORG_ID}")
    assert recipient.identifiers["gtr_organisation_id"] == ORG_ID
    assert recipient.strong_identifiers() == set()


def test_provenance_points_at_the_project_resource_over_tls():
    relation = connector_for(project()).harvest_grants().relations[0]
    assert relation.provenance.source_uri == "https://gtr.ukri.org/api/projects?ref=710397"
    assert relation.provenance.field_or_document_locator == "710397"
    assert relation.provenance.published_at == "06 Jul 2026"
    assert relation.provenance.retrieval_query == "page=1 size=25 (no server-side search)"


# ----------------------------------------------------- unresolved recipient path


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"detail_status": 404}, RECIPIENT_UNRESOLVED_LOOKUP_FAILED),
        ({"detail": detail_body(None)}, RECIPIENT_UNRESOLVED_NO_LEAD_ORGANISATION),
        ({"resolve_recipients": False}, RECIPIENT_UNRESOLVED_LOOKUP_DISABLED),
    ],
)
def test_unresolved_recipient_falls_back_to_a_visible_project_edge(kwargs, reason):
    fragment = connector_for(project(), **kwargs).harvest_grants()

    assert fragment.recipients_resolved == 0 and fragment.recipients_unresolved == 1
    relation = fragment.relations[0]
    assert relation.admitted is True
    assert relation.relation_type is RelationType.GRANTS_TO
    assert relation.target_entity_id == f"GTR-PROJECT-{PROJECT_ID}"
    assert relation.metadata["recipient_resolved"] is False
    assert relation.metadata["recipient_unresolved_reason"] == reason
    assert relation.metadata["target_node_kind"] == "project"
    assert fragment.skip_reasons[f"RECIPIENT_UNRESOLVED_{reason}"] == 1

    target = next(e for e in fragment.entities if e.entity_id.startswith("GTR-PROJECT-"))
    assert target.roles == [EntityRole.OTHER]
    assert target.metadata["recipient_resolved"] is False
    assert target.identifiers["gtr_grant_reference"] == "710397"
    assert target.canonical_name == "Mobile Analytics & Predictive Content"


def test_disabling_resolution_issues_no_project_lookup_at_all():
    calls: list[httpx.Request] = []
    connector_for(project(), resolve_recipients=False, calls=calls).harvest_grants()
    assert len(calls) == 1
    assert "ref=" not in str(calls[0].url)


def test_a_failed_lookup_does_not_abort_the_rest_of_the_page():
    other = project(id="OTHER-ID", grantReference="999999", resourceUrl="")
    fragment = connector_for(project(), other).harvest_grants()
    assert len(fragment.relations) == 2
    assert fragment.recipients_resolved == 1 and fragment.recipients_unresolved == 1


def test_recipient_is_never_guessed_from_a_similar_name():
    """The unresolved branch must not reach for any organisation-shaped fallback."""

    detail = detail_body(None)
    detail["projectOverview"]["projectComposition"]["organisationRoles"] = [
        {"id": ORG_ID, "name": "University of Example", "roles": [{"name": "PARTICIPANT"}]}
    ]
    fragment = connector_for(project(), detail=detail).harvest_grants()
    assert fragment.relations[0].target_entity_id.startswith("GTR-PROJECT-")
    assert not any(e.entity_id == f"GTR-{ORG_ID}" for e in fragment.entities)


# --------------------------------------------------------------- refusal paths


def test_undated_grant_is_skipped_rather_than_admitted_undated():
    undated = project(fund={"valuePounds": 1, "start": None, "end": None,
                            "funder": {"id": FUNDER_ID, "name": "Innovate UK"}})
    fragment = connector_for(undated).harvest_grants()
    assert fragment.relations == []
    assert fragment.skip_reasons["GRANT_UNDATED"] == 1


def test_missing_funder_is_skipped():
    fragment = connector_for(project(fund={"start": START_MS})).harvest_grants()
    assert fragment.relations == []
    assert fragment.skip_reasons["FUNDER_MISSING"] == 1


def test_end_before_start_is_dropped_rather_than_raising():
    backwards = project(fund={"valuePounds": 10, "start": END_MS, "end": START_MS,
                              "funder": {"id": FUNDER_ID, "name": "Innovate UK"}})
    relation = connector_for(backwards).harvest_grants().relations[0]
    assert relation.valid_from == date(2015, 3, 30)
    assert relation.valid_to is None


def test_self_funding_project_is_skipped_not_emitted_as_a_self_loop():
    organisation = dict(LEAD_ORGANISATION, id=FUNDER_ID)
    fragment = connector_for(project(), detail=detail_body(organisation)).harvest_grants()
    assert fragment.relations == []
    assert fragment.skip_reasons["FUNDER_IS_RECIPIENT"] == 1


@pytest.mark.parametrize("value", [None, "90461", -5])
def test_non_numeric_or_negative_value_is_not_recorded_as_pounds(value):
    payload = project(fund={"valuePounds": value, "start": START_MS, "end": END_MS,
                            "funder": {"id": FUNDER_ID, "name": "Innovate UK"}})
    assert connector_for(payload).harvest_grants().relations[0].amount_gbp is None


def test_empty_feed_is_safe():
    fragment = connector_for().harvest_grants()
    assert fragment.relations == [] and fragment.projects_seen == 0


def test_search_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    connector = UkriGatewayToResearchConnector(client=httpx.Client(transport=transport))
    with pytest.raises(httpx.HTTPStatusError):
        connector.harvest_grants()


# ------------------------------------------------------------------ MD15 wiring


def test_grant_family_and_tie_type_differ_from_both_procurement_connectors():
    """MD15 needs a component built from more than one relation type and family."""

    from oslt_research.connectors.contracts_finder import (
        DEPENDENCY_FAMILY as CONTRACTS_FINDER_FAMILY,
    )
    from oslt_research.connectors.find_a_tender import DEPENDENCY_FAMILY as FIND_A_TENDER_FAMILY

    assert DEPENDENCY_FAMILY not in {CONTRACTS_FINDER_FAMILY, FIND_A_TENDER_FAMILY}

    types = {r.relation_type for r in connector_for(project()).harvest_grants().relations}
    assert types == {RelationType.FUNDS}
    assert RelationType.CONTRACTS_WITH not in types


def test_title_contains_filters_the_retrieved_page():
    matching = {**project(), "title": "Gender identity in adolescence"}
    fragment = connector_for(project(), matching).harvest_grants(title_contains="gender identity")
    assert fragment.skip_reasons.get("TITLE_FILTER_EXCLUDED") == 1


def test_connector_rejects_a_server_side_term_it_cannot_honour():
    """GtR ignores q, term and searchTerm alike, so accepting one would mislead."""

    with pytest.raises(TypeError):
        connector_for(project()).harvest_grants(term="quantum")
