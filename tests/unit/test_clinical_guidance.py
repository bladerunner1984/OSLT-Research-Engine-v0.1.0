"""Unit tests for the W09 clinical-guidance connectors.

Every test uses ``httpx.MockTransport``; nothing here touches the network. The bulk of
the assertions are about one thing: that a revision timestamp never becomes a policy date.
"""

from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from oslt_research.connectors.clinical_guidance import (
    DECLINED_SOURCES,
    PROFESSIONAL_BODIES,
    GovUkPolicyDocumentConnector,
    GuidanceHarvest,
    NhsEnglandPolicyConnector,
    NiceGuidanceConnector,
    PolicyDocument,
    ProfessionalBody,
    ProfessionalBodyConnector,
    ThrottledClient,
    _year_conflict,
    parse_iso_date,
    strip_markup,
)


def client_returning(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def json_client(payload, *, status: int = 200) -> httpx.Client:
    return client_returning(lambda request: httpx.Response(status, json=payload))


# --------------------------------------------------------------------------------------
# core semantics
# --------------------------------------------------------------------------------------


def test_anchor_date_ignores_the_revision_timestamp_entirely():
    """The whole point of W09: last_updated is visible and unusable."""

    doc = PolicyDocument(
        source="s", publisher="p", title="t", url="u",
        published_on=date(2016, 1, 1), published_on_field="publicationDate",
        last_updated=date(2026, 8, 1), last_updated_field="lastUpdated",
    )
    assert doc.anchor_date() == date(2016, 1, 1)


def test_a_document_with_only_a_revision_timestamp_is_undated():
    doc = PolicyDocument(
        source="s", publisher="p", title="t", url="u", last_updated=date(2026, 8, 1)
    )
    assert doc.is_dated is False
    assert doc.anchor_date() is None


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2019-06-25T12:00:00", date(2019, 6, 25)),
        ("2024-04-10T00:01:00+0100"[:10], date(2024, 4, 10)),
        ("2022-07-28T00:00:00+00:00", date(2022, 7, 28)),
        ("2024-10-24T00:05:00+01:00", date(2024, 10, 24)),
        ("", None),
        (None, None),
        ("not a date", None),
        (20240410, None),
    ],
)
def test_parse_iso_date_returns_none_rather_than_guessing(value, expected):
    assert parse_iso_date(value) == expected


def test_strip_markup_removes_search_api_highlighting():
    assert strip_markup("<b>Gender</b> incongruence &amp; care") == "Gender incongruence & care"


def test_year_conflict_flags_a_migrated_page_but_tolerates_a_year_boundary():
    assert _year_conflict("Interim specification 2022", date(2026, 3, 1)) == 2022
    assert _year_conflict("Specification 2022", date(2023, 1, 5)) is None
    assert _year_conflict("No year here", date(2023, 1, 5)) is None
    assert _year_conflict("Specification 2022", None) is None


def test_harvest_anchor_dates_are_unique_and_sorted_and_exclude_undated():
    harvest = GuidanceHarvest(
        documents=[
            PolicyDocument("a", "a", "a", "1", published_on=date(2024, 4, 10)),
            PolicyDocument("a", "a", "a", "2", published_on=date(2024, 4, 10)),
            PolicyDocument("a", "a", "a", "3", published_on=date(2016, 1, 1)),
            PolicyDocument("a", "a", "a", "4", last_updated=date(2026, 1, 1)),
        ]
    )
    assert harvest.anchor_dates() == [date(2016, 1, 1), date(2024, 4, 10)]
    assert len(harvest.dated()) == 3 and len(harvest.undated()) == 1


def test_merged_harvest_deduplicates_on_url_and_sums_skips():
    left = GuidanceHarvest(
        documents=[PolicyDocument("a", "a", "a", "u1")], records_seen=1,
        skip_reasons={"X": 1},
    )
    right = GuidanceHarvest(
        documents=[PolicyDocument("b", "b", "b", "u1"), PolicyDocument("b", "b", "b", "u2")],
        records_seen=2, skip_reasons={"X": 2, "Y": 1},
    )
    merged = left.merged_with(right)
    assert {doc.url for doc in merged.documents} == {"u1", "u2"}
    assert merged.skip_reasons == {"X": 3, "Y": 1}
    assert merged.records_seen == 3


