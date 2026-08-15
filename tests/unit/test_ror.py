from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.ror import RorResolver
from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import ProvenanceRecord
from oslt_research.ontology.entities import EntityRole, InstitutionalEntity, SystemDomain


def entity(name: str, *, identifiers: dict | None = None) -> InstitutionalEntity:
    return InstitutionalEntity(
        entity_id=f"E-{name[:8]}", canonical_name=name, roles=[EntityRole.OTHER],
        system_domain=SystemDomain.UNKNOWN, jurisdiction="UK",
        identifiers=identifiers or {},
        provenance=ProvenanceRecord(source_id="S", source_uri="https://x", 
                                    checksum_sha256="a"*64, access_class=AccessClass.OPEN),
        source_status=SourceStatus.VERIFIED, dependency_family="f",
    )


def org(name="Newcastle University", ror="01kj2bm70", *, types=("education",),
        status="active", country="GB") -> dict:
    return {
        "id": f"https://ror.org/{ror}",
        "names": [{"value": name, "types": ["ror_display", "label"]}],
        "types": list(types), "status": status,
        "locations": [{"geonames_details": {"country_code": country}}],
    }


def resolver_for(*items: dict, status: int = 200, country_code: str | None = "GB") -> RorResolver:
    def handler(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(200, json={"items": list(items)})

    return RorResolver(client=httpx.Client(transport=httpx.MockTransport(handler)),
                       min_interval_seconds=0.0, country_code=country_code)


def test_exact_active_match_attaches_a_ror_id():
    report = resolver_for(org()).resolve([entity("Newcastle University")])
    assert report.attempts[0].resolved
    assert report.entities[0].identifiers["ror"] == "01kj2bm70"
    assert report.entities[0].strong_identifiers()


def test_display_name_is_read_from_the_names_array():
    """ROR v2 has no top-level name field; it is a list tagged ror_display."""

    assert RorResolver.display_name(org(name="A University")) == "A University"


def test_inactive_record_is_refused():
    report = resolver_for(org(status="inactive")).resolve([entity("Newcastle University")])
    assert not report.attempts[0].resolved
    assert report.attempts[0].reason == "NO_EXACT_ACTIVE_MATCH"


def test_wrong_country_is_refused():
    report = resolver_for(org(country="US")).resolve([entity("Newcastle University")])
    assert not report.attempts[0].resolved


def test_country_filter_can_be_disabled():
    report = resolver_for(org(country="US"), country_code=None).resolve(
        [entity("Newcastle University")]
    )
    assert report.attempts[0].resolved


def test_near_miss_name_is_refused():
    report = resolver_for(org(name="Newcastle College")).resolve([entity("Newcastle University")])
    assert report.attempts[0].reason == "NO_EXACT_ACTIVE_MATCH"


def test_two_distinct_active_ids_are_ambiguous():
    report = resolver_for(
        org(ror="aaa"), org(ror="bbb")
    ).resolve([entity("Newcastle University")])
    assert report.attempts[0].reason.startswith("AMBIGUOUS_")


@pytest.mark.parametrize(
    "types,expected",
    [
        (("education", "funder"), SystemDomain.ACADEMIC),
        (("healthcare",), SystemDomain.CLINICAL),
        (("government",), SystemDomain.POLICY),
        (("nonprofit",), SystemDomain.ADVOCACY),
        (("funder",), SystemDomain.PHILANTHROPIC),
    ],
)
def test_type_precedence_maps_to_a_domain(types, expected):
    """A university that also funds is academic, not philanthropic."""

    mapped = RorResolver._domain_for(list(types))
    assert mapped is not None and mapped[0] is expected


def test_unmappable_type_yields_no_domain():
    assert RorResolver._domain_for(["archive"]) is None


def test_entity_with_an_identifier_is_skipped():
    report = resolver_for(org()).resolve(
        [entity("Newcastle University", identifiers={"companies_house": "01234567"})]
    )
    assert report.attempts[0].reason == "ALREADY_HAS_STRONG_IDENTIFIER"


def test_search_failure_leaves_the_entity_untouched():
    original = entity("Newcastle University")
    report = resolver_for(status=500).resolve([original])
    assert report.attempts[0].reason.startswith("SEARCH_FAILED_")
    assert report.entities[0] == original
