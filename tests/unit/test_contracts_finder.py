from __future__ import annotations

from datetime import date

import httpx
import pytest

from oslt_research.connectors.contracts_finder import (
    DEPENDENCY_FAMILY,
    ContractsFinderConnector,
)
from oslt_research.ontology.entities import EntityRole, RelationType


def payload(*releases: dict) -> dict:
    return {"version": "1.1", "releases": list(releases)}


def release(
    *,
    ocid: str = "ocds-1",
    buyer: dict | None = None,
    awards: list[dict] | None = None,
) -> dict:
    return {
        "ocid": ocid,
        "date": "2024-01-15T00:00:00+00:00",
        "buyer": buyer if buyer is not None else {"name": "Example Council", "id": "GB-CFS-1"},
        "tender": {"title": "Example services"},
        "awards": awards
        if awards is not None
        else [
            {
                "id": "award-1",
                "date": "2024-02-01T00:00:00+00:00",
                "value": {"amount": 250000, "currency": "GBP"},
                "contractPeriod": {
                    "startDate": "2024-03-01T00:00:00+00:00",
                    "endDate": "2027-02-28T00:00:00+00:00",
                },
                "suppliers": [{"name": "Example Supplier Ltd", "id": "GB-COH-01234567"}],
            }
        ],
    }


def connector_for(body: dict) -> ContractsFinderConnector:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    return ContractsFinderConnector(client=httpx.Client(transport=transport))


def test_award_becomes_a_dated_valued_admitted_relation():
    fragment = connector_for(payload(release())).harvest_awards()
    assert len(fragment.relations) == 1
    relation = fragment.relations[0]
    assert relation.admitted is True
    assert relation.relation_type is RelationType.CONTRACTS_WITH
    assert relation.valid_from == date(2024, 3, 1)
    assert relation.valid_to == date(2027, 2, 28)
    assert relation.amount_gbp == 250000
    assert relation.dependency_family == DEPENDENCY_FAMILY


def test_buyer_and_supplier_get_distinct_roles_and_domains():
    fragment = connector_for(payload(release())).harvest_awards()
    roles = {entity.canonical_name: entity.roles[0] for entity in fragment.entities}
    assert roles["Example Council"] is EntityRole.COMMISSIONER
    assert roles["Example Supplier Ltd"] is EntityRole.PROVIDER


def test_companies_house_number_is_extracted_as_a_strong_identifier():
    fragment = connector_for(payload(release())).harvest_awards()
    supplier = next(e for e in fragment.entities if e.canonical_name == "Example Supplier Ltd")
    assert supplier.identifiers["companies_house"] == "01234567"
    assert supplier.strong_identifiers()

    buyer = next(e for e in fragment.entities if e.canonical_name == "Example Council")
    assert "companies_house" not in buyer.identifiers
    assert not buyer.strong_identifiers()


def test_undated_award_is_skipped_not_admitted_undated():
    body = payload(
        release(
            awards=[
                {
                    "id": "a",
                    "suppliers": [{"name": "Supplier", "id": "GB-CFS-9"}],
                }
            ]
        )
    )
    fragment = connector_for(body).harvest_awards()
    assert fragment.relations == []
    assert fragment.skip_reasons["AWARD_UNDATED"] == 1


def test_missing_names_are_skipped():
    no_buyer = connector_for(payload(release(buyer={"id": "GB-CFS-1"}))).harvest_awards()
    assert no_buyer.skip_reasons["BUYER_NAME_MISSING"] == 1

    body = payload(release(awards=[{
        "id": "a", "date": "2024-02-01T00:00:00+00:00",
        "suppliers": [{"name": "  ", "id": "GB-CFS-9"}],
    }]))
    assert connector_for(body).harvest_awards().skip_reasons["SUPPLIER_NAME_MISSING"] == 1


def test_self_award_does_not_create_a_self_loop():
    body = payload(release(
        buyer={"name": "Same Body", "id": "GB-COH-01234567"},
        awards=[{
            "id": "a", "date": "2024-02-01T00:00:00+00:00",
            "suppliers": [{"name": "Same Body", "id": "GB-COH-01234567"}],
        }],
    ))
    fragment = connector_for(body).harvest_awards()
    assert fragment.relations == []
    assert fragment.skip_reasons["SELF_AWARD"] == 1


def test_non_gbp_value_is_not_recorded_as_pounds():
    body = payload(release(awards=[{
        "id": "a", "date": "2024-02-01T00:00:00+00:00",
        "value": {"amount": 900, "currency": "EUR"},
        "suppliers": [{"name": "Supplier", "id": "GB-CFS-9"}],
    }]))
    assert connector_for(body).harvest_awards().relations[0].amount_gbp is None


def test_inverted_contract_period_drops_the_end_date_rather_than_raising():
    body = payload(release(awards=[{
        "id": "a", "date": "2024-02-01T00:00:00+00:00",
        "contractPeriod": {
            "startDate": "2024-03-01T00:00:00+00:00",
            "endDate": "2023-01-01T00:00:00+00:00",
        },
        "suppliers": [{"name": "Supplier", "id": "GB-CFS-9"}],
    }]))
    relation = connector_for(body).harvest_awards().relations[0]
    assert relation.valid_from == date(2024, 3, 1)
    assert relation.valid_to is None


def test_one_register_is_one_dependency_family():
    """Two awards from the same feed cannot corroborate one another."""

    body = payload(release(ocid="ocds-1"), release(ocid="ocds-2"))
    fragment = connector_for(body).harvest_awards()
    assert len(fragment.relations) == 2
    assert {r.dependency_family for r in fragment.relations} == {DEPENDENCY_FAMILY}


def test_empty_feed_is_safe():
    fragment = connector_for(payload()).harvest_awards()
    assert fragment.relations == [] and fragment.entities == []
    assert fragment.releases_seen == 0


def test_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    connector = ContractsFinderConnector(client=httpx.Client(transport=transport))
    with pytest.raises(httpx.HTTPStatusError):
        connector.harvest_awards()
