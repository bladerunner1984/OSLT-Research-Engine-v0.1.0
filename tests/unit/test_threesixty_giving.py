from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from oslt_research.connectors.threesixty_giving import (
    DEPENDENCY_FAMILY,
    REGISTRY_URL,
    SKIP_FILTERED,
    SKIP_FUNDER_MISSING,
    SKIP_RECIPIENT_MISSING,
    SKIP_SELF_LOOP,
    SKIP_UNDATED,
    DatasetRef,
    ThreeSixtyGivingConnector,
    grants_from_csv,
    identifiers_from_org,
    parse_grant_date,
)
from oslt_research.ontology.entities import EntityRole, RelationType, SystemDomain

DATASET_URL = "https://example.org/grants.json"
CSV_URL = "https://example.org/grants.csv"


def dataset(url: str = DATASET_URL) -> DatasetRef:
    return DatasetRef(
        publisher_name="East Suffolk Trust",
        publisher_prefix="360G-EaST",
        title="Open Programme grants",
        download_url=url,
        modified="2026-08-06T08:50:58.000Z",
        licence="Creative Commons Attribution 4.0 International (CC BY 4.0)",
    )


def grant(**overrides) -> dict:
    """One grant shaped exactly like a live 360Giving Standard JSON entry."""

    base = {
        "id": "360G-EaST-0008G",
        "title": "Purchase and improvement of land at Needham Market",
        "description": "To purchase and restore a chalk grassland.",
        "currency": "GBP",
        "amountAwarded": 50000.0,
        "awardDate": "2026-06-05",
        # The trap: a maintenance stamp two months later than the award.
        "dateModified": "2026-08-06T08:50:58.000Z",
        "plannedDates": [{"startDate": "2026-06-30", "endDate": "2026-12-31"}],
        "fundingOrganization": [{"id": "GB-CHC-1213569", "name": "East Suffolk Trust"}],
        "recipientOrganization": [
            {
                "id": "GB-CHC-1218116",
                "name": "Chalkeith Conservation",
                "charityNumber": "1218116",
            }
        ],
    }
    base.update(overrides)
    return base


