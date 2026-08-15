from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.companies_house import CompaniesHouseResolver
from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import ProvenanceRecord
from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    SystemDomain,
)


def entity(name: str, *, identifiers: dict[str, str] | None = None) -> InstitutionalEntity:
    return InstitutionalEntity(
        entity_id=f"E-{name[:8]}",
        canonical_name=name,
        roles=[EntityRole.PROVIDER],
        system_domain=SystemDomain.COMMERCIAL,
        jurisdiction="UK",
        identifiers=identifiers or {},
        provenance=ProvenanceRecord(
            source_id="SRC",
            source_uri="https://example.org/x",
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        source_status=SourceStatus.VERIFIED,
        dependency_family="register:test",
    )


def resolver_for(*items: dict) -> CompaniesHouseResolver:
    body = {"items": list(items)}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    return CompaniesHouseResolver(
        client=httpx.Client(transport=transport), min_interval_seconds=0.0
    )


def company(title: str, number: str = "01234567", status: str = "active") -> dict:
    return {"title": title, "company_number": number, "company_status": status}


def test_exact_unique_active_match_resolves():
    report = resolver_for(company("EXAMPLE SUPPLIER LTD")).resolve([entity("Example Supplier Ltd")])
    [attempt] = report.attempts
    assert attempt.resolved
    assert attempt.company_number == "01234567"
    assert report.entities[0].identifiers["companies_house"] == "01234567"
    assert report.entities[0].strong_identifiers()


def test_two_active_companies_with_the_same_name_are_refused():
    """Picking one would be a guess dressed as an identifier."""

    report = resolver_for(
        company("EXAMPLE LTD", "00000001"), company("Example Limited", "00000002")
    ).resolve([entity("Example Ltd")])
    [attempt] = report.attempts
    assert not attempt.resolved
    assert attempt.reason.startswith("AMBIGUOUS_")
    assert "companies_house" not in report.entities[0].identifiers


def test_dissolved_only_match_is_refused_with_its_own_reason():
    report = resolver_for(company("EXAMPLE LTD", status="dissolved")).resolve(
        [entity("Example Ltd")]
    )
    [attempt] = report.attempts
    assert not attempt.resolved
    assert attempt.reason == "ONLY_DISSOLVED_NAME_MATCH"


def test_near_miss_name_is_not_accepted():
    """Fuzzy matching would recreate the name-only problem with an identifier on top."""

    report = resolver_for(company("EXAMPLE SUPPLIES LIMITED")).resolve(
        [entity("Example Supplier Ltd")]
    )
    [attempt] = report.attempts
    assert not attempt.resolved
    assert attempt.reason == "NO_EXACT_NAME_MATCH"


def test_legal_suffix_differences_still_match():
    """'Ltd' versus 'Limited' is not a different organisation."""

    report = resolver_for(company("EXAMPLE SUPPLIER LIMITED")).resolve(
        [entity("Example Supplier Ltd")]
    )
    assert report.attempts[0].resolved


def test_entity_that_already_has_an_identifier_is_skipped():
    report = resolver_for(company("EXAMPLE LTD")).resolve(
        [entity("Example Ltd", identifiers={"companies_house": "09999999"})]
    )
    [attempt] = report.attempts
    assert not attempt.resolved
    assert attempt.reason == "ALREADY_HAS_STRONG_IDENTIFIER"
    assert report.entities[0].identifiers["companies_house"] == "09999999"


def test_empty_name_is_skipped():
    assert resolver_for().resolve([entity("   ")]).attempts[0].reason == "EMPTY_NAME"


def test_search_failure_leaves_the_entity_untouched():
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    resolver = CompaniesHouseResolver(
        client=httpx.Client(transport=transport), min_interval_seconds=0.0
    )
    original = entity("Example Ltd")
    report = resolver.resolve([original])
    assert not report.attempts[0].resolved
    assert report.attempts[0].reason.startswith("SEARCH_FAILED_")
    assert report.entities[0] == original


def test_summary_counts_and_reasons():
    report = resolver_for(company("EXAMPLE LTD", status="dissolved")).resolve(
        [entity("Example Ltd"), entity("Example Ltd")]
    )
    summary = report.summary()
    assert summary["attempted"] == 2
    assert summary["resolved"] == 0
    assert summary["unresolved_reasons"]["ONLY_DISSOLVED_NAME_MATCH"] == 2


def test_missing_api_key_raises_rather_than_failing_silently():
    with pytest.raises(ValueError, match="API key required"):
        CompaniesHouseResolver(api_key="")


def test_match_basis_is_recorded_on_the_entity():
    report = resolver_for(company("EXAMPLE LTD")).resolve([entity("Example Ltd")])
    assert report.entities[0].metadata["companies_house_match_basis"] == "EXACT_UNIQUE_ACTIVE_MATCH"
    assert report.entities[0].metadata["companies_house_matched_title"] == "EXAMPLE LTD"
