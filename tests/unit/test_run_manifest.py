from __future__ import annotations

from pathlib import Path

import pytest

from oslt_research.connectors.fixture import FixtureConnector
from oslt_research.governance.authority import NOT_PREREGISTERED
from oslt_research.pipelines.run_manifest import (
    CONFIG_FILES,
    build_run_manifest,
    repository_commit,
    working_tree_is_clean,
)


ROOT = Path(__file__).resolve().parents[2]


def manifest(**overrides):
    payload = dict(
        run_id="RUN-1",
        objective="a question",
        proposition_ids=["MD11", "MX14"],
        connectors=[FixtureConnector(records=[])],
        preregistration_ref=NOT_PREREGISTERED,
        root=ROOT,
    )
    payload.update(overrides)
    return build_run_manifest(**payload)


def test_manifest_records_commit_and_config_hashes():
    record = manifest()
    assert record.repository_commit
    assert len(record.repository_commit) == 40 or record.repository_commit.startswith("UNKNOWN")
    assert record.constitution_hash != "MISSING"
    assert len(record.constitution_hash) == 64


def test_every_governing_config_file_is_hashed():
    hashes = manifest().configuration_hashes
    for relative in CONFIG_FILES:
        assert relative in hashes, f"{relative} not hashed into the manifest"
        assert len(hashes[relative]) == 64


def test_connector_versions_are_recorded():
    record = manifest()
    assert record.connector_versions == {
        FixtureConnector.source_name: FixtureConnector.connector_version
    }


def test_environment_captures_interpreter_platform_and_tree_state():
    environment = manifest().environment
    assert environment["python"].startswith("3.")
    assert environment["platform"]
    assert environment["working_tree_clean"] in {"true", "false"}


def test_corpus_hash_is_carried_through():
    record = manifest(corpus_hashes={"corpus_manifest": "a" * 64})
    assert record.data_or_corpus_hashes["corpus_manifest"] == "a" * 64


def test_preregistration_reference_is_required_and_preserved():
    """It used to default to None and no caller ever passed it, so it said nothing.

    A manifest must state either the specification it was testing or, explicitly, that the
    run was not preregistered. Silence about a governance field is the defect, not a state.
    """

    assert manifest().preregistration_ref == NOT_PREREGISTERED
    assert manifest(preregistration_ref="SPEC-1").preregistration_ref == "SPEC-1"

    payload = dict(
        run_id="RUN-1",
        objective="a question",
        proposition_ids=["MD11"],
        connectors=[FixtureConnector(records=[])],
        root=ROOT,
    )
    with pytest.raises(TypeError):
        build_run_manifest(**payload)
    with pytest.raises(ValueError):
        build_run_manifest(**payload, preregistration_ref="")


def test_missing_commit_is_marked_not_blanked(tmp_path):
    """A manifest claiming no commit must look wrong, not empty."""

    commit = repository_commit(tmp_path)
    assert commit.startswith("UNKNOWN")
    assert commit != ""


def test_absent_config_directory_marks_constitution_missing(tmp_path):
    record = manifest(root=tmp_path)
    assert record.constitution_hash == "MISSING"
    assert record.configuration_hashes == {}


def test_working_tree_check_is_a_boolean_not_an_exception(tmp_path):
    assert working_tree_is_clean(tmp_path) in {True, False}


def test_model_gateway_defaults_to_disabled():
    assert manifest().model_gateway == "DISABLED"
