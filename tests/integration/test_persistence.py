from datetime import datetime, timezone

from oslt_research.domain.enums import AccessClass, EpistemicStatus, EvidenceLane, SourceStatus
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.provenance import sha256_text
from oslt_research.persistence.sqlite import SQLiteStore


def test_sqlite_roundtrip_evidence_and_results(tmp_path, result_factory):
    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    content = "content"
    evidence = EvidenceObject(
        evidence_id="EV-1",
        lane=EvidenceLane.SUPPORT,
        source_status=SourceStatus.VERIFIED,
        epistemic_status=EpistemicStatus.OBSERVATION,
        title="Title",
        content=content,
        provenance=ProvenanceRecord(
            source_id="DS033",
            source_uri="https://example.test",
            retrieved_at=datetime.now(timezone.utc),
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        dependency_family="F1",
        metadata={"content_sha256": sha256_text(content)},
        admitted=True,
    )
    store.save_evidence(evidence)
    assert store.list_evidence(admitted_only=True)[0].evidence_id == "EV-1"

    result = result_factory(result_id="KR-1")
    store.save_kernel_result(result)
    assert store.list_kernel_results("RUN-1")[0].result_id == "KR-1"


def test_lane_and_its_coding_survive_a_persistence_round_trip(tmp_path):
    """A lane that does not round-trip is indistinguishable from one never assigned."""

    from oslt_research.connectors.base import HarvestQuery
    from oslt_research.domain.enums import EvidenceLane, LaneCodingMethod
    from oslt_research.pipelines.harvest import raw_record_to_evidence
    from oslt_research.connectors.base import RawRecord

    record = RawRecord(
        source_name="Fixture",
        source_record_id="1",
        title="A Study",
        content="Risk of bias in the included studies",
        source_uri="fixture://1",
        identifiers={"doi": "10.1000/abc"},
        raw_response_hash="a" * 64,
    )
    item = raw_record_to_evidence(record, HarvestQuery(query_id="Q1", concept="c"))
    assert item.lane is EvidenceLane.BIAS_CRITIQUE

    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    store.save_evidence(item)

    (loaded,) = store.list_evidence()
    assert loaded.lane is EvidenceLane.BIAS_CRITIQUE
    assert loaded.lane_coding is not None
    assert loaded.lane_coding.method is LaneCodingMethod.AUTOMATED_CLASSIFIER
    assert loaded.lane_coding.coder_ref == item.lane_coding.coder_ref

    with store.connect() as connection:
        row = connection.execute(
            "SELECT lane FROM evidence_objects WHERE evidence_id = ?", (item.evidence_id,)
        ).fetchone()
    assert row["lane"] == EvidenceLane.BIAS_CRITIQUE.value
