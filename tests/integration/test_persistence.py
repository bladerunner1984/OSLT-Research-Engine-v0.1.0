from datetime import datetime, timezone

import pytest

from oslt_research.domain.enums import AccessClass, EpistemicStatus, EvidenceLane, SourceStatus
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.provenance import sha256_text
from oslt_research.connectors.fixture import FixtureConnector
from oslt_research.domain.enums import AuthorityLevel
from oslt_research.governance.authority import (
    NOT_PREREGISTERED,
    AuthorityError,
    AuthorityPatch,
)
from oslt_research.persistence.sqlite import MissingRunManifestError, SQLiteStore
from oslt_research.pipelines.run_manifest import build_run_manifest
from oslt_research.pipelines.synthesis import MasterSynthesisKernel


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
    seal(store, "RUN-1")
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


# ------------------------------------------------- manifest as a persistence precondition


def seal(store: SQLiteStore, run_id: str, **overrides) -> None:
    """Seal a minimal run manifest so results for `run_id` may be persisted."""

    manifest = build_run_manifest(
        run_id=run_id,
        objective="a question",
        proposition_ids=["MD11"],
        connectors=[FixtureConnector(records=[])],
        preregistration_ref=overrides.pop("preregistration_ref", NOT_PREREGISTERED),
    )
    store.save_run(
        manifest,
        authority=overrides.pop("authority", AuthorityLevel.A3_VERIFIED_EVIDENCE_COMPUTATION),
        **overrides,
    )


def test_kernel_result_without_a_manifest_is_refused(tmp_path, result_factory):
    """The defect this reproduces: 2 kernel results naming a run with 0 manifests.

    Sealing used to be a parallel step in one pipeline. Every other caller forgot it and
    nothing complained, so the store held results nobody could trace to a run.
    """

    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    with pytest.raises(MissingRunManifestError):
        store.save_kernel_result(result_factory(result_id="KR-1"))
    assert store.list_kernel_results("RUN-1") == []


def test_synthesis_without_a_manifest_is_refused(tmp_path, result_factory):
    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    seal(store, "RUN-1")
    store.save_kernel_result(result_factory(result_id="KR-1"))
    outcome = MasterSynthesisKernel().synthesise(
        run_id="RUN-1", results=store.list_kernel_results("RUN-1")
    )
    store.save_synthesis(outcome)
    assert store.get_synthesis(outcome.synthesis_id) is not None

    orphan = outcome.model_copy(update={"run_id": "RUN-UNSEALED", "synthesis_id": "SYN-X"})
    with pytest.raises(MissingRunManifestError):
        store.save_synthesis(orphan)


# ------------------------------------------------------------------- authority lattice


def test_sealing_a_run_records_its_authority(tmp_path):
    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    seal(store, "RUN-1")
    record = store.get_authority("RUN-1", "RUN_MANIFEST")
    assert record is not None
    assert record.authority is AuthorityLevel.A3_VERIFIED_EVIDENCE_COMPUTATION
    assert record.value["preregistration_ref"] == NOT_PREREGISTERED


def test_binding_a_run_to_a_preregistration_needs_human_authorisation(tmp_path):
    """PREREGISTERED_SPECIFICATION is protected: a pipeline cannot self-declare confirmatory."""

    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    with pytest.raises(AuthorityError):
        seal(store, "RUN-1", preregistration_ref="OSLT-P1-ACADEMIC-KNOWLEDGE-V1")
    assert store.get_run("RUN-1") is None
    assert store.get_authority("RUN-1", "PREREGISTERED_SPECIFICATION") is None

    seal(
        store,
        "RUN-1",
        preregistration_ref="OSLT-P1-ACADEMIC-KNOWLEDGE-V1",
        explicit_human_authorisation=True,
    )
    manifest = store.get_run("RUN-1")
    assert manifest.preregistration_ref == "OSLT-P1-ACADEMIC-KNOWLEDGE-V1"


def test_lower_authority_cannot_overwrite_a_sealed_run(tmp_path):
    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    seal(store, "RUN-1", authority=AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION)
    with pytest.raises(AuthorityError):
        seal(store, "RUN-1", authority=AuthorityLevel.A5_MODEL_PROPOSAL)
    assert (
        store.get_authority("RUN-1", "RUN_MANIFEST").authority
        is AuthorityLevel.A2_HUMAN_GOVERNANCE_DECISION
    )


def test_authority_ledger_refuses_a_downgrade_of_an_existing_claim(tmp_path):
    """A6 raw history must not be able to restate what an A3 computation sealed."""

    store = SQLiteStore(tmp_path / "oslt.db")
    store.initialise()
    seal(store, "RUN-1")
    with pytest.raises(AuthorityError):
        store.apply_authority(
            AuthorityPatch(
                object_id="RUN-1",
                object_type="RUN_MANIFEST",
                proposer_authority=AuthorityLevel.A6_RAW_HISTORY,
                value={},
            )
        )
    assert store.get_authority("RUN-1", "RUN_MANIFEST").value["preregistration_ref"] == (
        NOT_PREREGISTERED
    )
