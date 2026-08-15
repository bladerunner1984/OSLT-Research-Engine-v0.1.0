from __future__ import annotations

import csv
from pathlib import Path

import pytest

from oslt_research.connectors.base import HarvestQuery, RawRecord, SourceConnector
from oslt_research.evidence.provenance import sha256_text
from oslt_research.pipelines.kernel_harvest import (
    build_proposition_queries,
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
