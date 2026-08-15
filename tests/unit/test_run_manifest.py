from __future__ import annotations

from pathlib import Path

import pytest

from oslt_research.connectors.fixture import FixtureConnector
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


def test_preregistration_reference_is_optional_but_preserved():
    assert manifest().preregistration_ref is None
    assert manifest(preregistration_ref="SPEC-1").preregistration_ref == "SPEC-1"


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
