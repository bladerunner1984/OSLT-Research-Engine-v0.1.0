from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.base import HarvestQuery
from oslt_research.connectors.europepmc import EuropePmcConnector


def result(record_id="123", *, doi="10.1/a", pmid="123", title="A study",
           abstract="An abstract", source="MED") -> dict:
    return {
        "id": record_id, "source": source, "pmid": pmid, "doi": doi,
        "title": title, "abstractText": abstract,
        "authorString": "Smith J, Jones A.", "firstPublicationDate": "2024-01-15",
        "journalInfo": {"journal": {"title": "A Journal"}},
        "citedByCount": 4, "isOpenAccess": "Y",
    }


def connector_for(*pages: dict) -> EuropePmcConnector:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        index = min(calls["n"], len(pages) - 1)
        calls["n"] += 1
        return httpx.Response(200, json=pages[index])

    transport = httpx.MockTransport(handler)
    return EuropePmcConnector(client=httpx.AsyncClient(transport=transport))


def page(*results: dict, cursor: str | None = None) -> dict:
    body: dict = {"hitCount": len(results), "resultList": {"result": list(results)}}
    if cursor:
        body["nextCursorMark"] = cursor
    return body


def query(**overrides) -> HarvestQuery:
    payload = {"query_id": "Q1", "concept": "gender dysphoria", "max_records": 10}
    payload.update(overrides)
    return HarvestQuery(**payload)


async def test_result_maps_to_a_raw_record():
    [record] = await connector_for(page(result())).harvest(query())
    assert record.source_name == "EuropePMC"
    assert record.identifiers == {"pmid": "123", "doi": "10.1/a"}
    assert record.content == "An abstract"
    assert record.authors == ["Smith J", "Jones A."]
    assert record.published_at == "2024-01-15"
    assert record.source_uri.endswith("/MED/123")


async def test_abstract_text_is_carried_inline():
    """The whole point: no second lookup to get usable content."""

    [record] = await connector_for(page(result(abstract="x" * 900))).harvest(query())
    assert len(record.content) == 900


async def test_duplicate_ids_across_pages_are_dropped():
    """Deep paging on this API can repeat results; duplicates would inflate independence."""

    repeated = page(result("1"), cursor="c2")
    records = await connector_for(repeated, repeated).harvest(query(max_records=10))
    assert len(records) == 1


async def test_a_cursor_that_does_not_advance_stops_paging():
    stuck = page(result("1"), cursor="same")
    records = await connector_for(stuck).harvest(query(max_records=500))
    assert len(records) == 1


async def test_max_records_is_respected():
    big = page(*[result(str(i), doi=f"10.1/{i}", pmid=str(i)) for i in range(20)], cursor="c2")
    records = await connector_for(big).harvest(query(max_records=5))
    assert len(records) == 5


async def test_empty_result_list_terminates():
    assert await connector_for(page()).harvest(query()) == []


async def test_missing_identifiers_are_omitted_not_blanked():
    [record] = await connector_for(page(result(doi="", pmid=""))).harvest(query())
    assert "doi" not in record.identifiers and "pmid" not in record.identifiers


async def test_date_window_is_pushed_into_the_query():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(request.url.params).get("query", "")
        return httpx.Response(200, json=page(result()))

    connector = EuropePmcConnector(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    await connector.harvest(query(from_date="2015-01-01", to_date="2020-01-01"))
    assert "FIRST_PDATE:[2015-01-01 TO 2020-01-01]" in captured["query"]


async def test_registered_as_ds035_in_the_source_map():
    from oslt_research.pipelines.harvest import SOURCE_IDS

    assert SOURCE_IDS["EuropePMC"] == "DS035"


async def test_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    connector = EuropePmcConnector(client=httpx.AsyncClient(transport=transport))
    with pytest.raises(httpx.HTTPStatusError):
        await connector.harvest(query())
