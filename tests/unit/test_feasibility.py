from __future__ import annotations

import csv
from pathlib import Path

import pytest

from oslt_research.governance.feasibility import (
    Reachability,
    assess_feasibility,
)


REGISTRIES = Path(__file__).resolve().parents[2] / "registries"


def write_registry(root: Path, workstreams: list[dict], hypotheses: list[dict]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, rows, fields in (
        ("workstreams.csv", workstreams, ["workstream_id", "access_summary"]),
        (
            "hypotheses.csv",
            hypotheses,
            [
                "proposition_id",
                "model_family",
                "domain",
                "required_workstreams",
                "temporal_requirement",
                "maximum_claim_state",
            ],
        ),
    ):
        with (root / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return root


def hypothesis(**overrides) -> dict:
    payload = {
        "proposition_id": "P1",
        "model_family": "FAMILY_A",
        "domain": "A domain",
        "required_workstreams": "W01",
        "temporal_requirement": "context-aligned temporal comparison",
        "maximum_claim_state": "LIMITED_CAUSAL_EVIDENCE",
    }
    payload.update(overrides)
    return payload


# ------------------------------------------------------------- classification


def test_open_workstream_and_aggregate_design_is_testable(tmp_path):
    root = write_registry(
        tmp_path, [{"workstream_id": "W01", "access_summary": "OPEN;OPEN_API"}], [hypothesis()]
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.OPEN_TESTABLE
    assert result.testable_now


def test_individual_level_design_is_not_answerable_from_aggregate(tmp_path):
    root = write_registry(
        tmp_path,
        [{"workstream_id": "W01", "access_summary": "OPEN_AGGREGATE"}],
        [hypothesis(temporal_requirement="pre-exposure baseline and longitudinal follow-up")],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.NEEDS_INDIVIDUAL_LEVEL
    assert "at any sample size" in result.reason


def test_workstream_without_an_open_route_blocks(tmp_path):
    root = write_registry(
        tmp_path,
        [{"workstream_id": "W01", "access_summary": "RESTRICTED_TRE;LICENSED"}],
        [hypothesis()],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.NEEDS_RESTRICTED_ACCESS
    assert result.blocking_workstreams == ["W01"]


def test_primary_research_requires_collection_not_just_access(tmp_path):
    root = write_registry(
        tmp_path,
        [{"workstream_id": "W01", "access_summary": "PRIMARY_RESEARCH"}],
        [hypothesis()],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.NEEDS_PRIMARY_COLLECTION
    assert "consent" in result.reason


def test_unknown_workstream_blocks_rather_than_passing_silently(tmp_path):
    root = write_registry(tmp_path, [], [hypothesis(required_workstreams="W99")])
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.NEEDS_RESTRICTED_ACCESS


def test_one_blocked_workstream_blocks_the_whole_proposition(tmp_path):
    root = write_registry(
        tmp_path,
        [
            {"workstream_id": "W01", "access_summary": "OPEN"},
            {"workstream_id": "W02", "access_summary": "RESTRICTED_TRE"},
        ],
        [hypothesis(required_workstreams="W01;W02")],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.NEEDS_RESTRICTED_ACCESS


# --------------------------------------------------------- coverage asymmetry


def test_family_with_no_testable_proposition_is_flagged(tmp_path):
    root = write_registry(
        tmp_path,
        [
            {"workstream_id": "W01", "access_summary": "OPEN"},
            {"workstream_id": "W02", "access_summary": "RESTRICTED_TRE"},
        ],
        [
            hypothesis(proposition_id="P1", model_family="FAMILY_A", required_workstreams="W01"),
            hypothesis(proposition_id="P2", model_family="FAMILY_B", required_workstreams="W02"),
        ],
    )
    warnings = assess_feasibility(root).coverage_asymmetry()
    assert any("FAMILY_B" in item for item in warnings)
    assert any("UNEQUAL_BALLOT" in item for item in warnings)


def test_balanced_coverage_raises_no_asymmetry_warning(tmp_path):
    root = write_registry(
        tmp_path,
        [{"workstream_id": "W01", "access_summary": "OPEN"}],
        [
            hypothesis(proposition_id="P1", model_family="FAMILY_A"),
            hypothesis(proposition_id="P2", model_family="FAMILY_B"),
        ],
    )
    assert assess_feasibility(root).coverage_asymmetry() == []


# ------------------------------------------------------- the real registry


@pytest.mark.skipif(not REGISTRIES.exists(), reason="registries absent")
def test_real_registry_asymmetry_is_detected():
    """The live registry must not silently present an unequal ballot as a contest."""

    census = assess_feasibility(REGISTRIES)
    assert len(census.results) == 64
    warnings = census.coverage_asymmetry()
    assert warnings, "an unequal ballot across model families must be flagged"
    assert any("INTRINSIC_RECOGNITION" in item for item in warnings)
