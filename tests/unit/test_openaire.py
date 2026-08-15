from __future__ import annotations

from typing import Any

import httpx
import pytest

from oslt_research.connectors.base import HarvestQuery
from oslt_research.connectors.openaire import OpenAireConnector


def wrap(value: Any, **attrs: Any) -> dict[str, Any]:
    return {**attrs, "$": value}


def entity(
    *,
    obj_id: str = "doi_dedup___::abc",
    doi: str | None = "10.1/a",
    title: Any = None,
    description: Any = None,
    creator: Any = None,
    relevantdate: Any = None,
    dateofacceptance: Any = "2020-01-02",
    collected_at: str = "2026-07-23T09:54:03",
) -> dict[str, Any]:
    """Build one search result, defaulting to the multi-valued shapes the live API returns."""
    result_body: dict[str, Any] = {
        "title": title
        if title is not None
        else [wrap("A Study", **{"@classid": "main title"}), wrap("Alt", **{"@classid": "subtitle"})],
        "description": description if description is not None else wrap("An abstract."),
        "creator": creator
        if creator is not None
        else [wrap("Jones A", **{"@rank": "2"}), wrap("Smith J", **{"@rank": "1"})],
        "dateofacceptance": wrap(dateofacceptance) if dateofacceptance else None,
        "publisher": wrap("A Publisher"),
        "bestaccessright": {"@classid": "OPEN", "@classname": "Open Access"},
        "collectedfrom": [{"@name": "Crossref"}, {"@name": "PubMed Central"}],
    }
    if relevantdate is not None:
        result_body["relevantdate"] = relevantdate
    if doi:
        result_body["pid"] = [
            wrap(doi, **{"@classid": "doi"}),
            wrap(38465656, **{"@classid": "pmid"}),
        ]
    return {
        "header": {"dri:objIdentifier": wrap(obj_id), "dri:dateOfCollection": wrap(collected_at)},
        "metadata": {"oaf:entity": {"oaf:result": result_body}},
    }


def page(*results: dict[str, Any], total: int | None = None) -> dict[str, Any]:
    body: list[Any] | dict[str, Any] = list(results) if len(results) != 1 else results[0]
    return {
        "response": {
            "header": {"total": wrap(total if total is not None else len(results))},
            "results": {"result": body} if results else {},
        }
    }


