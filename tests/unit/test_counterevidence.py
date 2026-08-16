from __future__ import annotations

import pytest

from oslt_research.connectors.base import HarvestQuery, RawRecord, SourceConnector
from oslt_research.domain.enums import EvidenceLane
from oslt_research.evidence.provenance import sha256_text
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.counterevidence import (
    LANE_QUERY_TERMS,
    MANDATORY_LANES,
    STATUS_NOT_ATTEMPTED,
    STATUS_SEARCHED_COMPLETE,
    STATUS_SEARCHED_PARTIAL,
    STATUS_UNSEARCHED_ERROR,
    CounterevidenceHarvester,
    LaneSearchRecord,
    MandatoryLaneGapError,
    load_lane_searches,
    save_lane_searches,
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


# ------------------------------------------------ searched-zero vs unsearched (the point)


def test_status_distinguishes_never_attempted_from_searched():
    assert LaneSearchRecord(lane=EvidenceLane.CONTRADICT).status == STATUS_NOT_ATTEMPTED


async def test_a_lane_that_returned_nothing_records_a_genuine_zero():
    """The distinction the whole class exists for.

    A zero that was searched for is a statement about the literature. A zero that was
    never searched for is a statement about us, and the corpus must not confuse them.
    """

    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(records=0)]
    )
    record = report.lane_searches[EvidenceLane.CONTRADICT]
    assert record.status == STATUS_SEARCHED_COMPLETE
    assert record.genuine_zero is True
    assert EvidenceLane.CONTRADICT in report.genuine_zero_lanes()


async def test_a_lane_whose_every_query_failed_is_unsearched_not_zero():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(fail=True)]
    )
    record = report.lane_searches[EvidenceLane.CONTRADICT]
    assert record.status == STATUS_UNSEARCHED_ERROR
    assert record.records_returned == 0
    # An HTTP failure must never be reportable as "we looked and found nothing".
    assert record.genuine_zero is False
    assert report.genuine_zero_lanes() == []


async def test_a_partial_sweep_returning_nothing_is_not_a_citable_zero():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic",
        connectors=[StubConnector(fail=True), StubConnector(records=0)],
    )
    record = report.lane_searches[EvidenceLane.CONTRADICT]
    assert record.status == STATUS_SEARCHED_PARTIAL
    assert record.searched is True
    assert record.genuine_zero is False


# -------------------------------------------------------------- mandatory lane enforcement


async def test_enforcement_raises_when_a_mandatory_lane_was_not_searched():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(fail=True)]
    )
    with pytest.raises(MandatoryLaneGapError):
        report.enforce_mandatory_lanes()


async def test_enforcement_passes_after_a_clean_run():
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(records=0)]
    )
    report.enforce_mandatory_lanes()


async def test_a_lane_omitted_from_the_sweep_is_reported_not_attempted():
    report = await CounterevidenceHarvester(lanes=[EvidenceLane.NULL]).harvest(
        base_concept="topic", connectors=[StubConnector()]
    )
    assert report.mandatory_lane_status()["CONTRADICT"] == STATUS_NOT_ATTEMPTED
    assert not report.mandatory_lanes_satisfied()


# ------------------------------------------------------------------------ query symmetry


def test_support_and_contradict_searches_are_symmetric():
    """An asymmetric pair manufactures its own result.

    If SUPPORT were searched with more or richer phrasings than CONTRADICT, the shortfall
    of counterevidence would be an artefact of the query design, not of the literature.
    """

    support = LANE_QUERY_TERMS[EvidenceLane.SUPPORT]
    contradict = LANE_QUERY_TERMS[EvidenceLane.CONTRADICT]
    assert len(support) == len(contradict)
    assert [len(term.split()) for term in support] == [
        len(term.split()) for term in contradict
    ]


async def test_every_lane_query_shares_one_unmodified_base_concept():
    connector = StubConnector()
    await CounterevidenceHarvester().harvest(
        base_concept="subject matter stem", connectors=[connector]
    )
    assert all(query.startswith("subject matter stem ") for query in connector.queries)


# --------------------------------------------------------------------------- persistence


async def test_lane_searches_persist_and_read_back(tmp_path):
    store = SQLiteStore(tmp_path / "t.db")
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(records=0)], store=store
    )
    ids = save_lane_searches(store, run_id="CE-TEST", report=report)
    assert len(ids) == len(report.lane_searches)
    rows = load_lane_searches(store, run_id="CE-TEST")
    by_lane = {row["lane"]: row for row in rows}
    assert by_lane["CONTRADICT"]["status"] == STATUS_SEARCHED_COMPLETE
    assert by_lane["CONTRADICT"]["genuine_zero"] is True
    assert by_lane["CONTRADICT"]["queries_run"]


async def test_an_unsearched_lane_is_persisted_as_a_row_not_an_absence(tmp_path):
    """A failed lane must leave a row saying so.

    Persisting only the lanes that worked would put the corpus back exactly where it
    started: an absence with no way to tell whether anyone looked.
    """

    store = SQLiteStore(tmp_path / "t.db")
    report = await CounterevidenceHarvester().harvest(
        base_concept="topic", connectors=[StubConnector(fail=True)], store=store
    )
    save_lane_searches(store, run_id="CE-TEST", report=report)
    rows = {row["lane"]: row for row in load_lane_searches(store, run_id="CE-TEST")}
    assert rows["CONTRADICT"]["status"] == STATUS_UNSEARCHED_ERROR
    assert rows["CONTRADICT"]["searched"] is False
    assert rows["CONTRADICT"]["genuine_zero"] is False
    assert rows["CONTRADICT"]["errors"]


async def test_rerunning_a_lane_search_updates_rather_than_duplicates(tmp_path):
    store = SQLiteStore(tmp_path / "t.db")
    for _ in range(2):
        report = await CounterevidenceHarvester(lanes=[EvidenceLane.NULL]).harvest(
            base_concept="topic", connectors=[StubConnector()], store=store
        )
        save_lane_searches(store, run_id="CE-TEST", report=report)
    assert len(load_lane_searches(store, run_id="CE-TEST")) == 1