def test_declined_sources_record_the_reason_not_just_the_host():
    assert "cass.independent-review.uk" in DECLINED_SOURCES
    assert "webarchive.nationalarchives.gov.uk" in DECLINED_SOURCES
    assert "www.gmc-uk.org" in DECLINED_SOURCES
    assert all(len(reason) > 60 for reason in DECLINED_SOURCES.values())


def test_throttled_client_does_not_sleep_when_disabled():
    wrapped = ThrottledClient(json_client({"ok": True}), enabled=False)
    assert wrapped.get("https://www.nice.org.uk/x").json() == {"ok": True}


def test_throttled_client_sends_the_project_user_agent():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, json={})

    ThrottledClient(client_returning(handler), enabled=False).get("https://x.test/")
    assert seen["ua"].startswith("oslt-research-engine/")


# --------------------------------------------------------------------------------------
# NICE
# --------------------------------------------------------------------------------------


def nice_payload(*documents) -> dict:
    return {"resultCount": len(documents), "documents": list(documents)}


NICE_PUBLISHED = {
    "guidanceRef": "NG134",
    "title": "<b>Depression</b> in children and young people",
    "url": "https://www.nice.org.uk/guidance/ng134",
    "publicationDate": "2019-06-25T12:00:00",
    "lastUpdated": "2025-01-04T12:00:00",
    "guidanceStatus": ["Published"],
    "niceDocType": ["Guidance"],
}

NICE_IN_DEVELOPMENT = {
    "guidanceRef": None,
    "title": "<b>Gender</b> incongruence in children and young people",
    "url": "https://www.nice.org.uk/guidance/prioritisation/gid-ng10492",
    "publicationDate": None,
    "lastUpdated": "2024-07-11T12:00:00",
    "topicSelectionDecisionDate": "2024-07-11T12:00:00",
    "guidanceStatus": ["Topic prioritisation"],
    "niceDocType": ["Guidance"],
}


def test_nice_uses_publication_date_and_keeps_last_updated_separate():
    result = NiceGuidanceConnector(client=json_client(nice_payload(NICE_PUBLISHED))).search("x")
    [doc] = result.documents
    assert doc.published_on == date(2019, 6, 25)
    assert doc.published_on_field == "publicationDate"
    assert doc.last_updated == date(2025, 1, 4)
    assert doc.anchor_date() == date(2019, 6, 25)
    assert doc.identifiers["nice_reference"] == "NG134"
    assert doc.title == "Depression in children and young people"


def test_nice_in_development_record_is_kept_but_undated_with_a_named_reason():
    """A topic-selection decision date is not a publication date."""

    result = NiceGuidanceConnector(
        client=json_client(nice_payload(NICE_IN_DEVELOPMENT))
    ).search("gender")
    [doc] = result.documents
    assert doc.is_dated is False
    assert doc.anchor_date() is None
    assert "topicSelectionDecisionDate" in doc.undated_reason
    assert result.skip_reasons["NICE_NO_PUBLICATION_DATE"] == 1


def test_nice_withdrawn_guidance_is_flagged_but_kept():
    """A withdrawn guideline was in force for a period; that period is the subject."""

    withdrawn = {**NICE_PUBLISHED, "guidanceStatus": ["Withdrawn"]}
    [doc] = NiceGuidanceConnector(client=json_client(nice_payload(withdrawn))).search("x").documents
    assert doc.withdrawn is True
    assert doc.published_on == date(2019, 6, 25)


def test_nice_record_without_a_url_is_skipped():
    result = NiceGuidanceConnector(
        client=json_client(nice_payload({**NICE_PUBLISHED, "url": "", "sourceUrl": ""}))
    ).search("x")
    assert result.documents == []
    assert result.skip_reasons["NICE_TITLE_OR_URL_MISSING"] == 1


