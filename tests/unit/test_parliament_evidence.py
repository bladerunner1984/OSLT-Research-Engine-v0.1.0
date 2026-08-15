from __future__ import annotations

from datetime import date

import httpx
import pytest

from oslt_research.connectors.parliament_evidence import (
    DEPENDENCY_FAMILY,
    ParliamentWrittenEvidenceConnector,
)
from oslt_research.ontology.entities import EntityRole, RelationType, SystemDomain


def submission(
    *,
    witnesses=None,
    committees=None,
    publication_date: str | None = "2024-03-01T00:00:00",
    anonymous: bool = False,
) -> dict:
    return {
        "submissionId": "sub-1",
        "internalReference": "REF0001",
        "publicationDate": publication_date,
        "anonymous": anonymous,
        "committeeBusiness": {"title": "An inquiry"},
        "committees": committees
        if committees is not None
        else [{"id": 42, "name": "Health and Social Care Committee", "house": "Commons"}],
        "witnesses": witnesses
        if witnesses is not None
        else [{"submitterType": "Organisation", "organisations": [{"name": "Example Trust"}]}],
    }


def connector_for(*items) -> ParliamentWrittenEvidenceConnector:
    body = {"items": list(items), "totalResults": len(items)}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    return ParliamentWrittenEvidenceConnector(client=httpx.Client(transport=transport))


def test_organisation_submission_becomes_a_dated_advises_relation():
    fragment = connector_for(submission()).harvest_submissions()
    assert len(fragment.relations) == 1
    relation = fragment.relations[0]
    assert relation.admitted is True
    assert relation.relation_type is RelationType.ADVISES
    assert relation.valid_from == date(2024, 3, 1)
    assert relation.dependency_family == DEPENDENCY_FAMILY


def test_witness_organisation_domain_is_unknown_not_guessed():
    """Guessing a domain would fabricate the cross-system spread MD15 tests for."""

    fragment = connector_for(submission()).harvest_submissions()
    org = next(e for e in fragment.entities if e.canonical_name == "Example Trust")
    assert org.system_domain is SystemDomain.UNKNOWN
    assert org.roles == [EntityRole.OTHER]
    assert org.metadata["domain_undetermined"] is True


def test_committee_is_typed_policy():
    fragment = connector_for(submission()).harvest_submissions()
    committee = next(e for e in fragment.entities if "Committee" in e.canonical_name)
    assert committee.system_domain is SystemDomain.POLICY
    assert committee.identifiers["parliament_committee_id"] == "42"


def test_individual_submitters_are_skipped_by_design():
    body = submission(
        witnesses=[{"submitterType": "Individual", "organisations": [], "name": "A Person"}]
    )
    fragment = connector_for(body).harvest_submissions()
    assert fragment.relations == []
    assert fragment.skip_reasons["INDIVIDUAL_OR_UNNAMED_SUBMITTER"] == 1
    assert not any("Person" in e.canonical_name for e in fragment.entities)


def test_anonymous_submission_is_skipped():
    fragment = connector_for(submission(anonymous=True)).harvest_submissions()
    assert fragment.relations == []
    assert fragment.skip_reasons["ANONYMOUS_SUBMISSION"] == 1


def test_undated_submission_is_skipped_not_admitted_undated():
    fragment = connector_for(submission(publication_date=None)).harvest_submissions()
    assert fragment.relations == []
    assert fragment.skip_reasons["SUBMISSION_UNDATED"] == 1


def test_submission_without_a_committee_is_skipped():
    fragment = connector_for(submission(committees=[])).harvest_submissions()
    assert fragment.relations == []
    assert fragment.skip_reasons["NO_COMMITTEE_ON_SUBMISSION"] == 1


def test_one_submission_to_two_committees_creates_two_relations():
    body = submission(committees=[
        {"id": 1, "name": "First Committee", "house": "Commons"},
        {"id": 2, "name": "Second Committee", "house": "Lords"},
    ])
    assert len(connector_for(body).harvest_submissions().relations) == 2


def test_same_organisation_across_submissions_resolves_to_one_entity():
    first = submission()
    second = dict(submission(), submissionId="sub-2")
    fragment = connector_for(first, second).harvest_submissions()
    orgs = [e for e in fragment.entities if e.canonical_name == "Example Trust"]
    assert len(orgs) == 1
    assert len(fragment.relations) == 2


def test_organisation_name_is_case_folded_for_identity():
    a = submission()
    b = dict(
        submission(witnesses=[{"submitterType": "Organisation",
                               "organisations": [{"name": "EXAMPLE TRUST"}]}]),
        submissionId="sub-2",
    )
    fragment = connector_for(a, b).harvest_submissions()
    assert len({e.entity_id for e in fragment.entities if "xample" in e.canonical_name.lower()
                or "XAMPLE" in e.canonical_name}) == 1


def test_advises_is_a_distinct_tie_type_from_the_money_registers():
    from oslt_research.connectors.contracts_finder import (
        DEPENDENCY_FAMILY as CONTRACTS_FAMILY,
    )

    assert DEPENDENCY_FAMILY != CONTRACTS_FAMILY


def test_empty_feed_is_safe():
    fragment = connector_for().harvest_submissions()
    assert fragment.relations == [] and fragment.submissions_seen == 0


def test_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(502))
    connector = ParliamentWrittenEvidenceConnector(client=httpx.Client(transport=transport))
    with pytest.raises(httpx.HTTPStatusError):
        connector.harvest_submissions()
