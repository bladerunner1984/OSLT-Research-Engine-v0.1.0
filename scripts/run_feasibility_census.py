"""Run the feasibility census live and persist it, so the quoted figures can be re-derived.

The census numbers (16 OPEN_TESTABLE / 25 NEEDS_PRIMARY_COLLECTION / 16
NEEDS_RESTRICTED_ACCESS / 7 NEEDS_INDIVIDUAL_LEVEL) are quoted in `docs/ACADEMIC_HANDOFF.md`
and were produced by an ad-hoc invocation that persisted nothing. A governance figure that
gates what the project attempts, and that cannot be re-derived from the store, drifts
silently. This script makes it a stored, dated, digest-bound object.

Two things it deliberately does NOT do:

* It does not let the connector inventory change a `Reachability`. The census reads only
  `registries/workstreams.csv` and `registries/hypotheses.csv`; new connectors cannot move a
  proposition, and pretending otherwise would be the most dangerous kind of wrong here. The
  live connector inventory is recorded *alongside* the census as a separate overlay.
* It does not invent a run. Persistence requires a sealed `RunManifest`, exactly as kernel
  results do, so the census carries a commit, a constitution hash and a registry digest.

Usage::

    python scripts/run_feasibility_census.py            # compute and print, write nothing
    python scripts/run_feasibility_census.py --apply    # seal a run and persist
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from oslt_research.governance.authority import NOT_PREREGISTERED
from oslt_research.governance.design_requirements import requirements_for_blocked
from oslt_research.governance.feasibility import (
    assess_feasibility,
    connector_source_ids,
    registry_digest,
    workstream_source_coverage,
)
from oslt_research.domain.enums import AuthorityLevel
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.run_manifest import build_run_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

#: The figures recorded in docs/ACADEMIC_HANDOFF.md, kept here so the script can say
#: whether anything moved rather than leaving the reader to compare by eye.
QUOTED_COUNTS = {
    "OPEN_TESTABLE": 16,
    "NEEDS_PRIMARY_COLLECTION": 25,
    "NEEDS_RESTRICTED_ACCESS": 16,
    "NEEDS_INDIVIDUAL_LEVEL": 7,
}

#: The ballot composition recorded in the same handoff.
QUOTED_TESTABLE_BY_FAMILY = {"ASCERTAINMENT_SERVICE": 12}
QUOTED_FAMILIES_WITH_NONE = (
    "INTRINSIC_RECOGNITION",
    "MIXTURE_HETEROGENEITY",
    "NULL_OR_ALTERNATIVE",
)


def store_source_ids(database: Path) -> set[str]:
    """Which registry source ids actually have evidence in the store.

    Read-only and tolerant of a missing database: a fresh clone has no corpus, and the
    census must still run rather than pretending the corpus is empty when it is absent.
    """

    if not database.exists():
        return set()
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        return {
            row[0]
            for row in connection.execute("SELECT DISTINCT source_id FROM evidence_objects")
        }
    finally:
        connection.close()


def build_report(registry_root: Path, database: Path) -> dict[str, object]:
    census = assess_feasibility(registry_root)
    summary = census.summary()
    declared, undeclared = connector_source_ids()

    counts = dict(summary["by_reachability"])  # type: ignore[arg-type]
    drift = {
        key: {"quoted": value, "now": counts.get(key, 0), "changed": counts.get(key, 0) != value}
        for key, value in QUOTED_COUNTS.items()
    }
    testable_by_family = dict(summary["testable_by_model_family"])  # type: ignore[arg-type]
    families_with_none = [
        family for family in QUOTED_FAMILIES_WITH_NONE if family not in testable_by_family
    ]

    return {
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "registry_digest": registry_digest(registry_root),
        "summary": summary,
        "drift_against_handoff": drift,
        "ballot": {
            "quoted_testable_by_family": QUOTED_TESTABLE_BY_FAMILY,
            "testable_by_family_now": testable_by_family,
            "families_quoted_with_zero_still_zero": families_with_none,
            "asymmetry_changed": (
                sorted(families_with_none) != sorted(QUOTED_FAMILIES_WITH_NONE)
                or testable_by_family.get("ASCERTAINMENT_SERVICE")
                != QUOTED_TESTABLE_BY_FAMILY["ASCERTAINMENT_SERVICE"]
            ),
        },
        "connector_inventory": {
            "declared_source_ids": declared,
            "modules_declaring_no_source_id": undeclared,
            "note": (
                "Connector inventory is recorded for drift detection only. Reachability is "
                "read from registries/workstreams.csv access tokens and is not a function of "
                "which connectors exist."
            ),
        },
        "workstream_source_coverage": workstream_source_coverage(
            registry_root,
            connector_ids=set(declared.values()),
            store_source_ids=store_source_ids(database),
        ),
    }, census


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registries", default=str(REPOSITORY_ROOT / "registries"))
    parser.add_argument("--database", default=str(REPOSITORY_ROOT / "runtime" / "oslt.db"))
    parser.add_argument(
        "--output", default=str(REPOSITORY_ROOT / "data" / "feasibility_census.json")
    )
    parser.add_argument("--apply", action="store_true", help="seal a run manifest and persist")
    arguments = parser.parse_args()

    registry_root = Path(arguments.registries)
    database = Path(arguments.database)
    report, census = build_report(registry_root, database)

    requirements = requirements_for_blocked(census.results)
    report["design_requirements"] = [
        {
            "proposition_id": item.proposition_id,
            "model_family": item.model_family,
            "reachability": item.reachability.value,
            "design_needed": item.design_needed,
            "minimum_detectable_or": item.minimum_detectable_or,
            "participants_required": item.participants_required,
            "governance_needed": item.governance_needed,
            "claim_tier": item.claim_tier.value,
            "epistemic_status": item.epistemic_status.value,
        }
        for item in requirements
    ]

    census_id = f"FC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    run_id = f"FEAS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    report["census_id"] = census_id
    report["run_id"] = run_id if arguments.apply else "NOT_PERSISTED"

    Path(arguments.output).parent.mkdir(parents=True, exist_ok=True)
    Path(arguments.output).write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    counts = report["summary"]["by_reachability"]  # type: ignore[index]
    print(json.dumps(report["drift_against_handoff"], indent=2))
    print(json.dumps(report["ballot"], indent=2))
    print(f"counts now: {counts}")
    print(f"design requirements priced: {len(requirements)}")

    if arguments.apply:
        store = SQLiteStore(database)
        store.initialise()
        manifest = build_run_manifest(
            run_id=run_id,
            objective="Feasibility census over the proposition registry",
            proposition_ids=[item.proposition_id for item in census.results],
            connectors=[],
            registry_hashes=report["registry_digest"],  # type: ignore[arg-type]
            preregistration_ref=NOT_PREREGISTERED,
            root=REPOSITORY_ROOT,
        )
        store.save_run(manifest, authority=AuthorityLevel.A3_VERIFIED_EVIDENCE_COMPUTATION)
        store.save_feasibility_census(
            census_id=census_id,
            run_id=run_id,
            assessed_at=str(report["assessed_at"]),
            registry_digest=report["registry_digest"],  # type: ignore[arg-type]
            summary=report["summary"],  # type: ignore[arg-type]
            results=census.results,
            requirements=requirements,
        )
        print(f"persisted census {census_id} under run {run_id}")
    else:
        print("dry run: nothing written to the store (pass --apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
