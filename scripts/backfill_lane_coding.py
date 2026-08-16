"""Lane-code the evidence already in the store.

Existing records were harvested before the classifier was wired into the pipeline, so the
whole corpus persisted with `lane=UNCLASSIFIED` and no coding provenance at all. That is
not a cosmetic gap: EvidenceLane is the axis evidence is partitioned on before
triangulation, so a lane-blind corpus cannot support a triangulation claim.

Backfilling is safe here only because of what the classifier refuses to do. It never
assigns SUPPORT or CONTRADICT (those are proposition-relative and cannot be read off a
text), it declines below its confidence floor, and every code it writes is stamped
AUTOMATED_CLASSIFIER / A5_MODEL_PROPOSAL with `requires_human_adjudication=True`. So no
record can come out of this looking human-coded, and a record with no cue comes out
UNCLASSIFIED with a recorded reason rather than a guess.

Run with --dry-run first; it is the default.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from oslt_research.evidence.lane_coding import apply_lane_assignment
from oslt_research.persistence.sqlite import SQLiteStore


def backfill(store: SQLiteStore, *, apply_changes: bool) -> dict[str, int]:
    """Re-code every stored record, returning the resulting lane distribution."""

    records = store.list_evidence()
    distribution: Counter[str] = Counter()
    changed = 0

    for item in records:
        coded = apply_lane_assignment(item)
        distribution[coded.lane.value] += 1
        if coded.lane is not item.lane or coded.lane_coding != item.lane_coding:
            changed += 1
            if apply_changes:
                store.save_evidence(coded)

    return {"total": len(records), "changed": changed, **distribution}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("runtime/oslt.db"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the codes. Without it nothing is written and the outcome is only reported.",
    )
    args = parser.parse_args()

    store = SQLiteStore(args.db)
    store.initialise()
    result = backfill(store, apply_changes=args.apply)

    mode = "APPLIED" if args.apply else "DRY RUN (nothing written)"
    print(f"{mode} against {args.db}")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
