"""Standing check: every governance field on the persisted corpus must be non-default.

The failure mode this file exists to catch is not "a component is wrong". Every
component here is correct and unit-tested. The failure mode is that the component is
never invoked on the corpus path, and the persisted field holds a plausible default
instead - so the store looks healthy, no exception is raised, and the unit suite stays
green while the corpus is governance-blind.

Three defects of exactly this shape were found on 2026-08-15/16: `save_run` was never
called, `LaneClassifier` was never called by `harvest`, and `StudyFamilyResolver` was
never called by `execute_harvest`. Each was invisible until somebody queried the store
against the code.

These tests therefore assert against the LIVE store rather than a fixture. A fixture
proves the component works; only the store proves it ran. Tests skip when no corpus is
present (fresh clone, CI) - a skip is honest, a green pass on an empty database is not.

The `xfail(strict=True)` cases are open defects recorded by docs/WIRING_AUDIT.md. They
are strict so that fixing the wiring turns them red and forces the marker to be removed,
rather than letting a fixed defect quietly stay marked as expected.
"""

from __future__ import annotations

import collections

import pytest

from oslt_research.evidence.lane_coding import LaneClassifier
from oslt_research.evidence.provenance import assess_evidence_admission
from oslt_research.governance.authority import NOT_PREREGISTERED
from oslt_research.governance.human_review import synthesis_review_decision
from oslt_research.ontology.admission import assess_entity_admission, assess_relation_admission
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.settings import database_path


MINIMUM_CORPUS = 100


@pytest.fixture(scope="module")
def store() -> SQLiteStore:
    path = database_path()
    if not path.exists():
        pytest.skip(f"no persisted corpus at {path}")
    return SQLiteStore(path)


@pytest.fixture(scope="module")
def evidence(store: SQLiteStore):
    items = store.list_evidence()
    if len(items) < MINIMUM_CORPUS:
        pytest.skip(f"corpus too small to audit ({len(items)} records)")
    return items


# --------------------------------------------------------------------- effective wiring


def test_every_record_carries_lane_coding_provenance(evidence) -> None:
    """A lane with no coder attached is not a code - it is a default that looks like one."""

    uncoded = [item.evidence_id for item in evidence if item.lane_coding is None]
    assert not uncoded, f"{len(uncoded)} records carry a lane with no LaneCoding provenance"


def test_stored_lanes_reproduce_from_the_classifier(evidence) -> None:
    """The stored lane must be the lane the current classifier assigns.

    Records coded SOURCE_DECLARED are exempt: a retraction notice is a source fact the
    text classifier cannot see, and its precedence over the classifier is intended.
    """

    classifier = LaneClassifier()
    drifted = [
        item.evidence_id
        for item in evidence
        if item.lane_coding is not None
        and item.lane_coding.method.value == "AUTOMATED_CLASSIFIER"
        and classifier.classify(item).lane is not item.lane
    ]
    assert not drifted, f"{len(drifted)} automated lane codes disagree with the classifier"


def test_dependency_families_are_resolved_not_naive_dedup_keys(evidence) -> None:
    """`dependency_family` must be a resolved study family, not the identifier it started as.

    This is defect 3 from the audit, inverted into a guard. Equality with `dedup_key` is
    the exact signature of a corpus where StudyFamilyResolver never ran.
    """

    naive = [
        item.evidence_id
        for item in evidence
        if item.metadata.get("dedup_key")
        and item.dependency_family == item.metadata["dedup_key"]
    ]
    ratio = len(naive) / len(evidence)
    assert ratio < 0.10, (
        f"{len(naive)}/{len(evidence)} dependency families are still naive dedup keys"
    )


def test_evidence_admission_gate_reproduces_the_stored_verdict(evidence) -> None:
    mismatched = [
        item.evidence_id
        for item in evidence
        if assess_evidence_admission(item).admitted != item.admitted
    ]
    assert not mismatched, f"{len(mismatched)} admission verdicts do not reproduce"


def test_ontology_admission_gates_reproduce_the_stored_verdicts(store: SQLiteStore) -> None:
    entities = store.list_entities()
    relations = store.list_relations()
    if not entities and not relations:
        pytest.skip("no ontology in the store")
    bad_entities = [
        entity.entity_id
        for entity in entities
        if assess_entity_admission(entity).admitted != entity.admitted
    ]
    bad_relations = [
        relation.relation_id
        for relation in relations
        if assess_relation_admission(relation).admitted != relation.admitted
    ]
    assert not bad_entities and not bad_relations


