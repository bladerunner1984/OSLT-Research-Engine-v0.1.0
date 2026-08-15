import json

from oslt_research.connectors.base import HarvestQuery
from oslt_research.connectors.fixture import FixtureConnector
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.pilot1 import run_pilot_one


async def test_pilot_one_vertical_slice(tmp_path):
    connector = FixtureConnector(
        [
            {
                "id": "1",
                "title": "Study one",
                "identifiers": {"doi": "10.1/one"},
                "metadata": {"orientation": "MIXED"},
            },
            {
                "id": "2",
                "title": "Study two",
                "identifiers": {"doi": "10.1/two"},
                "metadata": {"orientation": "NOT_ASSESSABLE"},
            },
        ]
    )
    output = await run_pilot_one(
        run_id="P1-TEST",
        connectors=[connector],
        query=HarvestQuery(
            query_id="Q1",
            concept="test",
            proposition_ids=["MD11", "MX14"],
            max_records=10,
        ),
        store=SQLiteStore(tmp_path / "pilot.db"),
        output_root=tmp_path / "output",
    )
    assert len(output.evidence) == 2
    assert len(output.kernel_results) == 2
    manifest = json.loads(output.corpus_manifest_path.read_text())
    assert manifest["admitted_count"] == 2
    assert manifest["connector_versions"] == {"Fixture": connector.connector_version}
    assert manifest["source_record_counts"] == {"Fixture": 2}
    assert (tmp_path / "output/computation-journal.jsonl").exists()
