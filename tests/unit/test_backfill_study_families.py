"""Tests for the corpus-wide study-family backfill.

The defect these guard against is subtle: the field was populated (with the DOI), so it
looked like data, not wiring. The assertions therefore check that a family key can never
again be mistaken for a record identifier, and that re-running writes nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

from oslt_research.domain.enums import AccessClass
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.persistence.sqlite import SQLiteStore

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from backfill_study_families import backfill  # noqa: E402


def evidence(
    evidence_id: str,
    *,
    title: str = "A study",
    content: str = "",
    doi: str | None = None,
    authors: list[str] | None = None,
    dependency_family: str | None = None,
) -> EvidenceObject:
    return EvidenceObject(
        evidence_id=evidence_id,
        title=title,
        content=content,
        provenance=ProvenanceRecord(
            source_id="SRC",
            source_uri=f"https://example.org/{evidence_id}",
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        dependency_family=dependency_family or f"doi:{doi or evidence_id.lower()}",
        metadata={"authors": authors or []},
    )


def make_store(tmp_path, items) -> SQLiteStore:
    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    store.save_evidence_many(items)
    return store


def test_dry_run_writes_nothing(tmp_path):
    store = make_store(
        tmp_path,
        [
            evidence("EV1", content="Registered as NCT01234567."),
            evidence("EV2", content="Follow-up of NCT01234567."),
        ],
    )
    report = backfill(store, apply_changes=False)

    assert report["changed"] == 2
    for stored in store.list_evidence():
        assert stored.dependency_family.startswith("doi:")


def test_apply_collapses_a_shared_trial_and_records_the_basis(tmp_path):
    store = make_store(
        tmp_path,
        [
            evidence("EV1", content="Registered as NCT01234567."),
            evidence("EV2", content="Follow-up of NCT01234567."),
            evidence("EV3", content="Something unrelated entirely."),
        ],
    )
    report = backfill(store, apply_changes=True)

    assert report["families_before"] == 3
    assert report["families_after"] == 2
    assert report["multi_member_families"] == 1

    by_id = {item.evidence_id: item for item in store.list_evidence()}
    assert by_id["EV1"].dependency_family == by_id["EV2"].dependency_family
    assert by_id["EV1"].dependency_family != by_id["EV3"].dependency_family
    assert by_id["EV1"].metadata["dependency_family_basis"] == ["SHARED_TRIAL_REGISTRATION"]
    assert by_id["EV3"].metadata["dependency_family_basis"] == ["SINGLETON_NO_SIGNAL"]


def test_a_singleton_family_is_visibly_a_family_not_a_doi(tmp_path):
    """The whole bug was that a family key was indistinguishable from a dedup key."""

    store = make_store(tmp_path, [evidence("EV1", doi="10.1/abc")])
    backfill(store, apply_changes=True)

    (stored,) = store.list_evidence()
    assert stored.dependency_family.startswith("family:")
    assert "10.1/abc" not in stored.dependency_family
    # The naive key is preserved so a later corpus-wide pass can still merge on it.
    assert stored.metadata["dedup_key"] == "doi:10.1/abc"
    assert stored.metadata["dependency_family_size"] == 1


def test_rerunning_the_backfill_changes_nothing(tmp_path):
    store = make_store(
        tmp_path,
        [
            evidence("EV1", content="Registered as NCT01234567."),
            evidence("EV2", content="Follow-up of NCT01234567."),
            evidence("EV3", doi="10.1/abc"),
            evidence("EV4", doi="10.1/abc"),
        ],
    )
    backfill(store, apply_changes=True)
    second = backfill(store, apply_changes=True)
    assert second["changed"] == 0
    third = backfill(store, apply_changes=True)
    assert third["changed"] == 0


def test_cross_run_dedup_key_still_merges_after_a_first_pass(tmp_path):
    """Two records sharing a DOI must still merge once the field holds a family key."""

    store = make_store(tmp_path, [evidence("EV1", doi="10.1/abc")])
    backfill(store, apply_changes=True)
    store.save_evidence_many([evidence("EV2", doi="10.1/abc")])

    report = backfill(store, apply_changes=True)
    assert report["families_after"] == 1
    families = {item.dependency_family for item in store.list_evidence()}
    assert len(families) == 1


def test_conference_containers_are_not_clustered_together(tmp_path):
    """Container records share a degenerate heuristic key but are not one study."""

    shared = "heuristic:abstract:unknown:2025"
    store = make_store(
        tmp_path,
        [
            evidence(
                "EV1",
                title="Proceedings of the World Molecular Imaging Congress",
                dependency_family=shared,
            ),
            evidence("EV2", title="Oral Presentations", dependency_family=shared),
        ],
    )

    report = backfill(store, apply_changes=True)
    assert report["families_after"] == 2
    for stored in store.list_evidence():
        assert stored.metadata["dependency_family_basis"] == ["CONTAINER_RECORD_NOT_A_STUDY"]
