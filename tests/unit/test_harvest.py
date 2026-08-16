from oslt_research.connectors.base import HarvestQuery, RawRecord
from oslt_research.connectors.fixture import FixtureConnector
from oslt_research.pipelines.harvest import (
    dependency_family_for,
    evidence_id_for,
    execute_harvest,
    normalise_doi,
    raw_record_to_evidence,
)


def raw(**updates):
    payload = dict(
        source_name="Fixture",
        source_record_id="1",
        title="A Study",
        content="A Study content",
        source_uri="fixture://1",
        published_at="2024-01-01",
        identifiers={"doi": "https://doi.org/10.1000/ABC"},
        authors=["A Author"],
        metadata={},
        raw_response_hash="a" * 64,
    )
    payload.update(updates)
    return RawRecord(**payload)


def test_doi_normalisation_and_dependency_family():
    assert normalise_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert dependency_family_for(raw()) == "doi:10.1000/abc"
    assert dependency_family_for(raw(identifiers={"pmid": "123"})) == "pmid:123"
    assert dependency_family_for(raw(identifiers={})).startswith("heuristic:")


def test_raw_record_conversion_is_admitted():
    query = HarvestQuery(query_id="Q1", concept="test", proposition_ids=["MD11"])
    item = raw_record_to_evidence(raw(), query)
    assert item.admitted
    assert item.proposition_ids == ["MD11"]
    assert item.metadata["query_id"] == "Q1"
    assert item.evidence_id == evidence_id_for(raw())


async def test_execute_harvest_with_fixture_connector():
    connector = FixtureConnector(
        [
            {
                "id": "1",
                "title": "One",
                "identifiers": {"doi": "10.1/one"},
            },
            {
                "id": "2",
                "title": "Two",
                "identifiers": {"doi": "10.1/two"},
            },
        ]
    )
    result = await execute_harvest(
        connector,
        HarvestQuery(query_id="Q", concept="fixture", max_records=2),
    )
    assert len(result.admitted) == 2
    assert result.rejected == []
    assert all(item.metadata["connector_version"] == connector.connector_version for item in result.evidence)
    assert all(
        item.provenance.codebook_or_schema_ref
        == f"connector:Fixture:v{connector.connector_version}"
        for item in result.evidence
    )


def test_harvested_records_are_lane_coded_at_construction():
    """The defect this guards: harvest persisted the whole corpus as UNCLASSIFIED."""

    from oslt_research.domain.enums import EvidenceLane, LaneCodingMethod

    item = raw_record_to_evidence(
        raw(content="An independent replication of the earlier finding"),
        HarvestQuery(query_id="Q1", concept="c"),
    )
    assert item.lane is EvidenceLane.REPLICATION
    assert item.lane_coding is not None
    assert item.lane_coding.method is LaneCodingMethod.AUTOMATED_CLASSIFIER


def test_harvested_record_with_no_cue_records_that_it_was_screened():
    item = raw_record_to_evidence(raw(), HarvestQuery(query_id="Q1", concept="c"))
    from oslt_research.domain.enums import EvidenceLane

    assert item.lane is EvidenceLane.UNCLASSIFIED
    assert item.lane_coding is not None, "screened-but-uncoded must differ from never screened"


async def test_execute_harvest_resolves_study_families():
    """Regression: the resolver existed but was never called from the harvest path.

    Symptom was invisible because dependency_family was populated - with the DOI - so the
    corpus looked clustered while every record was its own "family".
    """

    connector = FixtureConnector(
        [
            {
                "id": "1",
                "title": "Trial report",
                "content": "Primary results of NCT01234567 in adults.",
                "identifiers": {"doi": "10.1/one"},
            },
            {
                "id": "2",
                "title": "Trial follow-up",
                "content": "Two-year follow-up of NCT01234567.",
                "identifiers": {"doi": "10.1/two"},
            },
            {
                "id": "3",
                "title": "Unrelated",
                "content": "Nothing in common.",
                "identifiers": {"doi": "10.1/three"},
            },
        ]
    )
    query = HarvestQuery(query_id="Q1", concept="test", proposition_ids=["MD11"])
    result = await execute_harvest(connector, query)

    families = {item.evidence_id: item.dependency_family for item in result.evidence}
    assert len(set(families.values())) == 2
    for item in result.evidence:
        assert item.dependency_family.startswith("family:")
        assert item.metadata["dedup_key"].startswith("doi:")
        assert item.metadata["dependency_family_basis"]
