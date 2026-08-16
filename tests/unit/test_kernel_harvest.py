from __future__ import annotations

import csv
from pathlib import Path

import pytest

from oslt_research.connectors.base import HarvestQuery, RawRecord, SourceConnector
from oslt_research.evidence.provenance import sha256_text
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.counterevidence import (
    LANE_QUERY_TERMS,
    MANDATORY_LANES,
    load_lane_searches,
)
from oslt_research.pipelines.kernel_harvest import (
    build_proposition_queries,
    harvest_counterevidence_for_kernels,
    harvest_for_kernels,
)


REGISTRIES = Path(__file__).resolve().parents[2] / "registries"


class Stub(SourceConnector):
    source_name = "Stub"
    connector_version = "1"

    def __init__(self, *, records: int = 2, fail: bool = False, doi_prefix: str = "10.1"):
        self.records = records
        self.fail = fail
        self.doi_prefix = doi_prefix
        self.concepts: list[str] = []

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        self.concepts.append(query.concept)
        if self.fail:
            raise RuntimeError("source down")
        return [
            RawRecord(
                source_name=self.source_name,
                source_record_id=f"{self.doi_prefix}-{i}",
                title=f"Paper {i}",
                content="text",
                source_uri=f"https://example.org/{i}",
                identifiers={"doi": f"{self.doi_prefix}/{i}"},
                raw_response_hash=sha256_text(str(i)),
            )
            for i in range(self.records)
        ]


