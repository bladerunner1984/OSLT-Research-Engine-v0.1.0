from __future__ import annotations

from datetime import date

import httpx
import pytest

from oslt_research.connectors.govuk_guidance import (
    DEPENDENCY_FAMILY,
    GovUkGuidanceConnector,
)
from oslt_research.ontology.entities import EntityRole, RelationType, SystemDomain


def document(
    *,
    doc_type: str = "guidance",
    timestamp: str | None = "2024-03-01T00:00:00+00:00",
    organisations: list | None = None,
    title: str = "Example guidance",
    link: str = "/example-guidance",
) -> dict:
    return {
        "title": title,
        "link": link,
        "public_timestamp": timestamp,
        "content_store_document_type": doc_type,
        "organisations": organisations
        if organisations is not None
        else [{"title": "Department of Health and Social Care", "slug": "dhsc"}],
    }


def connector_for(*docs: dict) -> GovUkGuidanceConnector:
    body = {"results": list(docs), "total": len(docs)}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    return GovUkGuidanceConnector(client=httpx.Client(transport=transport))


def test_guidance_becomes_a_dated_issues_guidance_relation():
    fragment = connector_for(document()).harvest_guidance()
    assert len(fragment.relations) == 1
    relation = fragment.relations[0]
    assert relation.admitted
    assert relation.relation_type is RelationType.ISSUES_GUIDANCE_TO
    assert relation.valid_from == date(2024, 3, 1)
    assert relation.dependency_family == DEPENDENCY_FAMILY


def test_issuer_is_typed_as_a_guideline_body_in_policy():
    fragment = connector_for(document()).harvest_guidance()
    issuer = next(e for e in fragment.entities if "Department" in e.canonical_name)
    assert issuer.roles == [EntityRole.GUIDELINE_BODY]
    assert issuer.system_domain is SystemDomain.POLICY
    assert issuer.identifiers["govuk_organisation_slug"] == "dhsc"


def test_the_document_is_not_treated_as_an_institution():
    """A guidance document is the target of a tie, not a body that can span a domain."""

    fragment = connector_for(document()).harvest_guidance()
    target = next(e for e in fragment.entities if e.canonical_name == "Example guidance")
    assert target.system_domain is SystemDomain.UNKNOWN
    assert target.metadata["is_document_not_institution"] is True


@pytest.mark.parametrize("doc_type", ["news_story", "press_release", "transaction", "answer"])
def test_non_guidance_document_types_are_skipped(doc_type):
    """A press release is not a body issuing guidance."""

    fragment = connector_for(document(doc_type=doc_type)).harvest_guidance()
    assert fragment.relations == []
    assert fragment.skip_reasons[f"NOT_GUIDANCE_{doc_type}"] == 1


def test_statutory_guidance_is_accepted():
    assert connector_for(document(doc_type="statutory_guidance")).harvest_guidance().relations


def test_undated_document_is_skipped():
    fragment = connector_for(document(timestamp=None)).harvest_guidance()
    assert fragment.skip_reasons["DOCUMENT_UNDATED"] == 1


def test_document_without_an_issuer_is_skipped():
    fragment = connector_for(document(organisations=[])).harvest_guidance()
    assert fragment.relations == []
    assert fragment.skip_reasons["NO_ISSUING_ORGANISATION"] == 1


def test_two_issuers_create_two_relations():
    fragment = connector_for(document(organisations=[
        {"title": "DHSC", "slug": "dhsc"}, {"title": "DfE", "slug": "dfe"},
    ])).harvest_guidance()
    assert len(fragment.relations) == 2


def test_guidance_is_a_third_tie_type_and_family():
    from oslt_research.connectors.contracts_finder import DEPENDENCY_FAMILY as CF
    from oslt_research.connectors.parliament_evidence import DEPENDENCY_FAMILY as PWE

    assert DEPENDENCY_FAMILY not in {CF, PWE}


def test_empty_feed_is_safe():
    fragment = connector_for().harvest_guidance()
    assert fragment.relations == [] and fragment.documents_seen == 0


def test_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(502))
    with pytest.raises(httpx.HTTPStatusError):
        GovUkGuidanceConnector(client=httpx.Client(transport=transport)).harvest_guidance()
