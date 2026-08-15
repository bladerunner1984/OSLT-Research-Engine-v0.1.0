import json

import httpx

from oslt_research.connectors.base import HarvestQuery
from oslt_research.connectors.crossref import CrossrefConnector
from oslt_research.connectors.openalex import OpenAlexConnector
from oslt_research.connectors.pubmed import PubMedConnector


async def test_openalex_connector_parses_records():
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "display_name": "OpenAlex title",
                "publication_date": "2024-01-01",
                "ids": {"doi": "https://doi.org/10.1/test"},
                "authorships": [{"author": {"display_name": "A Author"}}],
                "abstract_inverted_index": {"Hello": [0], "world": [1]},
                "type": "article",
                "cited_by_count": 3,
                "is_retracted": False,
            }
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/works"
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://api.openalex.org"
    ) as client:
        records = await OpenAlexConnector(client=client).harvest(
            HarvestQuery(query_id="Q", concept="test", max_records=1)
        )
    assert records[0].title == "OpenAlex title"
    assert "Hello world" in records[0].content
    assert records[0].identifiers["doi"].endswith("10.1/test")


async def test_crossref_connector_parses_records():
    payload = {
        "message": {
            "items": [
                {
                    "DOI": "10.2/test",
                    "title": ["Crossref title"],
                    "abstract": "Abstract",
                    "author": [{"given": "A", "family": "Author"}],
                    "URL": "https://doi.org/10.2/test",
                    "issued": {"date-parts": [[2024, 2, 3]]},
                    "type": "journal-article",
                }
            ]
        }
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await CrossrefConnector(client=client).harvest(
            HarvestQuery(query_id="Q", concept="test", max_records=1)
        )
    assert records[0].published_at == "2024-02-03"
    assert records[0].authors == ["A Author"]


async def test_pubmed_connector_uses_search_then_summary():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["123"]}})
        if request.url.path.endswith("esummary.fcgi"):
            return httpx.Response(
                200,
                json={
                    "result": {
                        "123": {
                            "title": "PubMed title",
                            "pubdate": "2024",
                            "authors": [{"name": "A Author"}],
                            "articleids": [
                                {"idtype": "doi", "value": "10.3/test"},
                            ],
                            "pubtype": ["Journal Article"],
                        }
                    }
                },
            )
        return httpx.Response(404, text=json.dumps({"error": "unexpected"}))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await PubMedConnector(client=client).harvest(
            HarvestQuery(query_id="Q", concept="test", max_records=1)
        )
    assert records[0].source_record_id == "123"
    assert records[0].identifiers["doi"] == "10.3/test"

from oslt_research.connectors.clinicaltrials import ClinicalTrialsConnector


async def test_clinicaltrials_connector_captures_registration_metadata():
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/version":
            return httpx.Response(200, json={"dataTimestamp": "2026-08-06T12:00:00Z"})
        if request.url.path == "/api/v2/studies":
            assert request.url.params["query.term"] == "gender dysphoria"
            return httpx.Response(
                200,
                json={
                    "studies": [
                        {
                            "protocolSection": {
                                "identificationModule": {
                                    "nctId": "NCT00000001",
                                    "briefTitle": "Registered trial",
                                },
                                "statusModule": {
                                    "overallStatus": "COMPLETED",
                                    "studyFirstPostDateStruct": {"date": "2024-01-01"},
                                },
                                "descriptionModule": {"briefSummary": "Trial summary"},
                                "designModule": {
                                    "studyType": "INTERVENTIONAL",
                                    "phases": ["PHASE2"],
                                    "enrollmentInfo": {"count": 100},
                                },
                                "conditionsModule": {
                                    "conditions": ["Gender Dysphoria"],
                                    "keywords": ["adolescent"],
                                },
                                "sponsorCollaboratorsModule": {
                                    "leadSponsor": {"name": "Research Institute"}
                                },
                            },
                            "resultsSection": {"participantFlowModule": {}},
                        }
                    ]
                },
            )
        return httpx.Response(404, json={"error": "unexpected path"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        records = await ClinicalTrialsConnector(client=client).harvest(
            HarvestQuery(
                query_id="Q-CT",
                concept="gender dysphoria",
                max_records=1,
            )
        )

    record = records[0]
    assert record.source_record_id == "NCT00000001"
    assert record.identifiers == {"nct": "NCT00000001"}
    assert record.metadata["record_kind"] == "registration"
    assert record.metadata["has_results_posted"] is True
    assert record.metadata["data_version"] == "2026-08-06T12:00:00Z"
    assert record.authors == ["Research Institute"]