def test_nice_non_json_response_does_not_raise():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text="<html>"))
    result = NiceGuidanceConnector(client=httpx.Client(transport=transport)).search("x")
    assert result.skip_reasons["NICE_RESPONSE_NOT_JSON"] == 1


def test_nice_http_error_propagates_and_is_not_an_absence():
    with pytest.raises(httpx.HTTPStatusError):
        NiceGuidanceConnector(client=json_client({}, status=500)).search("x")


# --------------------------------------------------------------------------------------
# NHS England
# --------------------------------------------------------------------------------------


def wp_record(**overrides) -> dict:
    record = {
        "id": 250580,
        "date": "2024-08-07T11:57:24",
        "date_gmt": "2024-08-07T10:57:24",
        "modified_gmt": "2024-08-29T11:32:16",
        "status": "publish",
        "type": "long-read",
        "link": "https://www.england.nhs.uk/long-read/implementing-the-cass-review/",
        "title": {"rendered": "Children and young people&#8217;s gender services"},
    }
    record.update(overrides)
    return record


def test_nhs_england_publication_timestamp_anchors_and_modified_does_not():
    result = NhsEnglandPolicyConnector(client=json_client([wp_record()])).collection("long-read")
    [doc] = result.documents
    assert doc.published_on == date(2024, 8, 7)
    assert doc.published_on_field == "wp:date_gmt"
    assert doc.last_updated == date(2024, 8, 29)
    assert doc.anchor_date() == date(2024, 8, 7)


def test_nhs_england_refuses_to_anchor_a_page_whose_title_contradicts_the_site_date():
    """A 2022 interim specification with a 2026 site timestamp is a migration."""

    record = wp_record(
        date_gmt="2026-02-01T00:00:00",
        title={"rendered": "Interim service specification 2022"},
    )
    result = NhsEnglandPolicyConnector(client=json_client([record])).collection("long-read")
    [doc] = result.documents
    assert doc.is_dated is False
    assert "2022" in doc.undated_reason
    assert result.skip_reasons["NHSE_TITLE_YEAR_CONFLICT"] == 1


def test_nhs_england_page_beyond_the_end_is_exhaustion_not_absence():
    result = NhsEnglandPolicyConnector(
        client=json_client({"code": "rest_post_invalid_page_number"}, status=400)
    ).collection("long-read", page=99)
    assert result.documents == []
    assert result.skip_reasons["NHSE_PAGE_BEYOND_END"] == 1


def test_nhs_england_record_without_a_link_is_skipped():
    result = NhsEnglandPolicyConnector(
        client=json_client([wp_record(link="")])
    ).collection("long-read")
    assert result.skip_reasons["NHSE_TITLE_OR_LINK_MISSING"] == 1


def test_nhs_england_category_lookup_returns_none_for_an_unknown_slug():
    connector = NhsEnglandPolicyConnector(client=json_client([]))
    assert connector.category_id("no-such-category") is None


def test_nhs_england_category_lookup_resolves_a_known_slug():
    connector = NhsEnglandPolicyConnector(client=json_client([{"id": 2875}]))
    assert connector.category_id("gender-identity") == 2875


# --------------------------------------------------------------------------------------
# GOV.UK
# --------------------------------------------------------------------------------------