def connector_for(*pages: dict[str, Any]) -> tuple[OpenAireConnector, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        index = min(len(seen), len(pages) - 1)
        seen.append(request)
        return httpx.Response(200, json=pages[index])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenAireConnector(client=client), seen


def query(**overrides: Any) -> HarvestQuery:
    base: dict[str, Any] = {"query_id": "q1", "concept": "gender dysphoria", "max_records": 10}
    base.update(overrides)
    return HarvestQuery(**base)


@pytest.mark.asyncio
async def test_harvest_extracts_core_fields() -> None:
    connector, _ = connector_for(page(entity()))
    records = await connector.harvest(query())

    assert len(records) == 1
    record = records[0]
    assert record.source_name == "OpenAIRE"
    assert record.source_record_id == "doi_dedup___::abc"
    assert record.title == "A Study"
    assert record.content == "An abstract."
    assert record.identifiers["doi"] == "10.1/a"
    assert record.identifiers["pmid"] == "38465656"
    assert record.source_uri == "https://doi.org/10.1/a"
    assert record.raw_response_hash


@pytest.mark.asyncio
async def test_authors_ordered_by_rank_not_array_order() -> None:
    connector, _ = connector_for(page(entity()))
    records = await connector.harvest(query())
    assert records[0].authors == ["Smith J", "Jones A"]


@pytest.mark.asyncio
async def test_single_dict_fields_handled_like_lists() -> None:
    connector, _ = connector_for(
        page(
            entity(
                title=wrap("Solo Title", **{"@classid": "main title"}),
                creator=wrap("Solo Author"),
            )
        )
    )
    records = await connector.harvest(query())
    assert records[0].title == "Solo Title"
    assert records[0].authors == ["Solo Author"]


@pytest.mark.asyncio
async def test_bare_scalar_fields_handled() -> None:
    connector, _ = connector_for(page(entity(title="Bare Title", description="Bare abstract")))
    records = await connector.harvest(query())
    assert records[0].title == "Bare Title"
    assert records[0].content == "Bare abstract"


@pytest.mark.asyncio
async def test_longest_description_wins() -> None:
    connector, _ = connector_for(
        page(entity(description=[wrap("Short."), wrap("A considerably longer abstract body.")]))
    )
    records = await connector.harvest(query())
    assert records[0].content == "A considerably longer abstract body."


@pytest.mark.asyncio
async def test_publication_date_prefers_published_print_over_created() -> None:
    """`created` is the metadata-registration date and runs years after publication."""
    connector, _ = connector_for(
        page(
            entity(
                dateofacceptance="2018-04-19",
                relevantdate=[
                    wrap("2020-12-24", **{"@classid": "created"}),
                    wrap("2018-04-19", **{"@classid": "published-print"}),
                ],
            )
        )
    )
    records = await connector.harvest(query())
    assert records[0].published_at == "2018-04-19"


@pytest.mark.asyncio
async def test_publication_date_never_uses_collection_timestamp() -> None:
    connector, _ = connector_for(
        page(
            entity(
                dateofacceptance=None,
                relevantdate=[wrap("2020-12-24", **{"@classid": "created"})],
                collected_at="2026-07-23T09:54:03",
            )
        )
    )
    records = await connector.harvest(query())
    assert records[0].published_at is None
    assert records[0].metadata["openaire_collected_at"].startswith("2026-07-23")


@pytest.mark.asyncio
async def test_publication_date_falls_back_to_acceptance() -> None:
    connector, _ = connector_for(page(entity(dateofacceptance="2021-05-06", relevantdate=None)))
    records = await connector.harvest(query())
    assert records[0].published_at == "2021-05-06"


@pytest.mark.asyncio
async def test_deduplicates_by_object_id_across_pages() -> None:
    first = page(entity(obj_id="a", doi="10.1/a"), entity(obj_id="b", doi="10.1/b"))
    second = page(entity(obj_id="a", doi="10.1/a"))
    connector, _ = connector_for(first, second)
    records = await connector.harvest(query(max_records=2))
    assert [r.source_record_id for r in records] == ["a", "b"]


@pytest.mark.asyncio
async def test_deduplicates_by_doi_case_insensitively() -> None:
    connector, _ = connector_for(
        page(entity(obj_id="a", doi="10.1/A"), entity(obj_id="b", doi="10.1/a"))
    )
    records = await connector.harvest(query())
    assert len(records) == 1


@pytest.mark.asyncio
async def test_query_term_is_sent_as_keywords() -> None:
    connector, seen = connector_for(page(entity()))
    await connector.harvest(query(concept="volcanology"))
    assert seen[0].url.params["keywords"] == "volcanology"
    assert seen[0].url.params["format"] == "json"


@pytest.mark.asyncio
async def test_date_bounds_and_extra_filters_are_forwarded() -> None:
    connector, seen = connector_for(page(entity()))
    await connector.harvest(
        query(from_date="2020-01-01", to_date="2021-01-01", extra_filters={"OA": "true"})
    )
    params = seen[0].url.params
    assert params["fromDateAccepted"] == "2020-01-01"
    assert params["toDateAccepted"] == "2021-01-01"
    assert params["OA"] == "true"


@pytest.mark.asyncio
async def test_pages_until_max_records_then_stops() -> None:
    full = page(*[entity(obj_id=f"p1-{i}", doi=f"10.1/{i}") for i in range(3)])
    second = page(*[entity(obj_id=f"p2-{i}", doi=f"10.2/{i}") for i in range(3)])
    connector, seen = connector_for(full, second)
    connector.MAX_PAGE_SIZE = 3  # force a second request without fabricating a 100-item page
    records = await connector.harvest(query(max_records=6))
    assert len(records) == 6
    assert [int(r.url.params["page"]) for r in seen] == [1, 2]


@pytest.mark.asyncio
async def test_short_page_ends_pagination() -> None:
    connector, seen = connector_for(page(entity(obj_id="a", doi="10.1/a")))
    records = await connector.harvest(query(max_records=50))
    assert len(records) == 1
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_empty_result_set_returns_nothing() -> None:
    connector, _ = connector_for(page())
    assert await connector.harvest(query()) == []


@pytest.mark.asyncio
async def test_record_without_identifier_is_skipped() -> None:
    bad = entity(obj_id="", doi=None)
    connector, _ = connector_for(page(bad, entity(obj_id="ok", doi="10.9/z")))
    records = await connector.harvest(query())
    assert [r.source_record_id for r in records] == ["ok"]


@pytest.mark.asyncio
async def test_missing_entity_body_is_skipped() -> None:
    connector, _ = connector_for(page({"header": {}, "metadata": {}}))
    assert await connector.harvest(query()) == []


@pytest.mark.asyncio
async def test_source_uri_falls_back_to_explore_when_no_doi() -> None:
    connector, _ = connector_for(page(entity(obj_id="xyz", doi=None)))
    records = await connector.harvest(query())
    assert records[0].source_uri.endswith("articleId=xyz")


@pytest.mark.asyncio
async def test_http_error_propagates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    connector = OpenAireConnector(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(httpx.HTTPStatusError):
        await connector.harvest(query())
