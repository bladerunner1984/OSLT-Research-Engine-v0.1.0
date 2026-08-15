from __future__ import annotations

import pytest

from oslt_research.connectors.base import HarvestQuery, RawRecord, SourceConnector
from oslt_research.domain.enums import EvidenceLane
from oslt_research.evidence.provenance import sha256_text
from oslt_research.pipelines.counterevidence import (
    LANE_QUERY_TERMS,
    MANDATORY_LANES,
    CounterevidenceHarvester,
    LaneSearchRecord,
)


class StubConnector(SourceConnector):
    source_name = "Stub"
    connector_version = "1"

    def __init__(self, *, content: str = "", fail: bool = False, records: int = 1):
        self.content = content
        self.fail = fail
        self.records = records
        self.queries: list[str] = []

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        self.queries.append(query.concept)
        if self.fail:
            raise RuntimeError("upstream unavailable")
        return [
            RawRecord(
                source_name=self.source_name,
                source_record_id=f"{query.query_id}-{index}",
                title=f"Result {index}",
                content=self.content,
                source_uri=f"https://example.org/{query.query_id}/{index}",
                identifiers={"doi": f"10.1/{query.query_id}-{index}"},
                raw_response_hash=sha256_text(f"{query.query_id}{index}"),
            )
            for index in range(self.records)
        ]


# ---------------------------------------------------------------- configuration


def test_every_mandatory_lane_has_query_terms():
    for lane in MANDATORY_LANES:
        assert LANE_QUERY_TERMS.get(lane), f"{lane} has no targeted query"


def test_harvester_rejects_invalid_page_size():
    with pytest.raises(ValueError):
        CounterevidenceHarvester(max_records_per_query=0)


# --------------------------------------------------------------------- searching


async def test_each_lane_gets_its_own_targeted_queries():
    connector = StubConnector(content="no significant association found")
    report = await CounterevidenceHarvester().harvest(
        base_concept="gender dysphoria referral", connectors=[connector]
    )
    assert len(connector.queries) == sum(len(terms) for terms in LANE_QUERY_TERMS.values())
    assert all(query.startswith("gender dysphoria referral ") for query in connector.queries)


async def test_mandatory_lanes_are_satisfied_after_a_clean_run():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector()]
    )
    assert report.mandatory_lanes_satisfied()
    assert report.missing_mandatory_lanes() == []
    assert set(MANDATORY_LANES) <= report.lanes_searched()


async def test_an_empty_lane_still_counts_as_searched():
    """Finding no counterevidence is a result. Not looking is a governance failure."""

    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(records=0)]
    )
    null_record = report.lane_searches[EvidenceLane.NULL]
    assert null_record.records_returned == 0
    assert null_record.searched is True
    assert report.mandatory_lanes_satisfied()


async def test_a_failing_source_does_not_silently_mark_a_lane_searched():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(fail=True)]
    )
    assert not report.mandatory_lanes_satisfied()
    assert set(report.missing_mandatory_lanes()) == set(MANDATORY_LANES)
    assert report.lane_searches[EvidenceLane.NULL].errors


async def test_one_failing_source_does_not_sink_a_lane_with_a_working_source():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic",
        connectors=[StubConnector(fail=True), StubConnector(content="null findings")],
    )
    assert report.mandatory_lanes_satisfied()
    assert report.lane_searches[EvidenceLane.NULL].errors  # the failure is still recorded


async def test_lane_confirmation_counts_records_the_classifier_agrees_with():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(content="no significant association")]
    )
    assert report.lane_searches[EvidenceLane.NULL].records_lane_confirmed > 0
    # A retraction query returning null-language text should not confirm as a retraction.
    assert report.lane_searches[EvidenceLane.CORRECTION_RETRACTION].records_lane_confirmed == 0


async def test_evidence_is_deduplicated_across_lane_queries():
    report = await CounterevidenceHarvester(
        lanes=[EvidenceLane.NULL, EvidenceLane.RIVAL]
    ).harvest(base_concept="topic", connectors=[StubConnector()])
    ids = [item.evidence_id for item in report.evidence]
    assert len(ids) == len(set(ids))


async def test_summary_reports_lane_status_for_the_journal():
    report = await CounterevidenceHarvester(lanes=[EvidenceLane.NULL]).harvest(
        base_concept="topic", connectors=[StubConnector()]
    )
    summary = report.summary()
    assert summary["base_concept"] == "topic"
    assert "NULL" in summary["per_lane"]
    assert summary["per_lane"]["NULL"]["queries"]


# ----------------------------------------------------------------- search record


def test_lane_record_with_no_queries_is_not_searched():
    assert LaneSearchRecord(lane=EvidenceLane.NULL).searched is False


def test_lane_record_with_errors_but_results_still_counts_as_searched():
    record = LaneSearchRecord(
        lane=EvidenceLane.NULL,
        queries_run=["q"],
        records_returned=3,
        errors=["Stub:RuntimeError"],
    )
    assert record.searched is True
