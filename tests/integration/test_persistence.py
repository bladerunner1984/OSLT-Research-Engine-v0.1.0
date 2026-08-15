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
