from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.charity_commission import CharityCommissionResolver
from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import ProvenanceRecord
from oslt_research.ontology.entities import (
    EntityRole,
    InstitutionalEntity,
    SystemDomain,
)


def entity(
    name: str,
    *,
    domain: SystemDomain = SystemDomain.UNKNOWN,
    identifiers: dict[str, str] | None = None,
) -> InstitutionalEntity:
    return InstitutionalEntity(
        entity_id=f"E-{name[:8]}",
        canonical_name=name,
        roles=[EntityRole.OTHER],
        system_domain=domain,
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


def charity(name: str, number: str = "1160575", status: str = "R") -> dict:
    return {"charity_name": name, "reg_charity_number": number, "reg_status": status}


def resolver_for(*items: dict, status_code: int = 200) -> CharityCommissionResolver:
    def handler(request: httpx.Request) -> httpx.Response:
        if status_code != 200:
            return httpx.Response(status_code)
        return httpx.Response(200, json=list(items))

    return CharityCommissionResolver(
        client=httpx.Client(transport=httpx.MockTransport(handler)), min_interval_seconds=0.0
    )


def test_exact_unique_registered_match_resolves():
    report = resolver_for(charity("EXAMPLE TRUST")).resolve([entity("Example Trust")])
    [attempt] = report.attempts
    assert attempt.resolved
    assert attempt.company_number == "1160575"
    assert report.entities[0].identifiers["charity_number"] == "1160575"


def test_registration_types_an_unknown_domain_as_advocacy():
    """An UNKNOWN domain can never contribute to a coupling verdict, so this is the point."""

    report = resolver_for(charity("EXAMPLE TRUST")).resolve([entity("Example Trust")])
    resolved = report.entities[0]
    assert resolved.system_domain is SystemDomain.ADVOCACY
    assert resolved.roles == [EntityRole.ADVOCACY_ORGANISATION]
    assert resolved.metadata["domain_undetermined"] is False
    assert resolved.metadata["domain_source"] == "charity_commission_register"


def test_an_already_typed_domain_is_not_overwritten():
    report = resolver_for(charity("EXAMPLE TRUST")).resolve(
        [entity("Example Trust", domain=SystemDomain.CLINICAL)]
    )
    assert report.entities[0].system_domain is SystemDomain.CLINICAL


def test_removed_charity_is_refused():
    """Searching a real name returns both registered and removed bodies."""

    report = resolver_for(charity("EXAMPLE TRUST", status="RM")).resolve([entity("Example Trust")])
    [attempt] = report.attempts
    assert not attempt.resolved
    assert attempt.reason == "ONLY_REMOVED_NAME_MATCH"
    assert report.entities[0].system_domain is SystemDomain.UNKNOWN


def test_registered_wins_over_a_removed_namesake():
    report = resolver_for(
        charity("EXAMPLE TRUST", "1073991", "RM"), charity("EXAMPLE TRUST", "1160575", "R")
    ).resolve([entity("Example Trust")])
    assert report.attempts[0].company_number == "1160575"


def test_two_registered_charities_of_the_same_name_are_refused():
    report = resolver_for(
        charity("EXAMPLE TRUST", "1000001"), charity("Example Trust", "1000002")
    ).resolve([entity("Example Trust")])
    assert not report.attempts[0].resolved
    assert report.attempts[0].reason.startswith("AMBIGUOUS_")


def test_group_entries_sharing_one_number_are_not_ambiguous():
    """Group and subsidiary rows share a charity number under different suffixes."""

    report = resolver_for(
        charity("EXAMPLE TRUST", "1160575"), charity("EXAMPLE TRUST", "1160575")
    ).resolve([entity("Example Trust")])
    assert report.attempts[0].resolved


def test_near_miss_name_is_not_accepted():
    report = resolver_for(charity("EXAMPLE TRUSTEES")).resolve([entity("Example Trust")])
    assert report.attempts[0].reason == "NO_EXACT_NAME_MATCH"


def test_entity_with_an_identifier_is_skipped():
    report = resolver_for(charity("EXAMPLE TRUST")).resolve(
        [entity("Example Trust", identifiers={"companies_house": "01234567"})]
    )
    assert report.attempts[0].reason == "ALREADY_HAS_STRONG_IDENTIFIER"


def test_no_results_is_handled_as_no_match():
    assert resolver_for().resolve([entity("Nothing")]).attempts[0].reason == "NO_EXACT_NAME_MATCH"


def test_search_failure_leaves_the_entity_untouched():
    original = entity("Example Trust")
    report = resolver_for(status_code=500).resolve([original])
    assert report.attempts[0].reason.startswith("SEARCH_FAILED_")
    assert report.entities[0] == original


def test_missing_api_key_raises():
    with pytest.raises(ValueError, match="API key required"):
        CharityCommissionResolver(api_key="")