def client_for(routes: dict[str, tuple[int, str, str]]) -> httpx.Client:
    """Mock transport keyed by URL -> (status, body, content-type)."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url not in routes:
            return httpx.Response(404, text="not found")
        status, body, content_type = routes[url]
        return httpx.Response(status, text=body, headers={"content-type": content_type})

    return httpx.Client(transport=httpx.MockTransport(handler))


def harvest(grants: list[dict], **kwargs):
    body = json.dumps({"grants": grants})
    with client_for({DATASET_URL: (200, body, "application/json")}) as client:
        return ThreeSixtyGivingConnector(client=client).harvest_dataset(dataset(), **kwargs)


# ------------------------------------------------------------------- date parsing


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-06-05", date(2026, 6, 5)),
        ("2021-07-08T00:00:00Z", date(2021, 7, 8)),
        ("03/04/2020", date(2020, 4, 3)),  # UK day-first, not 3 April read as 4 March
        ("2020/03/20", date(2020, 3, 20)),
    ],
)
def test_parse_grant_date_accepts_live_formats(raw, expected):
    assert parse_grant_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "not a date", None, 20200320, {}])
def test_parse_grant_date_rejects_unusable(raw):
    assert parse_grant_date(raw) is None


# ------------------------------------------------------------------- identifiers


def test_identifiers_from_org_reads_charity_prefix():
    assert identifiers_from_org({"id": "GB-CHC-1218116", "name": "X"})["charity_number"] == "1218116"


def test_identifiers_from_org_reads_company_prefix():
    ids = identifiers_from_org({"id": "GB-COH-04600790", "name": "X"})
    assert ids["companies_house"] == "04600790"
    assert "charity_number" not in ids


def test_identifiers_from_org_prefers_explicit_fields_over_prefix():
    ids = identifiers_from_org(
        {"id": "360G-local-99", "charityNumber": "1098744", "companyNumber": "04600790"}
    )
    assert ids["charity_number"] == "1098744"
    assert ids["companies_house"] == "04600790"
    assert ids["threesixtygiving_org_id"] == "360G-local-99"


def test_identifiers_from_org_emits_nothing_when_unregistered():
    assert identifiers_from_org({"name": "Unregistered Group"}) == {}


def test_scottish_and_ni_charity_prefixes_share_the_charity_namespace():
    assert identifiers_from_org({"id": "GB-SC-SC012345"})["charity_number"] == "SC012345"
    assert identifiers_from_org({"id": "GB-NIC-101234"})["charity_number"] == "101234"


# ------------------------------------------------------------------------ mapping


def test_emits_dated_funds_edge_with_admitted_nodes():
    fragment = harvest([grant()])

    assert fragment.grants_seen == 1
    assert len(fragment.relations) == 1
    edge = fragment.relations[0]
    assert edge.relation_type is RelationType.FUNDS
    assert edge.valid_from == date(2026, 6, 5)
    assert edge.valid_to == date(2026, 12, 31)
    assert edge.amount_gbp == 50000.0
    assert edge.is_dated()
    assert edge.admitted is True
    assert edge.admission_failures == []
    assert edge.dependency_family == DEPENDENCY_FAMILY
    assert all(entity.admitted for entity in fragment.entities)


def test_award_date_is_used_not_the_last_modified_stamp():
    """`dateModified` post-dates the award; reading it would break temporal ordering."""

    edge = harvest([grant()]).relations[0]
    assert edge.valid_from == date(2026, 6, 5)
    assert edge.valid_from != date(2026, 8, 6)
    assert edge.metadata["date_field_used"] == "awardDate"


def test_undated_grant_is_skipped_with_a_reason_not_admitted():
    fragment = harvest([grant(awardDate="")])

    assert fragment.relations == []
    assert fragment.entities == []
    assert fragment.skip_reasons == {SKIP_UNDATED: 1}


def test_grant_whose_only_date_is_last_modified_is_still_skipped():
    fragment = harvest([grant(awardDate=None, dateModified="2026-08-06T08:50:58.000Z")])
    assert fragment.skip_reasons == {SKIP_UNDATED: 1}


def test_funder_is_philanthropic_and_recipient_domain_is_not_guessed():
    fragment = harvest([grant()])
    by_id = {entity.entity_id: entity for entity in fragment.entities}

    funder = by_id["360G-GB-CHC-1213569"]
    assert funder.roles == [EntityRole.PHILANTHROPIC_FUNDER]
    assert funder.system_domain is SystemDomain.PHILANTHROPIC

    recipient = by_id["360G-GB-CHC-1218116"]
    assert recipient.system_domain is SystemDomain.UNKNOWN
    assert recipient.roles == [EntityRole.OTHER]
    assert recipient.metadata["domain_source"] == "NOT_STATED_BY_SOURCE"


def test_recipient_charity_number_reaches_strong_identifiers():
    fragment = harvest([grant()])
    recipient = next(e for e in fragment.entities if e.entity_id == "360G-GB-CHC-1218116")
    assert ("charity_number", "1218116") in recipient.strong_identifiers()


def test_missing_funder_or_recipient_is_skipped():
    assert harvest([grant(fundingOrganization=[])]).skip_reasons == {SKIP_FUNDER_MISSING: 1}
    assert harvest([grant(recipientOrganization=[])]).skip_reasons == {SKIP_RECIPIENT_MISSING: 1}


def test_self_loop_is_skipped_rather_than_raising():
    fragment = harvest(
        [grant(recipientOrganization=[{"id": "GB-CHC-1213569", "name": "East Suffolk Trust"}])]
    )
    assert fragment.relations == []
    assert fragment.skip_reasons == {SKIP_SELF_LOOP: 1}


def test_non_gbp_award_leaves_amount_unset_rather_than_wrong():
    edge = harvest([grant(currency="EUR", amountAwarded=50000)]).relations[0]
    assert edge.amount_gbp is None
    assert edge.metadata["currency"] == "EUR"


def test_end_date_before_award_date_is_dropped_not_raised():
    edge = harvest(
        [grant(plannedDates=[{"startDate": "2020-01-01", "endDate": "2019-01-01"}])]
    ).relations[0]
    assert edge.valid_to is None


def test_title_filter_is_client_side_and_discriminates():
    matched = harvest([grant()], title_contains="Needham")
    missed = harvest([grant()], title_contains="dementia")

    assert len(matched.relations) == 1
    assert missed.relations == []
    assert missed.skip_reasons == {SKIP_FILTERED: 1}
    assert "CLIENT-SIDE" in matched.relations[0].provenance.retrieval_query


def test_provenance_records_the_document_stamp_not_the_award_date():
    edge = harvest([grant()]).relations[0]
    assert edge.provenance.published_at == "2026-08-06T08:50:58.000Z"
    assert edge.provenance.source_uri == DATASET_URL
    assert edge.provenance.codebook_or_schema_ref == "360giving:standard/grant"


def test_repeated_funder_is_emitted_once():
    fragment = harvest([grant(), grant(id="360G-EaST-0009G")])
    assert len(fragment.relations) == 2
    assert len(fragment.entities) == 2
    assert len({edge.relation_id for edge in fragment.relations}) == 2


def test_max_grants_caps_the_harvest():
    fragment = harvest([grant(id=f"360G-EaST-{n}") for n in range(5)], max_grants=2)
    assert fragment.grants_seen == 5
    assert len(fragment.relations) == 2


# ---------------------------------------------------------------------------- CSV

CSV_BODY = (
    "Identifier,Title,Currency,Amount awarded,Award date,"
    "Recipient Org:Name,Recipient Org:Charity Number,Recipient Org:Company Number,"
    "Funding Org:Identifier,Funding Org:Name,Last Modified\r\n"
    "360G-zing-1,Youth coaching,GBP,50000,2010-12-01,"
    "Greenhouse Sports,1098744,04600790,GB-CHC-1123456,ZING,2022-01-21T00:00:00Z\r\n"
)


def test_csv_headers_are_matched_case_insensitively():
    """Publishers disagree on capitalisation; a strict match would drop every date."""

    grants = grants_from_csv(CSV_BODY)
    assert len(grants) == 1
    assert grants[0]["awardDate"] == "2010-12-01"
    assert grants[0]["amountAwarded"] == "50000"


def test_csv_dataset_produces_the_same_edge_shape_as_json():
    with client_for({CSV_URL: (200, CSV_BODY, "text/csv")}) as client:
        fragment = ThreeSixtyGivingConnector(client=client).harvest_dataset(dataset(CSV_URL))

    assert len(fragment.relations) == 1
    edge = fragment.relations[0]
    assert edge.valid_from == date(2010, 12, 1)
    assert edge.relation_type is RelationType.FUNDS
    assert edge.admitted is True

    recipient = next(e for e in fragment.entities if e.canonical_name == "Greenhouse Sports")
    assert recipient.identifiers["charity_number"] == "1098744"
    assert recipient.identifiers["companies_house"] == "04600790"
    assert recipient.system_domain is SystemDomain.UNKNOWN


def test_csv_last_modified_column_never_becomes_the_edge_date():
    with client_for({CSV_URL: (200, CSV_BODY, "text/csv")}) as client:
        edge = ThreeSixtyGivingConnector(client=client).harvest_dataset(dataset(CSV_URL)).relations[0]
    assert edge.valid_from == date(2010, 12, 1)
    assert edge.valid_from.year != 2022


# ----------------------------------------------------------------------- registry

REGISTRY_BODY = json.dumps(
    [
        {
            "title": "Open Programme grants",
            "modified": "2025-02-11T14:13:07.000+0000",
            "license_name": "CC BY 4.0",
            "publisher": {"name": "East Suffolk Trust", "prefix": "360G-EaST"},
            "distribution": [{"downloadURL": DATASET_URL, "title": "Grants"}],
        },
        {
            "title": "Council grants",
            "modified": "2024-01-01",
            "publisher": {"name": "Barnet Council", "prefix": "360G-barnet"},
            "distribution": [{"downloadURL": CSV_URL, "title": "Grants CSV"}],
        },
        {
            "title": "Spreadsheet only",
            "publisher": {"name": "Haberdashers", "prefix": "360G-habs"},
            "distribution": [{"downloadURL": "https://example.org/grants.xlsx"}],
        },
    ]
)


def registry_connector() -> tuple[ThreeSixtyGivingConnector, httpx.Client]:
    client = client_for({REGISTRY_URL: (200, REGISTRY_BODY, "application/json")})
    return ThreeSixtyGivingConnector(client=client), client


def test_registry_lists_machine_readable_distributions_only():
    connector, client = registry_connector()
    with client:
        datasets = connector.fetch_registry()
    urls = {item.download_url for item in datasets}
    assert urls == {DATASET_URL, CSV_URL}


def test_registry_publisher_filter_is_client_side_and_discriminates():
    """Two different filters must return different sets, not the same full list."""

    connector, client = registry_connector()
    with client:
        suffolk = connector.fetch_registry(publisher_contains="Suffolk")
        barnet = connector.fetch_registry(publisher_contains="Barnet")
        nothing = connector.fetch_registry(publisher_contains="no such publisher")

    assert [item.publisher_name for item in suffolk] == ["East Suffolk Trust"]
    assert [item.publisher_name for item in barnet] == ["Barnet Council"]
    assert nothing == []


def test_registry_format_filter_narrows_to_json():
    connector, client = registry_connector()
    with client:
        datasets = connector.fetch_registry(formats=("json",))
    assert [item.download_url for item in datasets] == [DATASET_URL]


def test_registry_carries_the_document_modified_stamp():
    connector, client = registry_connector()
    with client:
        found = connector.fetch_registry(publisher_contains="Suffolk")[0]
    assert found.modified == "2025-02-11T14:13:07.000+0000"
    assert found.licence == "CC BY 4.0"


def test_unparseable_dataset_body_yields_an_empty_fragment_not_an_exception():
    with client_for({DATASET_URL: (200, "<html>challenge</html>", "text/html")}) as client:
        fragment = ThreeSixtyGivingConnector(client=client).harvest_dataset(dataset())
    assert fragment.grants_seen == 0
    assert fragment.relations == []


def test_transport_error_on_dataset_propagates():
    """A failed fetch means we have nothing, and that must surface rather than look empty."""

    with client_for({}) as client:
        with pytest.raises(httpx.HTTPStatusError):
            ThreeSixtyGivingConnector(client=client).harvest_dataset(dataset())