def govuk_client(search_results, content_by_path, *, content_status=200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/search.json":
            return httpx.Response(200, json={"results": search_results})
        path = request.url.path[len("/api/content"):]
        if path not in content_by_path:
            return httpx.Response(404, json={})
        return httpx.Response(content_status, json=content_by_path[path])

    return client_returning(handler)


SEARCH_HIT = {
    "title": "Poor governance at Mermaids",
    "link": "/government/news/poor-governance-at-mermaids",
    "public_timestamp": "2024-10-23T23:05:00Z",
    "organisations": [{"title": "Charity Commission"}],
}


def test_govuk_dates_from_first_published_at_never_from_updated_at():
    """updated_at is a content-store write and was two years later in the live probe."""

    content = {
        "/government/news/poor-governance-at-mermaids": {
            "title": "Poor governance at Mermaids",
            "first_published_at": "2024-10-24T00:05:00+01:00",
            "public_updated_at": "2024-10-24T00:05:00+01:00",
            "updated_at": "2026-08-12T16:52:41+01:00",
            "document_type": "press_release",
            "withdrawn_notice": {},
        }
    }
    [doc] = GovUkPolicyDocumentConnector(
        client=govuk_client([SEARCH_HIT], content)
    ).search("mermaids").documents
    assert doc.published_on == date(2024, 10, 24)
    assert doc.published_on_field == "first_published_at"
    assert doc.anchor_date().year == 2024
    assert doc.publisher == "Charity Commission"


def test_govuk_withdrawn_document_is_flagged_kept_and_still_dated():
    content = {
        "/government/news/poor-governance-at-mermaids": {
            "first_published_at": "2020-01-15T00:00:00+00:00",
            "withdrawn_notice": {"withdrawn_at": "2023-06-30T00:00:00+00:00"},
            "document_type": "guidance",
        }
    }
    [doc] = GovUkPolicyDocumentConnector(
        client=govuk_client([SEARCH_HIT], content)
    ).search("x").documents
    assert doc.withdrawn is True
    assert doc.status == "withdrawn"
    assert doc.published_on == date(2020, 1, 15)
    assert doc.identifiers["withdrawn_at"] == "2023-06-30"


def test_govuk_content_api_failure_yields_no_document_rather_than_a_search_timestamp():
    result = GovUkPolicyDocumentConnector(
        client=govuk_client([SEARCH_HIT], {})
    ).search("x")
    assert result.documents == []
    assert result.skip_reasons["GOVUK_CONTENT_API_UNAVAILABLE"] == 1


def test_govuk_result_without_a_content_path_is_skipped():
    hit = {**SEARCH_HIT, "link": "https://external.example/thing"}
    result = GovUkPolicyDocumentConnector(client=govuk_client([hit], {})).search("x")
    assert result.skip_reasons["GOVUK_NOT_A_CONTENT_PATH"] == 1


def test_govuk_content_item_without_first_published_at_is_kept_but_undated():
    content = {
        "/government/news/poor-governance-at-mermaids": {
            "public_updated_at": "2021-05-05T00:00:00+00:00",
            "document_type": "guidance",
        }
    }
    result = GovUkPolicyDocumentConnector(
        client=govuk_client([SEARCH_HIT], content)
    ).search("x")
    [doc] = result.documents
    assert doc.is_dated is False
    assert doc.last_updated == date(2021, 5, 5)
    assert result.skip_reasons["GOVUK_NO_FIRST_PUBLISHED_AT"] == 1


# --------------------------------------------------------------------------------------
# professional bodies
# --------------------------------------------------------------------------------------


SITEMAP = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://example.test/news/detail/2024/04/10/response-to-cass</loc>"
    "<lastmod>2026-08-01</lastmod></url>"
    "<url><loc>https://example.test/resources/gender-identity-guidance</loc>"
    "<lastmod>2026-08-01</lastmod></url>"
    "<url><loc>https://example.test/about/contact</loc></url>"
    "</urlset>"
)

JSON_LD_PAGE = (
    "<html><head><title>Response to the Cass Review | Body</title>"
    '<script type="application/ld+json">'
    + json.dumps(
        {
            "@graph": [
                {
                    "@type": "NewsArticle",
                    "datePublished": "2024-04-10T00:01:00+01:00",
                    "dateModified": "2025-02-02T00:00:00+01:00",
                }
            ]
        }
    )
    + "</script></head><body></body></html>"
)

UNDATED_PAGE = "<html><head><title>Gender identity guidance | Body</title></head></html>"


