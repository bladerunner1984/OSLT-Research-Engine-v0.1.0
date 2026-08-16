from __future__ import annotations

import sys
from pathlib import Path

from oslt_research.domain.enums import AccessClass, EvidenceLane, LaneCodingMethod
from oslt_research.domain.models import EvidenceObject, LaneCoding, ProvenanceRecord
from oslt_research.persistence.sqlite import SQLiteStore

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from backfill_lane_coding import backfill  # noqa: E402


def evidence(evidence_id: str, content: str) -> EvidenceObject:
    return EvidenceObject(
        evidence_id=evidence_id,
        title="A study",
        content=content,
        provenance=ProvenanceRecord(
            source_id="SRC",
            source_uri=f"https://example.org/{evidence_id}",
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        dependency_family=f"doi:{evidence_id}",
    )


def make_store(tmp_path, items) -> SQLiteStore:
    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    store.save_evidence_many(items)
    return store


def test_dry_run_writes_nothing(tmp_path):
    store = make_store(tmp_path, [evidence("EV1", "This paper has been retracted")])
    report = backfill(store, apply_changes=False)

    assert report["changed"] == 1
    (stored,) = store.list_evidence()
    assert stored.lane is EvidenceLane.UNCLASSIFIED
    assert stored.lane_coding is None


def test_apply_codes_the_corpus_and_reports_the_distribution(tmp_path):
    store = make_store(
        tmp_path,
        [
            evidence("EV1", "This paper has been retracted"),
            evidence("EV2", "An independent replication"),
            evidence("EV3", "Cohort profile of the sample"),
        ],
    )
    report = backfill(store, apply_changes=True)

    assert report["total"] == 3
    assert report[EvidenceLane.CORRECTION_RETRACTION.value] == 1
    assert report[EvidenceLane.REPLICATION.value] == 1
    assert report[EvidenceLane.UNCLASSIFIED.value] == 1

    by_id = {item.evidence_id: item for item in store.list_evidence()}
    assert by_id["EV1"].lane is EvidenceLane.CORRECTION_RETRACTION
    # Every backfilled code is a proposal, never a verified one.
    for item in by_id.values():
        assert item.lane_coding is not None
        assert item.lane_coding.method is LaneCodingMethod.AUTOMATED_CLASSIFIER
        assert item.lane_coding.requires_human_adjudication is True


def test_backfill_leaves_an_existing_human_code_alone(tmp_path):
    human = evidence("EV1", "This paper has been retracted").model_copy(
        update={
            "lane": EvidenceLane.NULL,
            "lane_coding": LaneCoding(
                method=LaneCodingMethod.HUMAN_CODER,
                confidence=1.0,
                coder_ref="A. Coder",
                requires_human_adjudication=False,
            ),
        }
    )
    store = make_store(tmp_path, [human])
    backfill(store, apply_changes=True)

    (stored,) = store.list_evidence()
    assert stored.lane is EvidenceLane.NULL
    assert stored.lane_coding is not None
    assert stored.lane_coding.method is LaneCodingMethod.HUMAN_CODER


def test_rerunning_the_backfill_changes_nothing(tmp_path):
    store = make_store(tmp_path, [evidence("EV1", "An independent replication")])
    backfill(store, apply_changes=True)
    second = backfill(store, apply_changes=True)
    assert second["changed"] == 0
