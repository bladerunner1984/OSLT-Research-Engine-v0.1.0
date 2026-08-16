"""Guards on persisting the feasibility census and the claim-release verdicts.

These test the *wiring*, not the components: the components already had unit tests and were
already correct, and being correct is exactly why nobody noticed they never ran.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from oslt_research.domain.enums import AuthorityLevel, ClaimTier
from oslt_research.governance.authority import NOT_PREREGISTERED
from oslt_research.governance.claim_release import (
    ClaimSubmission,
    assess_documented_claim,
)
from oslt_research.governance.design_requirements import requirements_for_blocked
from oslt_research.governance.feasibility import (
    assess_feasibility,
    connector_source_ids,
    registry_digest,
    workstream_source_coverage,
)
from oslt_research.persistence.sqlite import MissingRunManifestError, SQLiteStore
from oslt_research.pipelines.run_manifest import build_run_manifest


REGISTRIES = Path(__file__).resolve().parents[2] / "registries"


def sealed_store(tmp_path, run_id: str = "RUN-TEST") -> SQLiteStore:
    store = SQLiteStore(tmp_path / "test.db")
    store.initialise()
    store.save_run(
        build_run_manifest(
            run_id=run_id,
            objective="test",
            proposition_ids=["P1"],
            connectors=[],
            preregistration_ref=NOT_PREREGISTERED,
        ),
        authority=AuthorityLevel.A3_VERIFIED_EVIDENCE_COMPUTATION,
    )
    return store


# ------------------------------------------------------------------ census persistence


def test_census_write_requires_a_sealed_run_manifest(tmp_path):
    """A census that cannot be traced to a run is not reproducible, so refuse the write."""

    store = SQLiteStore(tmp_path / "test.db")
    store.initialise()
    census = assess_feasibility(REGISTRIES)
    with pytest.raises(MissingRunManifestError):
        store.save_feasibility_census(
            census_id="FC-1",
            run_id="RUN-NOT-SEALED",
            assessed_at="2026-08-16T00:00:00+00:00",
            registry_digest=registry_digest(REGISTRIES),
            summary=census.summary(),
            results=census.results,
        )


def test_census_write_refuses_an_empty_registry_digest(tmp_path):
    store = sealed_store(tmp_path)
    census = assess_feasibility(REGISTRIES)
    with pytest.raises(ValueError, match="REGISTRY_DIGEST_REQUIRED"):
        store.save_feasibility_census(
            census_id="FC-1",
            run_id="RUN-TEST",
            assessed_at="2026-08-16T00:00:00+00:00",
            registry_digest={},
            summary=census.summary(),
            results=census.results,
        )


def test_persisted_census_round_trips_and_reproduces_from_the_registry(tmp_path):
    store = sealed_store(tmp_path)
    census = assess_feasibility(REGISTRIES)
    digest = registry_digest(REGISTRIES)
    store.save_feasibility_census(
        census_id="FC-1",
        run_id="RUN-TEST",
        assessed_at="2026-08-16T00:00:00+00:00",
        registry_digest=digest,
        summary=census.summary(),
        results=census.results,
        requirements=requirements_for_blocked(census.results)[:3],
    )

    stored = store.get_feasibility_census("FC-1")
    assert stored is not None
    assert stored["registry_digest"] == digest
    assert stored["summary"]["by_reachability"] == census.counts()
    assert len(stored["results"]) == len(census.results)
    assert store.latest_feasibility_census_id() == "FC-1"


def test_design_requirements_persist_as_simulation_only(tmp_path):
    """Priced designs are simulation, and the stored row must say so on its own.

    A design cost sitting in a table next to real results is one copy-paste away from being
    read as a finding. The tier lives in a column, not only inside the payload blob.
    """

    store = sealed_store(tmp_path)
    census = assess_feasibility(REGISTRIES)
    requirements = requirements_for_blocked(census.results)[:2]
    store.save_feasibility_census(
        census_id="FC-1",
        run_id="RUN-TEST",
        assessed_at="2026-08-16T00:00:00+00:00",
        registry_digest=registry_digest(REGISTRIES),
        summary=census.summary(),
        results=census.results,
        requirements=requirements,
    )
    with store.transaction() as connection:
        rows = connection.execute(
            "SELECT claim_tier, epistemic_status FROM design_requirements"
        ).fetchall()
    assert rows
    assert {row["claim_tier"] for row in rows} == {"SIMULATION_ONLY"}
    assert {row["epistemic_status"] for row in rows} == {"SIMULATION"}


# ------------------------------------------------------------- connector inventory overlay


def test_connector_inventory_separates_declared_from_unknown():
    """Modules that declare no SOURCE_ID are UNKNOWN, never counted as declaring nothing."""

    declared, undeclared = connector_source_ids()
    assert declared
    assert undeclared
    assert not set(declared) & set(undeclared)


def test_coverage_overlay_does_not_change_reachability():
    """The overlay is diagnostic. If it ever fed back into the census it would conflate an
    engineering gap with an access gap, and the census is quoted as an access statement."""

    declared, _ = connector_source_ids()
    before = assess_feasibility(REGISTRIES).counts()
    workstream_source_coverage(
        REGISTRIES, connector_ids=set(declared.values()), store_source_ids=set()
    )
    assert assess_feasibility(REGISTRIES).counts() == before


# --------------------------------------------------------------- claim release wiring


def submission(**overrides) -> ClaimSubmission:
    payload = {
        "claim_ref": "C1",
        "source_document": "docs/EXAMPLE.md",
        "wording": "the records show a rise",
        "declared_tier": ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
        "tier_source": "test",
    }
    payload.update(overrides)
    return ClaimSubmission(**payload)  # type: ignore[arg-type]


def test_undeclared_tier_is_refused_and_never_defaulted():
    assessment = assess_documented_claim(submission(declared_tier=None))
    assert not assessment.released
    assert "CLAIM_TIER_NOT_DECLARED" in assessment.failures
    assert assessment.declared_tier is None
    assert assessment.wording_check is None


def test_advisory_scan_is_reported_separately_from_a_verdict():
    """An advisory scan on an undeclared claim must never look like a passed check."""

    assessment = assess_documented_claim(
        submission(declared_tier=None, wording="this proves the effect of policy"),
        advisory_tier=ClaimTier.DESCRIPTIVE_EVIDENCE_ONLY,
    )
    assert not assessment.released
    assert assessment.wording_check is None
    assert "proves" in assessment.advisory_prohibited_hits
    assert assessment.as_record()["prohibited_hits"] == []


def test_documented_claim_without_a_result_is_refused_not_synthesised():
    assessment = assess_documented_claim(submission())
    assert not assessment.released
    assert "NO_PERSISTED_RESULT_FOR_CLAIM" in assessment.failures


def test_wording_over_tier_fails_even_when_everything_else_is_absent():
    assessment = assess_documented_claim(
        submission(wording="the intended and documented effect of guideline revisions")
    )
    assert any(failure.startswith("WORDING_EXCEEDS_CLAIM_TIER") for failure in assessment.failures)
    assert assessment.wording_check is not None
    assert "effect of" in assessment.wording_check.prohibited_hits


def test_claim_assessment_write_requires_a_sealed_run_manifest(tmp_path):
    store = SQLiteStore(tmp_path / "test.db")
    store.initialise()
    assessment = assess_documented_claim(submission())
    with pytest.raises(MissingRunManifestError):
        store.save_claim_assessment(
            assessment, run_id="RUN-NOT-SEALED", assessed_at="2026-08-16T00:00:00+00:00"
        )


def test_refusals_are_persisted_with_an_undeclared_tier_stored_as_null(tmp_path):
    store = sealed_store(tmp_path)
    store.save_claim_assessment(
        assess_documented_claim(submission(declared_tier=None)),
        run_id="RUN-TEST",
        assessed_at="2026-08-16T00:00:00+00:00",
    )
    with store.transaction() as connection:
        row = connection.execute(
            "SELECT declared_tier, released FROM claim_release_assessments"
        ).fetchone()
    assert row["declared_tier"] is None
    assert row["released"] == 0
    assert store.list_claim_assessments("RUN-TEST")[0]["declared_tier"] is None
