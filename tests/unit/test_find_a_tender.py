from __future__ import annotations

from datetime import date

import httpx
import pytest

from oslt_research.connectors.find_a_tender import DEPENDENCY_FAMILY, FindATenderConnector
from oslt_research.connectors.ocds import identifiers_from_party, parse_ocds_date
from oslt_research.ontology.entities import EntityRole


def release(*, awards=None, contracts=None, parties=None, buyer=None) -> dict:
    return {
        "ocid": "ocds-h6vhtk-1",
        "date": "2026-07-01T00:00:00+01:00",
        "buyer": buyer if buyer is not None else {"name": "Example Authority", "id": "GB-FTS-1"},
        "tender": {"title": "Example"},
        "parties": parties
        if parties is not None
        else [
            {"id": "GB-FTS-1", "name": "Example Authority", "roles": ["buyer"],
             "identifier": {"legalName": "Example Authority"}},
            {"id": "GB-FTS-2", "name": "Example Supplier Ltd", "roles": ["supplier"],
             "identifier": {"legalName": "Example Supplier Ltd", "id": "08664789",
                            "scheme": "GB-COH"}},
        ],
        "awards": awards
        if awards is not None
        else [{"id": "A-1", "status": "active",
               "suppliers": [{"name": "Example Supplier Ltd", "id": "GB-FTS-2"}]}],
        "contracts": contracts
        if contracts is not None
        else [{"id": "A-1", "awardID": "A-1", "dateSigned": "2026-07-09T00:00:00+01:00",
               "value": {"amount": 50943.59, "currency": "GBP"}}],
    }


def connector_for(*releases) -> FindATenderConnector:
    body = {"version": "1.1", "releases": list(releases)}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    return FindATenderConnector(client=httpx.Client(transport=transport))


# ---------------------------------------------------------------- shared helpers


@pytest.mark.parametrize(
    "value,expected",
    [("2026-07-09T00:00:00+01:00", date(2026, 7, 9)), ("nonsense", None), (None, None)],
)
def test_parse_ocds_date(value, expected):
    assert parse_ocds_date(value) == expected


def test_identifiers_from_structured_scheme_and_embedded_id():
    structured = identifiers_from_party(
        {"identifier": {"scheme": "GB-COH", "id": "08664789"}}, "GB-FTS-2"
    )
    assert structured["companies_house"] == "08664789"

    embedded = identifiers_from_party(None, "GB-COH-01234567")
    assert embedded["companies_house"] == "01234567"

    weak = identifiers_from_party({"identifier": {"legalName": "X"}}, "GB-FTS-9")
    assert "companies_house" not in weak
    assert weak["ocds_party_id"] == "GB-FTS-9"


# -------------------------------------------------------------------- connector


def test_award_joins_contract_for_date_and_value():
    fragment = connector_for(release()).harvest_awards()
    assert len(fragment.relations) == 1
    relation = fragment.relations[0]
    assert relation.admitted is True
    assert relation.valid_from == date(2026, 7, 9)
    assert relation.amount_gbp == pytest.approx(50943.59)
    assert relation.dependency_family == DEPENDENCY_FAMILY


def test_award_without_matching_contract_is_skipped():
    fragment = connector_for(release(contracts=[])).harvest_awards()
    assert fragment.relations == []
    assert fragment.skip_reasons["AWARD_UNDATED_NO_MATCHING_CONTRACT"] == 1


def test_supplier_companies_house_number_becomes_a_strong_identifier():
    fragment = connector_for(release()).harvest_awards()
    supplier = next(e for e in fragment.entities if "Supplier" in e.canonical_name)
    assert supplier.identifiers["companies_house"] == "08664789"
    assert supplier.strong_identifiers()
    assert supplier.roles[0] is EntityRole.PROVIDER


def test_buyer_without_a_register_identifier_stays_weak():
    fragment = connector_for(release()).harvest_awards()
    buyer = next(e for e in fragment.entities if e.canonical_name == "Example Authority")
    assert not buyer.strong_identifiers()
    assert buyer.roles[0] is EntityRole.COMMISSIONER


def test_find_a_tender_is_a_separate_dependency_family_from_contracts_finder():
    from oslt_research.connectors.contracts_finder import (
        DEPENDENCY_FAMILY as CONTRACTS_FINDER_FAMILY,
    )

    assert DEPENDENCY_FAMILY != CONTRACTS_FINDER_FAMILY


def test_non_gbp_contract_value_is_not_recorded_as_pounds():
    body = release(contracts=[{"id": "A-1", "awardID": "A-1",
                               "dateSigned": "2026-07-09T00:00:00+01:00",
                               "value": {"amount": 100, "currency": "EUR"}}])
    assert connector_for(body).harvest_awards().relations[0].amount_gbp is None


def test_missing_buyer_name_is_skipped():
    fragment = connector_for(release(buyer={"id": "GB-FTS-1"})).harvest_awards()
    assert fragment.skip_reasons["BUYER_NAME_MISSING"] == 1


def test_empty_feed_is_safe():
    fragment = connector_for().harvest_awards()
    assert fragment.relations == [] and fragment.releases_seen == 0


def test_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        FindATenderConnector(client=httpx.Client(transport=transport)).harvest_awards()