def body_client(pages: dict[str, str]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        key = str(request.url)
        if key not in pages:
            return httpx.Response(404, text="missing")
        return httpx.Response(
            200, text=pages[key], headers={"content-type": "text/html; charset=utf-8"}
        )

    return client_returning(handler)


DATED_BODY = ProfessionalBody(
    key="test", name="Test Body", sitemap_url="https://example.test/sitemap.xml"
)
URL_DATED_BODY = ProfessionalBody(
    key="urltest",
    name="URL Dated Body",
    sitemap_url="https://example.test/sitemap.xml",
    url_date_pattern=PROFESSIONAL_BODIES["rcpsych"].url_date_pattern,
)


def test_professional_body_reads_schema_org_date_published():
    pages = {
        "https://example.test/sitemap.xml": SITEMAP,
        "https://example.test/news/detail/2024/04/10/response-to-cass": JSON_LD_PAGE,
        "https://example.test/resources/gender-identity-guidance": UNDATED_PAGE,
    }
    result = ProfessionalBodyConnector(client=body_client(pages)).harvest(
        DATED_BODY, keywords=["cass", "gender"]
    )
    by_url = {doc.url: doc for doc in result.documents}
    dated = by_url["https://example.test/news/detail/2024/04/10/response-to-cass"]
    assert dated.published_on == date(2024, 4, 10)
    assert dated.published_on_field == "schema.org datePublished"
    assert dated.last_updated == date(2025, 2, 2)
    assert dated.title == "Response to the Cass Review"


def test_professional_body_page_without_a_declared_date_is_undated_not_lastmod_dated():
    """The sitemap says 2026-08-01. That must not become the publication date."""

    pages = {
        "https://example.test/sitemap.xml": SITEMAP,
        "https://example.test/news/detail/2024/04/10/response-to-cass": JSON_LD_PAGE,
        "https://example.test/resources/gender-identity-guidance": UNDATED_PAGE,
    }
    result = ProfessionalBodyConnector(client=body_client(pages)).harvest(
        DATED_BODY, keywords=["gender"]
    )
    [doc] = [d for d in result.documents if d.url.endswith("gender-identity-guidance")]
    assert doc.is_dated is False
    assert "lastmod" in doc.undated_reason
    assert result.skip_reasons["TEST_NO_PUBLICATION_DATE"] == 1


def test_professional_body_takes_the_date_from_the_canonical_url_without_fetching():
    """RCPsych encodes the publication date in the path, as legislation.gov.uk does."""

    fetched: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        fetched.append(str(request.url))
        if str(request.url).endswith("sitemap.xml"):
            return httpx.Response(200, text=SITEMAP)
        return httpx.Response(500, text="should not have been fetched")

    result = ProfessionalBodyConnector(client=client_returning(handler)).harvest(
        URL_DATED_BODY, keywords=["cass"]
    )
    [doc] = result.documents
    assert doc.published_on == date(2024, 4, 10)
    assert doc.published_on_field.startswith("canonical URL path")
    assert fetched == ["https://example.test/sitemap.xml"]


def test_professional_body_http_error_on_a_page_is_unknown_not_absent():
    pages = {"https://example.test/sitemap.xml": SITEMAP}
    result = ProfessionalBodyConnector(client=body_client(pages)).harvest(
        DATED_BODY, keywords=["gender-identity-guidance"]
    )
    [doc] = result.documents
    assert doc.is_dated is False
    assert "HTTP 404" in doc.undated_reason and "not the same as absent" in doc.undated_reason


def test_professional_body_sitemap_with_a_bom_still_parses():
    pages = {"https://example.test/sitemap.xml": "﻿" + SITEMAP}
    urls = ProfessionalBodyConnector(client=body_client(pages)).sitemap_urls(DATED_BODY)
    assert len(urls) == 3


def test_professional_body_unparseable_sitemap_falls_back_to_regex():
    broken = "<urlset><loc>https://example.test/a</loc><url unclosed"
    pages = {"https://example.test/sitemap.xml": broken}
    urls = ProfessionalBodyConnector(client=body_client(pages)).sitemap_urls(DATED_BODY)
    assert urls == ["https://example.test/a"]


def test_professional_body_registry_covers_the_three_permitted_hosts():
    assert set(PROFESSIONAL_BODIES) == {"rcpch", "bps", "rcpsych"}
    assert PROFESSIONAL_BODIES["rcpsych"].url_date_pattern is not None
    assert PROFESSIONAL_BODIES["rcpch"].url_date_pattern is None
