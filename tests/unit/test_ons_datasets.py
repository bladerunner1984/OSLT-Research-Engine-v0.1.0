from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.ons_datasets import (
    OnsDataset,
    OnsDatasetsConnector,
    OnsVersion,
)


def connector_for(routes: dict[str, dict]) -> OnsDatasetsConnector:
    def handler(request: httpx.Request) -> httpx.Response:
        for fragment, body in routes.items():
            if fragment in str(request.url):
                return httpx.Response(200, json=body)
        return httpx.Response(404, json={})

    return OnsDatasetsConnector(client=httpx.Client(transport=httpx.MockTransport(handler)))


DATASETS = {"items": [
    {"id": "mid-year-pop-est", "title": "Population Estimates", "description": "by age and sex"},
    {"id": "labour-market", "title": "UK Labour Market", "description": "employment"},
]}
EDITIONS = {"items": [{
    "edition": "time-series",
    "links": {"latest_version": {"href": "https://api.beta.ons.gov.uk/v1/version-detail/3"}},
}]}
VERSION = {
    "version": "3", "release_date": "2024-06-01",
    "dimensions": [{"name": "time"}, {"name": "geography"}, {"name": "sex"}],
    "downloads": {"csv": {"href": "https://example.org/data.csv", "size": "100"}},
}


def test_datasets_are_listed():
    items = connector_for({"/datasets": DATASETS}).list_datasets()
    assert [item.dataset_id for item in items] == ["mid-year-pop-est", "labour-market"]


def test_search_matches_title_and_description():
    connector = connector_for({"/datasets": DATASETS})
    assert len(connector.search("population")) == 1
    assert len(connector.search("sex")) == 1          # matches the description
    assert connector.search("nothing here") == []


def test_search_is_case_insensitive():
    assert OnsDataset("x", "Population Estimates").matches("POPULATION")


def test_latest_version_follows_the_link_rather_than_composing_a_url():
    """Composing a versions URL returns 404; the API expects the link to be followed."""

    connector = connector_for({"/editions": EDITIONS, "/version-detail/3": VERSION})
    version = connector.latest_version("mid-year-pop-est")
    assert version is not None
    assert version.version == "3"
    assert version.dimensions == ["time", "geography", "sex"]
    assert version.has_download
    assert version.csv_url == "https://example.org/data.csv"


def test_edition_is_recorded_so_the_caller_knows_which_one_they_got():
    connector = connector_for({"/editions": EDITIONS, "/version-detail/3": VERSION})
    assert connector.latest_version("x").edition == "time-series"


def test_a_named_edition_can_be_requested():
    editions = {"items": [
        {"edition": "old", "links": {"latest_version": {"href": "https://x/version-detail/1"}}},
        {"edition": "new", "links": {"latest_version": {"href": "https://x/version-detail/3"}}},
    ]}
    connector = connector_for({"/editions": editions, "/version-detail/3": VERSION})
    assert connector.latest_version("x", edition="new").version == "3"


def test_dataset_with_no_editions_returns_none():
    assert connector_for({"/editions": {"items": []}}).latest_version("x") is None


def test_version_without_a_download_is_flagged():
    no_download = {**VERSION, "downloads": {}}
    connector = connector_for({"/editions": EDITIONS, "/version-detail/3": no_download})
    assert connector.latest_version("x").has_download is False


def test_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        OnsDatasetsConnector(client=httpx.Client(transport=transport)).list_datasets()
