"""Read-only wiring audit: does each governance component's effect exist in the store?

A component can be correct, unit-tested, and completely absent from the corpus. Three
defects of exactly that shape were found on 2026-08-15/16 (`save_run`, the lane
classifier, the study-family resolver), and in every case the persisted field held a
plausible default so nothing failed loudly.

This script does not read the code. It reads the database and re-runs each governance
component over what it finds, then reports where the stored value and the component's
own verdict disagree, and where a whole field sits at its default.

Read-only: opens SQLite with `mode=ro` and writes nothing.

    python scripts/audit_wiring.py
"""

from __future__ import annotations

import collections
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from oslt_research.evidence.lane_coding import LaneClassifier  # noqa: E402
from oslt_research.evidence.provenance import assess_evidence_admission  # noqa: E402
from oslt_research.governance.human_review import (  # noqa: E402
    kernel_review_decision,
    synthesis_review_decision,
)
from oslt_research.kernels.academic_knowledge import (  # noqa: E402
    AcademicKnowledgeProductionKernel,
)
from oslt_research.ontology.admission import (  # noqa: E402
    assess_entity_admission,
    assess_relation_admission,
)
from oslt_research.persistence.sqlite import SQLiteStore  # noqa: E402
from oslt_research.settings import database_path  # noqa: E402


def _readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _section(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> int:
    path = database_path()
    if not path.exists():
        print(f"no store at {path}")
        return 1

    store = SQLiteStore(path)
    connection = _readonly(path)

    _section("Table counts")
    counts = {}
    for (name,) in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ):
        counts[name] = connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  {name:28} {counts[name]}")

    evidence = store.list_evidence()
    entities = store.list_entities()
    relations = store.list_relations()

    _section("Evidence governance fields (default value = suspect)")
    for field in ("lane", "source_status", "epistemic_status"):
        tally = collections.Counter(getattr(item, field).value for item in evidence)
        print(f"  {field:22} {dict(tally)}")
    print(f"  lane_coding present    {sum(1 for i in evidence if i.lane_coding)}/{len(evidence)}")
    print(
        "  lane_coding method     "
        + str(
            dict(
                collections.Counter(
                    i.lane_coding.method.value for i in evidence if i.lane_coding
                )
            )
        )
    )
    print(
        "  access_class           "
        + str(dict(collections.Counter(i.provenance.access_class.value for i in evidence)))
    )
    print(
        "  dependency_family pfx  "
        + str(dict(collections.Counter(i.dependency_family.split(":")[0] for i in evidence)))
    )
    naive = sum(1 for i in evidence if i.dependency_family == i.metadata.get("dedup_key"))
    print(f"  family == naive key    {naive}/{len(evidence)}  (high = resolver never ran)")
    for key in ("orientation", "record_kind", "bias_signature", "registration_id"):
        present = sum(1 for i in evidence if i.metadata.get(key) is not None)
        print(f"  metadata[{key!r}] present  {present}/{len(evidence)}")

    _section("Do the admission gates reproduce the stored verdicts?")
    mismatched = [
        i.evidence_id for i in evidence if assess_evidence_admission(i).admitted != i.admitted
    ]
    print(f"  evidence  mismatches   {len(mismatched)}")
    print(
        "  entity    would-reject  "
        f"{sum(1 for e in entities if not assess_entity_admission(e).admitted)}/{len(entities)}"
    )
    print(
        "  relation  would-reject  "
        f"{sum(1 for r in relations if not assess_relation_admission(r).admitted)}/{len(relations)}"
    )

    _section("Does the lane classifier reproduce the stored lanes?")
    classifier = LaneClassifier()
    diffs = [
        (i.evidence_id, i.lane.value, classifier.classify(i).lane.value)
        for i in evidence
        if classifier.classify(i).lane is not i.lane
    ]
    print(f"  mismatches             {len(diffs)}/{len(evidence)}")
    for row in diffs[:5]:
        print(f"    {row}")

    _section("Run manifests vs the runs that reference them")
    run_ids = {
        row["run_id"]
        for row in connection.execute("SELECT DISTINCT run_id FROM kernel_results")
    } | {
        row["run_id"]
        for row in connection.execute("SELECT DISTINCT run_id FROM synthesis_outcomes")
    }
    for run_id in sorted(run_ids):
        print(f"  {run_id}: manifest={'YES' if store.get_run(run_id) else 'MISSING'}")
    if not run_ids:
        print("  (no runs)")

    _section("Governance verdicts the store never recorded")
    for run_id in sorted(run_ids):
        for result in store.list_kernel_results(run_id):
            decision = kernel_review_decision(result)
            print(
                f"  KernelResult {result.result_id}: governance.human_review says "
                f"required={decision.required} {decision.reasons} "
                "(KernelResult has no field to hold this)"
            )
    for row in connection.execute("SELECT payload_json FROM synthesis_outcomes"):
        outcome = store.get_synthesis(json.loads(row["payload_json"])["synthesis_id"])
        decision = synthesis_review_decision(outcome)
        print(
            f"  Synthesis {outcome.synthesis_id}: stored human_review_required="
            f"{outcome.human_review_required}, governance.human_review says "
            f"required={decision.required} {decision.reasons}"
        )

    _section("The denominator that gates the pilot's claim tier")
    metrics = AcademicKnowledgeProductionKernel.metrics(evidence)
    print(f"  registrations                    {metrics.registrations}")
    print(f"  orientation_counts               {metrics.orientation_counts}")
    print(f"  publication_rates_by_orientation {metrics.publication_rates_by_orientation}")
    print(f"  denominator_available            {metrics.denominator_available}")
    results = AcademicKnowledgeProductionKernel().analyse(
        run_id="AUDIT-DRY-RUN", evidence=evidence, period="AUDIT"
    )
    for result in results:
        print(
            f"  {result.result_id}: {result.finding_direction.value} "
            f"{result.claim_tier.value} falsifier={result.falsifier_status.value}"
        )

    connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
