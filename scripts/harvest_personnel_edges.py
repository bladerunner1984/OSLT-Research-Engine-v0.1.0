"""Harvest Companies House officer/PSC edges for organisations already in the graph.

WHY
---
`docs/COUPLING_READJUDICATION.md` §7 names personnel overlap as the first bound on its
own MX09 disposition: no board or personnel data is loaded, so coupling running through
shared directors is invisible. This script loads exactly that channel, so the
disposition can be attacked with the evidence it says it lacks.

WHAT IT SELECTS
---------------
Every entity in `runtime/oslt.db` carrying a `companies_house` identifier. There are 94
of them, out of 824 entities and 390 with any strong identifier. That is not a sample of
the graph - it is a CENSUS of the only part of the graph Companies House can speak
about at all. The remaining 730 entities carry a charity number, a 360Giving org id, an
OCDS party id or nothing, and cannot be looked up in this register. That bound is
recorded in the output and must travel with any result.

ORDERING
--------
Companies are ordered so that, if the budget were exhausted, the ones harvested first
are the ones whose overlap could actually flip the verdict: POLICY / COMMERCIAL /
ACADEMIC domains, and organisations sitting on ADVISES, CONTRACTS_WITH or
ISSUES_GUIDANCE_TO edges, ahead of the 360Giving philanthropic grantee mass. The
ordering is fixed BEFORE any request is made and is not revisited after seeing results.

ABSENCE DISCIPLINE
------------------
An empty officer list is EMPTY_UNCONFIRMED (an unknown company number also returns 200
with an empty list). A 429 or 404 is UNAVAILABLE - unknown, never "no officers". Both
are counted separately from "harvested" in the coverage report.

THROTTLING
----------
600 requests per 5 minutes. `CompaniesHouseOfficersConnector` applies the shared
minimum interval from the FIRST request, not after a 429. A hard request budget is
enforced here as well, and the run stops and reports rather than silently truncating.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import httpx

from oslt_research.connectors.companies_house_officers import (
    CompaniesHouseOfficersConnector,
    PersonnelFragment,
    merge_fragments,
)
from oslt_research.ontology.entities import RelationType, SystemDomain
from oslt_research.persistence.sqlite import SQLiteStore

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "personnel_edges.json"

#: Relation types whose endpoints are the advisory / procurement / guidance networks.
#: A bridge between one of these and the funding network is the tie that would flip the
#: MX09 disposition, so their members are harvested first.
PRIORITY_RELATION_TYPES = {
    RelationType.ADVISES,
    RelationType.CONTRACTS_WITH,
    RelationType.ISSUES_GUIDANCE_TO,
}
PRIORITY_DOMAINS = {SystemDomain.POLICY, SystemDomain.COMMERCIAL, SystemDomain.ACADEMIC}

#: Wall-clock guard. 0.55s minimum interval => ~109 requests/minute.
MIN_INTERVAL_SECONDS = 0.55
REQUEST_BUDGET = 2400
BUDGET_MINUTES = 30.0  # full set measures ~23 min; the extra 7 absorbs transport retries


def with_transport_retry(call, label, unavailable):
    """Run one fetch, retrying transient transport failures.

    A DNS or connection failure is a property of this machine's network, not of the
    register. It is recorded as UNAVAILABLE_TRANSPORT - unknown, never "no officers" -
    and the run continues rather than losing the whole harvest, as one earlier run did
    at officer 1000 of 1798.
    """

    for attempt in range(3):
        try:
            return call()
        except httpx.HTTPError as exc:
            if attempt == 2:
                unavailable[label] = f"UNAVAILABLE_TRANSPORT_{type(exc).__name__}"
                return PersonnelFragment(companies_unavailable=dict(unavailable))
            time.sleep(5.0 * (attempt + 1))
    return PersonnelFragment()


def select_companies(entities, relations):
    """Graph entities carrying a Companies House number, priority-ordered."""

    priority_entity_ids: set[str] = set()
    for relation in relations:
        if relation.relation_type in PRIORITY_RELATION_TYPES:
            priority_entity_ids.add(relation.source_entity_id)
            priority_entity_ids.add(relation.target_entity_id)

    selected = []
    for entity in entities:
        number = str(entity.identifiers.get("companies_house") or "").strip().upper()
        if not number:
            continue
        on_priority_edge = entity.entity_id in priority_entity_ids
        in_priority_domain = entity.system_domain in PRIORITY_DOMAINS
        rank = 0 if (on_priority_edge and in_priority_domain) else (
            1 if on_priority_edge else (2 if in_priority_domain else 3)
        )
        selected.append(
            {
                "entity_id": entity.entity_id,
                "company_number": number,
                "name": entity.canonical_name,
                "domain": entity.system_domain.value,
                "on_priority_edge": on_priority_edge,
                "rank": rank,
            }
        )
    selected.sort(key=lambda row: (row["rank"], row["company_number"]))
    return selected


def main() -> int:
    store = SQLiteStore(ROOT / "runtime" / "oslt.db")
    entities = store.list_entities()
    relations = store.list_relations()
    targets = select_companies(entities, relations)

    per_company_requests = 2  # officers + PSC, before pagination
    estimate_phase_one = len(targets) * per_company_requests
    print(
        f"Selected {len(targets)} of {len(entities)} graph entities "
        f"(all those carrying a companies_house identifier).\n"
        f"Phase 1 (officers + PSC): >= {estimate_phase_one} requests, "
        f">= {estimate_phase_one * MIN_INTERVAL_SECONDS / 60:.1f} min at "
        f"{MIN_INTERVAL_SECONDS}s/request.\n"
        f"Phase 2 (reverse index /officers/{{id}}/appointments): one request per distinct "
        f"officer id found, unknown until phase 1 completes; capped by a "
        f"{REQUEST_BUDGET}-request / {BUDGET_MINUTES:.0f}-minute budget.",
        flush=True,
    )

    connector = CompaniesHouseOfficersConnector(min_interval_seconds=MIN_INTERVAL_SECONDS)
    started = time.monotonic()
    requests_used = 0
    transport_failures: dict[str, str] = {}
    fragments = []
    phase_one_done: list[str] = []
    phase_one_skipped: list[str] = []

    def budget_exhausted() -> bool:
        return (
            requests_used >= REQUEST_BUDGET
            or (time.monotonic() - started) / 60.0 >= BUDGET_MINUTES
        )

    for index, row in enumerate(targets, start=1):
        if budget_exhausted():
            phase_one_skipped.extend(item["company_number"] for item in targets[index - 1 :])
            break
        fragment = with_transport_retry(
            lambda row=row: connector.harvest_company(
                row["company_number"], company_name=row["name"], include_psc=True
            ),
            f"company:{row['company_number']}",
            transport_failures,
        )
        requests_used += per_company_requests
        fragments.append(fragment)
        phase_one_done.append(row["company_number"])
        if index % 10 == 0:
            print(
                f"  phase 1: {index}/{len(targets)} companies, "
                f"{(time.monotonic() - started) / 60:.1f} min elapsed",
                flush=True,
            )

    phase_one = merge_fragments(fragments) if fragments else None

    # --------------------------------------------------------------- phase two
    # The reverse index. One request per distinct officer id returns every company that
    # person is appointed to, including companies not reached in phase 1.
    officer_ids = sorted(
        {
            entity.entity_id.split("-", 1)[1]
            for entity in (phase_one.entities if phase_one else [])
            if entity.entity_id.startswith("CHO-")
        }
    )
    print(
        f"Phase 1 complete: {len(phase_one_done)} companies, "
        f"{len(officer_ids)} distinct officer ids. Phase 2 needs {len(officer_ids)} "
        f"requests, ~{len(officer_ids) * MIN_INTERVAL_SECONDS / 60:.1f} min.",
        flush=True,
    )

    appointment_fragments = []
    officers_queried: list[str] = []
    officers_skipped: list[str] = []
    for index, officer_id in enumerate(officer_ids, start=1):
        if budget_exhausted():
            officers_skipped.extend(officer_ids[index - 1 :])
            break
        appointment_fragments.append(
            with_transport_retry(
                lambda officer_id=officer_id: connector.harvest_officer_appointments(
                    officer_id
                ),
                f"officer:{officer_id}",
                transport_failures,
            )
        )
        requests_used += 1
        officers_queried.append(officer_id)
        if index % 25 == 0:
            print(
                f"  phase 2: {index}/{len(officer_ids)} officers, "
                f"{(time.monotonic() - started) / 60:.1f} min elapsed",
                flush=True,
            )

    combined = merge_fragments([f for f in fragments + appointment_fragments])

    # ------------------------------------------------------- overlap, graph-relative
    # A shared officer only matters here if it joins two organisations ALREADY IN THE
    # GRAPH. Appointments at companies outside the graph are recorded but cannot bridge
    # anything, and are reported separately rather than counted as a finding.
    graph_numbers = {row["company_number"]: row for row in targets}
    by_person: dict[str, set[str]] = defaultdict(set)
    for relation in combined.relations:
        if relation.source_entity_id.startswith(("CHO-", "CHP-")):
            by_person[relation.source_entity_id].add(relation.target_entity_id)

    bridges = []
    for person, orgs in sorted(by_person.items()):
        in_graph = sorted(
            number for number in (org.removeprefix("CH-") for org in orgs)
            if number in graph_numbers
        )
        if len(in_graph) > 1:
            name = next(
                (e.canonical_name for e in combined.entities if e.entity_id == person), person
            )
            bridges.append(
                {
                    "person_entity_id": person,
                    "person_name": name,
                    "graph_organisations": [
                        {
                            "company_number": number,
                            "graph_entity_id": graph_numbers[number]["entity_id"],
                            "name": graph_numbers[number]["name"],
                            "domain": graph_numbers[number]["domain"],
                            "on_priority_edge": graph_numbers[number]["on_priority_edge"],
                        }
                        for number in in_graph
                    ],
                    "total_appointments_including_outside_graph": len(orgs),
                }
            )

    payload = {
        "generated_by": "scripts/harvest_personnel_edges.py",
        "generated_at": datetime.now(UTC).isoformat(),
        "store": str(store.path),
        "coverage": {
            "graph_entities_total": len(entities),
            "graph_entities_with_any_strong_identifier": sum(
                1 for e in entities if e.strong_identifiers()
            ),
            "graph_entities_with_companies_house_number": len(targets),
            "companies_harvested": phase_one_done,
            "companies_not_harvested_budget": phase_one_skipped,
            "officer_ids_found": len(officer_ids),
            "officer_ids_queried_for_appointments": len(officers_queried),
            "officer_ids_not_queried_budget": officers_skipped,
            "requests_used": requests_used,
            "transport_failures_unknown_not_absence": transport_failures,
            "wall_clock_minutes": round((time.monotonic() - started) / 60, 2),
            "NOT_COVERED": (
                f"{len(entities) - len(targets)} graph entities carry no Companies House "
                "number (charity number, 360Giving org id, OCDS party id, or none) and "
                "cannot be looked up in this register at all. The 883 360Giving grantee "
                "relations are overwhelmingly in that group. Any personnel tie running "
                "through those bodies is invisible to this harvest."
            ),
        },
        "fragment_summary": combined.summary(),
        "bridges_between_graph_organisations": bridges,
        "entities": [json.loads(e.model_dump_json()) for e in combined.entities],
        "relations": [json.loads(r.model_dump_json()) for r in combined.relations],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "coverage": {
                    k: v
                    for k, v in payload["coverage"].items()
                    if k not in {"companies_harvested", "officer_ids_not_queried_budget"}
                },
                "fragment_summary": payload["fragment_summary"],
                "bridges_between_graph_organisations": len(bridges),
            },
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