def write_registry(root: Path, rows: list[dict]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    fields = ["proposition_id", "model_family", "domain", "primary_outcome_construct"]
    with (root / "hypotheses.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return root


def test_query_is_built_from_domain_and_outcome_not_the_claim(tmp_path):
    """Searching a claim biases retrieval towards papers phrased the same way."""

    root = write_registry(tmp_path, [{
        "proposition_id": "P1", "model_family": "F",
        "domain": "Referral threshold", "primary_outcome_construct": "referral rate",
    }])
    [built] = build_proposition_queries(root)
    assert "referral" in built.concept and "threshold" in built.concept


def test_stopwords_are_dropped_from_the_concept(tmp_path):
    root = write_registry(tmp_path, [{
        "proposition_id": "P1", "model_family": "F",
        "domain": "The impact of and for", "primary_outcome_construct": "referral",
    }])
    [built] = build_proposition_queries(root)
    assert "the" not in built.concept.split()
    assert "and" not in built.concept.split()


def test_proposition_with_no_usable_terms_is_dropped(tmp_path):
    root = write_registry(tmp_path, [{
        "proposition_id": "P1", "model_family": "F",
        "domain": "", "primary_outcome_construct": "",
    }])
    assert build_proposition_queries(root) == []


def test_the_real_registry_yields_a_query_for_every_proposition():
    queries = build_proposition_queries(REGISTRIES)
    assert len(queries) == 64
    assert all(item.concept for item in queries)


async def test_records_are_tagged_with_their_proposition(tmp_path):
    root = write_registry(tmp_path, [{
        "proposition_id": "P1", "model_family": "F",
        "domain": "Referral threshold", "primary_outcome_construct": "referral rate",
    }])
    report = await harvest_for_kernels(
        queries=build_proposition_queries(root), connectors=[Stub()]
    )
    assert all("P1" in item.proposition_ids for item in report.evidence)


async def test_a_paper_answering_two_propositions_keeps_both(tmp_path):
    """Discarding the duplicate would silently lose proposition coverage."""

    root = write_registry(tmp_path, [
        {"proposition_id": "P1", "model_family": "F", "domain": "Alpha",
         "primary_outcome_construct": "referral"},
        {"proposition_id": "P2", "model_family": "F", "domain": "Beta",
         "primary_outcome_construct": "referral"},
    ])
    report = await harvest_for_kernels(
        queries=build_proposition_queries(root), connectors=[Stub(records=1)]
    )
    assert len(report.evidence) == 1
    assert report.evidence[0].proposition_ids == ["P1", "P2"]


async def test_a_failing_source_is_recorded_not_fatal(tmp_path):
    root = write_registry(tmp_path, [{
        "proposition_id": "P1", "model_family": "F", "domain": "Alpha",
        "primary_outcome_construct": "referral",
    }])
    report = await harvest_for_kernels(
        queries=build_proposition_queries(root), connectors=[Stub(fail=True)]
    )
    assert report.failures["P1"].startswith("Stub:")
    assert report.summary()["propositions_failed"] == 1


async def test_one_working_source_rescues_a_failing_one(tmp_path):
    root = write_registry(tmp_path, [{
        "proposition_id": "P1", "model_family": "F", "domain": "Alpha",
        "primary_outcome_construct": "referral",
    }])
    report = await harvest_for_kernels(
        queries=build_proposition_queries(root),
        connectors=[Stub(fail=True), Stub(doi_prefix="10.2")],
    )
    assert report.failures == {}
    assert report.evidence


async def test_summary_names_propositions_that_found_nothing(tmp_path):
    root = write_registry(tmp_path, [{
        "proposition_id": "P1", "model_family": "F", "domain": "Alpha",
        "primary_outcome_construct": "referral",
    }])
    report = await harvest_for_kernels(
        queries=build_proposition_queries(root), connectors=[Stub(records=0)]
    )
    assert report.summary()["propositions_with_no_results"] == ["P1"]


# ------------------------------------------------- counterevidence on the corpus path


async def test_counterevidence_sweep_persists_a_search_record_for_every_lane(tmp_path):
    store = SQLiteStore(tmp_path / "t.db")
    queries = [item for item in build_proposition_queries(REGISTRIES)][:1]
    report = await harvest_counterevidence_for_kernels(
        queries=queries,
        connectors=[Stub(records=0)],
        store=store,
        run_id="CE-TEST",
        request_delay_seconds=0.0,
    )
    rows = load_lane_searches(store, run_id="CE-TEST")
    assert {row["lane"] for row in rows} == {lane.value for lane in LANE_QUERY_TERMS}
    assert report.complete
    # Every mandatory lane searched and empty: a result, and recorded as one.
    mandatory = {row["lane"]: row for row in rows if row["mandatory"]}
    assert set(mandatory) == {lane.value for lane in MANDATORY_LANES}
    assert all(row["genuine_zero"] for row in mandatory.values())


async def test_counterevidence_sweep_names_the_propositions_it_could_not_cover(tmp_path):
    store = SQLiteStore(tmp_path / "t.db")
    queries = [item for item in build_proposition_queries(REGISTRIES)][:1]
    report = await harvest_counterevidence_for_kernels(
        queries=queries,
        connectors=[Stub(fail=True)],
        store=store,
        run_id="CE-TEST",
        request_delay_seconds=0.0,
    )
    assert not report.complete
    gaps = report.incomplete_propositions[queries[0].proposition_id]
    assert set(gaps) == {lane.value for lane in MANDATORY_LANES}
    # The gap is persisted, not merely returned in memory.
    rows = {row["lane"]: row for row in load_lane_searches(store, run_id="CE-TEST")}
    assert rows["CONTRADICT"]["status"] == "UNSEARCHED_ERROR"


async def test_counterevidence_concept_comes_from_domain_and_outcome_not_the_statement():
    """CRITICAL: searching the statement retrieves papers that agree with it.

    The base concept must be the registry's neutral subject-matter description. If any
    distinctive word of the proposition's own claim leaked into the query, the sweep
    would be retrieving agreement and calling it a search for disagreement.
    """

    rows = {
        row["proposition_id"]: row
        for row in csv.DictReader(
            (REGISTRIES / "hypotheses.csv").open(encoding="utf-8-sig")
        )
    }
    connector = Stub(records=0)
    queries = [item for item in build_proposition_queries(REGISTRIES) if item.proposition_id]
    target = queries[0]
    await harvest_counterevidence_for_kernels(
        queries=[target],
        connectors=[connector],
        run_id="CE-TEST",
        request_delay_seconds=0.0,
    )
    statement = rows[target.proposition_id]["statement"].casefold()
    stem_words = set(target.concept.split())
    registry_words = set(
        f"{rows[target.proposition_id]['domain']} "
        f"{rows[target.proposition_id]['primary_outcome_construct']}".casefold().split()
    )
    # Every word of the stem traces back to domain/outcome, never to the claim alone.
    leaked = [
        word
        for word in stem_words
        if word in statement and not any(word in item for item in registry_words)
    ]
    assert not leaked, f"statement text leaked into the search stem: {leaked}"
    assert connector.concepts and all(
        concept.startswith(target.concept + " ") for concept in connector.concepts
    )
