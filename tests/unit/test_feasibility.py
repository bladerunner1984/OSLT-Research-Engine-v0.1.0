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


# ------------------------------------------------- predictor availability (v2 fix 2)
#
# A proposition whose prediction names a predictor no required workstream carries is not
# testable, however open its workstreams are. This is a SECOND necessary condition on top
# of access; it never relabels access, which stays derived from human-written tokens.


def write_predictor_registry(root: Path, workstreams: list[dict], hypotheses: list[dict]) -> Path:
    """Like ``write_registry`` but carrying the two columns the check actually reads."""

    root.mkdir(parents=True, exist_ok=True)
    for name, rows, fields in (
        (
            "workstreams.csv",
            workstreams,
            ["workstream_id", "workstream", "data_to_accumulate", "access_summary"],
        ),
        (
            "hypotheses.csv",
            hypotheses,
            [
                "proposition_id",
                "model_family",
                "domain",
                "prediction",
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


OPEN_NO_AWARENESS = {
    "workstream_id": "W01",
    "workstream": "Population denominators",
    "data_to_accumulate": "Population size, age, sex, geography, time trends",
    "access_summary": "OPEN_AGGREGATE",
}
OPEN_WITH_AWARENESS = {
    "workstream_id": "W11",
    "workstream": "Media and public discourse",
    "data_to_accumulate": "News corpora, web archives, GDELT, framing data over time",
    "access_summary": "OPEN_ARCHIVE",
}


def test_named_predictor_absent_from_required_set_is_not_open_testable(tmp_path):
    root = write_predictor_registry(
        tmp_path,
        [OPEN_NO_AWARENESS, OPEN_WITH_AWARENESS],
        [
            hypothesis(
                prediction="Search/media/clinical awareness predicts presentation.",
                required_workstreams="W01",
            )
        ],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.NEEDS_PREDICTOR_SOURCE
    assert result.missing_predictors == ["AWARENESS_OR_MEDIA_ATTENTION"]
    assert not result.testable_now
    assert "does not hold" in result.reason


def test_requiring_the_workstream_that_carries_the_predictor_restores_testability(tmp_path):
    root = write_predictor_registry(
        tmp_path,
        [OPEN_NO_AWARENESS, OPEN_WITH_AWARENESS],
        [
            hypothesis(
                prediction="Search/media/clinical awareness predicts presentation.",
                required_workstreams="W01;W11",
            )
        ],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.OPEN_TESTABLE
    assert result.missing_predictors == []


def test_a_prediction_naming_no_lexicon_predictor_is_never_blocked_by_this_check(tmp_path):
    """Unknown is not absent. The check removes false testability, not real testability."""

    root = write_predictor_registry(
        tmp_path,
        [OPEN_NO_AWARENESS],
        [hypothesis(prediction="Age/sex standardisation attenuates raw growth.")],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.OPEN_TESTABLE


def test_access_still_takes_precedence_over_a_missing_predictor(tmp_path):
    """This check ADDS a condition; it must never relabel an access block."""

    root = write_predictor_registry(
        tmp_path,
        [{**OPEN_NO_AWARENESS, "access_summary": "RESTRICTED_TRE"}],
        [hypothesis(prediction="Search/media awareness predicts presentation.")],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.NEEDS_RESTRICTED_ACCESS


def test_registry_without_the_data_column_is_not_read_as_full_of_holes(tmp_path):
    """An unpopulated column is missing evidence, not evidence of missing data."""

    root = write_registry(
        tmp_path,
        [{"workstream_id": "W01", "access_summary": "OPEN"}],
        [hypothesis()],
    )
    [result] = assess_feasibility(root).results
    assert result.reachability is Reachability.OPEN_TESTABLE


@pytest.mark.skipif(not REGISTRIES.exists(), reason="registries absent")
def test_real_registry_loses_exactly_the_six_propositions_with_no_predictor():
    """The six the 2026-08-16 findings run had to record as untestable after the fact."""

    census = assess_feasibility(REGISTRIES)
    blocked = {
        item.proposition_id
        for item in census.results
        if item.reachability is Reachability.NEEDS_PREDICTOR_SOURCE
    }
    assert blocked == {"AS04", "AS05", "AS07", "AS12", "TH05", "TH08"}
    assert len(census.testable_now()) == 10
    # Fewer, but every one of them can actually be run.
    assert census.counts()["OPEN_TESTABLE"] == 10


@pytest.mark.skipif(not REGISTRIES.exists(), reason="registries absent")
def test_removing_six_propositions_does_not_remove_the_unequal_ballot_warning():
    warnings = assess_feasibility(REGISTRIES).coverage_asymmetry()
    assert any("INTRINSIC_RECOGNITION" in item for item in warnings)
    assert any("OPEN_TESTABLE_SET_DOMINATED_BY:ASCERTAINMENT_SERVICE" in item for item in warnings)
