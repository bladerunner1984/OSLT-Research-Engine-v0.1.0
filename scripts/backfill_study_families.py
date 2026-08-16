"""Resolve study families across the evidence already in the store.

Existing records were harvested before ``StudyFamilyResolver`` was wired into
``execute_harvest``, so every record persisted with its *dedup key* — the DOI — sitting in
the ``dependency_family`` field. That is not a naming quirk. Dependency-family collapse is
what stops three reports of one trial counting as three independent corroborations, so a
corpus of 98% singleton "families" inflates every corroboration count in the project by an
unknown factor and no triangulation claim over it can be trusted.

This pass re-clusters the whole corpus at once, which is strictly stronger than the
per-batch resolution the harvest path can do: two reports of the same trial harvested in
different runs can only be merged by a corpus-wide pass.

The thresholds are NOT relaxed here. Author-network overlap still requires >=2 shared
authors AND Jaccard >=0.6. Under-collapsing biases towards over-counting independence,
which is the conservative direction for corroboration but must be reported, not fixed by
loosening the rule.

Run with the default dry run first, and back the database up before ``--apply``:
    copy runtime/oslt.db runtime/oslt.db.pre-family-backfill
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Sequence

from oslt_research.domain.models import EvidenceObject
from oslt_research.evidence.study_family import StudyFamilyResolver
from oslt_research.persistence.sqlite import SQLiteStore


def _outcome(item: EvidenceObject) -> tuple[str, tuple[str, ...], int, str]:
    """The fields this backfill owns, for an identical-outcome comparison.

    Re-running must report zero changes. Comparing the whole record would be wrong (other
    passes may have touched it) and comparing nothing at all is how the lane backfill
    initially rewrote every row on every run.
    """

    metadata = item.metadata or {}
    return (
        item.dependency_family,
        tuple(metadata.get("dependency_family_basis") or ()),
        int(metadata.get("dependency_family_size") or 0),
        str(metadata.get("dedup_key") or ""),
    )


def backfill(
    store: SQLiteStore,
    *,
    apply_changes: bool,
    cohort_lexicon: Sequence[str] = (),
) -> dict[str, object]:
    """Re-resolve every stored record's dependency family, reporting what moved."""

    records = store.list_evidence()
    before_families = Counter(item.dependency_family for item in records)
    before_sizes = Counter(before_families.values())

    resolver = StudyFamilyResolver(cohort_lexicon=tuple(cohort_lexicon))
    resolved, resolution = resolver.apply(records)

    existing = {item.evidence_id: _outcome(item) for item in records}
    changed = 0
    for item in resolved:
        if _outcome(item) == existing[item.evidence_id]:
            continue
        changed += 1
        if apply_changes:
            store.save_evidence(item)

    sizes = resolution.size_distribution()
    return {
        "total": len(records),
        "changed": changed,
        "families_before": len(before_families),
        "families_after": resolution.family_count,
        "multi_member_families": sum(count for size, count in sizes.items() if size > 1),
        "largest_family": max(sizes) if sizes else 0,
        "size_distribution_before": dict(sorted(before_sizes.items())),
        "size_distribution_after": sizes,
        "basis_counts": resolution.basis_counts(),
        "signal_counts": resolution.signal_counts,
        "collapse_rate": round(resolution.collapse_rate, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("runtime/oslt.db"))
    parser.add_argument(
        "--cohort",
        action="append",
        default=[],
        help="A preregistered named cohort. Repeatable. Empty by default on purpose: which "
        "cohorts dominate a literature is a study-design decision, not an engine guess.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the families. Without it nothing is written and the outcome is reported.",
    )
    args = parser.parse_args()

    store = SQLiteStore(args.db)
    store.initialise()
    result = backfill(store, apply_changes=args.apply, cohort_lexicon=args.cohort)

    mode = "APPLIED" if args.apply else "DRY RUN (nothing written)"
    print(f"{mode} against {args.db}")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