def test_persisted_manifests_state_a_preregistration_and_an_authority(
    store: SQLiteStore,
) -> None:
    """Every sealed manifest must name its specification and the authority that sealed it.

    `preregistration_ref` was a parameter no caller ever passed, and no persisted object
    carried an authority level at all. Both are now required at the write, so a manifest in
    the store that lacks either came from a path that bypassed the store's own gate.
    """

    with store.connect() as connection:
        run_ids = [row[0] for row in connection.execute("SELECT run_id FROM run_manifests")]
    if not run_ids:
        pytest.skip("no run manifests in the store")
    silent = []
    unauthorised = []
    for run_id in run_ids:
        manifest = store.get_run(run_id)
        if not manifest.preregistration_ref:
            silent.append(run_id)
        protected = manifest.preregistration_ref not in (None, NOT_PREREGISTERED)
        object_type = "PREREGISTERED_SPECIFICATION" if protected else "RUN_MANIFEST"
        if store.get_authority(run_id, object_type) is None:
            unauthorised.append(run_id)
    assert not silent, f"manifests saying nothing about preregistration: {silent}"
    assert not unauthorised, f"manifests sealed with no recorded authority: {unauthorised}"


# ------------------------------------------------------------------------ open defects


@pytest.mark.xfail(
    strict=True,
    reason=(
        "WIRING AUDIT: no RunManifest is persisted for any run in the store. "
        "`save_run` is called only by pipelines/pilot1.py, which is not the corpus path; "
        "the corpus path (kernel_harvest.harvest_for_kernels -> execute_harvest) builds "
        "no manifest and has no production caller at all. Every persisted KernelResult "
        "and SynthesisOutcome therefore names a run that cannot be reproduced. "
        "See docs/WIRING_AUDIT.md."
    ),
)
def test_every_persisted_run_has_a_manifest(store: SQLiteStore) -> None:
    with store.connect() as connection:
        run_ids = {
            row[0] for row in connection.execute("SELECT DISTINCT run_id FROM kernel_results")
        } | {
            row[0]
            for row in connection.execute("SELECT DISTINCT run_id FROM synthesis_outcomes")
        }
    if not run_ids:
        pytest.skip("no runs in the store")
    missing = sorted(run_id for run_id in run_ids if store.get_run(run_id) is None)
    assert not missing, f"runs with no RunManifest: {missing}"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "WIRING AUDIT: governance/human_review.py has no production consumer. "
        "pipelines/synthesis.py reimplements a narrower rule inline, so the persisted "
        "SynthesisOutcome records human_review_required=False for an outcome the "
        "governance module says requires review. See docs/WIRING_AUDIT.md."
    ),
)
def test_stored_human_review_flag_agrees_with_the_governance_module(
    store: SQLiteStore,
) -> None:
    with store.connect() as connection:
        ids = [
            row[0] for row in connection.execute("SELECT synthesis_id FROM synthesis_outcomes")
        ]
    if not ids:
        pytest.skip("no synthesis outcomes in the store")
    disagreements = []
    for synthesis_id in ids:
        outcome = store.get_synthesis(synthesis_id)
        expected = synthesis_review_decision(outcome).required
        if outcome.human_review_required != expected:
            disagreements.append((synthesis_id, outcome.human_review_required, expected))
    assert not disagreements, f"stored flag disagrees with governance: {disagreements}"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "WIRING AUDIT: nothing assigns metadata['orientation'], so every admitted record "
        "falls into the NOT_ASSESSABLE bucket via the .get() default. That single bucket "
        "is nonetheless large enough to satisfy AcademicCorpusMetrics.denominator_available, "
        "which promotes the pilot's kernel results from DESCRIPTIVE_EVIDENCE_ONLY to "
        "ASSOCIATION_ONLY and produces a PARTIALLY_TRIGGERED falsifier for MD11 from a "
        "comparison with nothing to compare. See docs/WIRING_AUDIT.md."
    ),
)
def test_orientation_coding_is_populated_for_the_denominator(evidence) -> None:
    coded = [
        item
        for item in evidence
        if item.admitted and item.metadata.get("orientation") not in (None, "NOT_ASSESSABLE")
    ]
    tally = collections.Counter(
        str(item.metadata.get("orientation", "NOT_ASSESSABLE"))
        for item in evidence
        if item.admitted
    )
    assert coded, (
        "no admitted record carries an orientation code; the publication-rate "
        f"denominator is a single degenerate bucket: {dict(tally)}"
    )
