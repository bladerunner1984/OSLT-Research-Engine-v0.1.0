"""Live counterevidence sweep over the corpus path.

Runs `harvest_counterevidence_for_kernels` against real sources and persists both the
evidence and - the point of the exercise - a `LaneSearchRecord` per lane, so the corpus
can distinguish "the CONTRADICT lane was searched and returned nothing" from "nobody
searched it". Before this existed the store held 0 CONTRADICT records and no proof that
anyone had ever looked, which made the zero uninterpretable.

Scope defaults to the propositions the persisted kernel results are about (MD11, MX14)
plus their direct rivals, because those are the claims currently resting on an unsearched
absence.

Search concepts come from `build_proposition_queries`, which derives them from the
registry's `domain` and `primary_outcome_construct` and never from `statement`.

Usage:
    python scripts/run_counterevidence.py [--propositions MD11,MX14] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from oslt_research.connectors.europepmc import EuropePmcConnector
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.counterevidence import LANE_QUERY_TERMS, MANDATORY_LANES
from oslt_research.pipelines.kernel_harvest import (
    build_proposition_queries,
    harvest_counterevidence_for_kernels,
)
from oslt_research.settings import database_path, repository_root


#: MD11 and MX14 are the two propositions with persisted kernel results. MX08, MX09 and
#: MX11 are the rival/null model families those results are implicitly compared against,
#: so an unsearched lane on any of them is the same defect one step removed.
DEFAULT_PROPOSITIONS = ("MD11", "MX14", "MX08", "MX09", "MX11")

OUTPUT = Path("data/counterevidence_run.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--propositions", default=",".join(DEFAULT_PROPOSITIONS))
    parser.add_argument("--max-records", type=int, default=25)
    parser.add_argument(
        "--delay",
        type=float,
        default=1.2,
        help="Seconds before every request. Applied from the first request, not after a 429.",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the exact queries that would be issued and exit without any request.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wanted = {item.strip() for item in args.propositions.split(",") if item.strip()}
    queries = [
        item
        for item in build_proposition_queries(repository_root() / "registries")
        if item.proposition_id in wanted
    ]
    missing = wanted - {item.proposition_id for item in queries}
    if missing:
        raise SystemExit(f"unknown propositions: {sorted(missing)}")

    planned = {
        item.proposition_id: {
            "base_concept": item.concept,
            "derived_from": {"domain": item.domain, "outcome": item.outcome_construct},
            "lane_queries": {
                lane.value: [f"{item.concept} {term}" for term in terms]
                for lane, terms in LANE_QUERY_TERMS.items()
            },
        }
        for item in queries
    }

    if args.dry_run:
        print(json.dumps(planned, indent=2))
        return 0

    run_id = args.run_id or f"CE-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    # Europe PMC only, deliberately. OpenAlex was returning 429 and a rate-limited source
    # contributes errors, not evidence - and an error-shaped lane is UNSEARCHED, which
    # would suppress the whole sweep rather than improve it.
    connectors = [EuropePmcConnector(email=None)]
    store = SQLiteStore(database_path())

    report = asyncio.run(
        harvest_counterevidence_for_kernels(
            queries=queries,
            connectors=connectors,
            store=store,
            run_id=run_id,
            max_records_per_query=args.max_records,
            request_delay_seconds=args.delay,
        )
    )

    payload = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [connector.source_name for connector in connectors],
        "mandatory_lanes": [lane.value for lane in MANDATORY_LANES],
        "planned_queries": planned,
        "summary": report.summary(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report.summary()["lane_totals"], indent=2))
    print(f"run_id={run_id} complete={report.complete} -> {args.output}")
    if not report.complete:
        print("INCOMPLETE: mandatory lanes unsearched", report.incomplete_propositions)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
