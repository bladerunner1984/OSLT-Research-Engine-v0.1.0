"""Re-adjudicate the MD15/MX09 institutional coupling test on the CURRENT graph.

The published disposition (MX09 over MD15) was reached on a 337-relation graph. The
SQLite store now holds far more. This script reloads the persisted graph, re-runs
`assess_coupling` at STRONG_IDENTIFIER, and records the verdict against SEVERAL real
outcome dates fixed by Parliament rather than one date chosen by the analyst.

It changes nothing under src/ and lowers no threshold. If the test refuses to
discriminate, that is the recorded output.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import networkx as nx

from oslt_research.connectors.legislation import LegislationConnector
from oslt_research.ontology.entities import SystemDomain
from oslt_research.ontology.graph import InstitutionalOntologyGraph, ResolutionTier
from oslt_research.persistence.sqlite import SQLiteStore

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "coupling_readjudication.json"

#: Fallback outcome dates, used only if the live legislation feed is unreachable.
#: Enactment years as encoded in legislation.gov.uk identifiers, resolved to 1 January
#: exactly as LegislationItem.anchor_date() does.
FALLBACK_DATES = [date(2004, 1, 1), date(2010, 1, 1), date(2022, 1, 1)]
FALLBACK_NOTE = (
    "enactment years recorded in the repo (Gender Recognition Act 2004 /ukpga/2004/7; "
    "Equality Act 2010 /ukpga/2010/15; Health and Care Act 2022 /ukpga/2022/31), "
    "resolved to 1 January by LegislationItem.anchor_date() semantics"
)

QUERIES = ["Gender Recognition", "Equality Act", "Health and Care Act"]


def live_outcome_dates() -> tuple[list[date], str]:
    dates: set[date] = set()
    try:
        connector = LegislationConnector(timeout=30.0)
        for query in QUERIES:
            feed = connector.search(title=query, page_size=50)
            dates.update(feed.outcome_dates())
    except Exception as exc:  # noqa: BLE001
        return [], f"LIVE_FETCH_FAILED: {type(exc).__name__}: {exc}"
    if not dates:
        return [], "LIVE_FETCH_RETURNED_NO_DATED_ITEMS"
    return sorted(dates), "LegislationConnector.outcome_dates() live from legislation.gov.uk"


def component_detail(graph: InstitutionalOntologyGraph, outcome: date, tier: ResolutionTier):
    """Rebuild the same prior-relation projection assess_coupling uses, for reporting."""
    canonical, merges = graph._canonical_map(tier)  # noqa: SLF001 - reporting only

    def node_of(entity_id: str) -> str:
        return canonical.get(entity_id, entity_id)

    prior = [r for r in graph.relations.values() if r.admitted and r.precedes(outcome)]
    projected = nx.Graph()
    for item in prior:
        projected.add_edge(node_of(item.source_entity_id), node_of(item.target_entity_id),
                           relation=item)
    components = sorted(nx.connected_components(projected), key=len, reverse=True)

    def describe(component: set[str]) -> dict:
        sub = projected.subgraph(component)
        domains = sorted(
            {
                graph.entities[n].system_domain.value
                for n in component
                if n in graph.entities
                and graph.entities[n].system_domain is not SystemDomain.UNKNOWN
            }
        )
        kinds = sorted({sub.edges[e]["relation"].relation_type.value for e in sub.edges})
        return {
            "size": len(component),
            "domains": domains,
            "relation_types": kinds,
            "qualifies_for_md15": len(component) > 2 and len(domains) > 1 and len(kinds) > 1,
            "entities": sorted(
                (graph.entities[n].canonical_name if n in graph.entities else n)
                for n in component
            )[:40],
        }

    return {
        "prior_relations": len(prior),
        "components_total": len(components),
        "merges_applied": merges,
        "largest_components": [describe(c) for c in components[:5]],
        "qualifying_components": [
            describe(c) for c in components if describe(c)["qualifies_for_md15"]
        ][:5],
    }


def main() -> int:
    store = SQLiteStore(ROOT / "runtime" / "oslt.db")
    entities = store.list_entities()
    relations = store.list_relations()

    graph = InstitutionalOntologyGraph()
    for entity in entities:
        graph.add_entity(entity)
    placed, unplaceable = 0, 0
    for relation in relations:
        if (
            relation.source_entity_id in graph.entities
            and relation.target_entity_id in graph.entities
        ):
            graph.add_relation(relation)
            placed += 1
        else:
            unplaceable += 1

    outcome_dates, provenance = live_outcome_dates()
    if not outcome_dates:
        outcome_dates, provenance = FALLBACK_DATES, f"FALLBACK ({provenance}): {FALLBACK_NOTE}"

    tier = ResolutionTier.STRONG_IDENTIFIER
    results = {}
    for outcome in outcome_dates:
        assessment = graph.assess_coupling(
            outcome, resolve_entities=True, minimum_resolution_tier=tier
        )
        results[outcome.isoformat()] = {
            "assessment": json.loads(assessment.model_dump_json()),
            "components": component_detail(graph, outcome, tier),
        }

    strong = sum(1 for e in entities if e.strong_identifiers())
    payload = {
        "generated_by": "scripts/readjudicate_coupling.py",
        "store": str(store.path),
        "resolution_tier": tier.value,
        "graph": {
            "entities_in_store": len(entities),
            "relations_in_store": len(relations),
            "relations_placed_in_graph": placed,
            "relations_unplaceable": unplaceable,
            "admitted_relations": sum(1 for r in relations if r.admitted),
            "entities_with_strong_identifier": strong,
            "entities_without_strong_identifier": len(entities) - strong,
            "relation_type_counts": {
                kind: sum(1 for r in relations if r.relation_type.value == kind)
                for kind in sorted({r.relation_type.value for r in relations})
            },
            "system_domain_counts": {
                dom: sum(1 for e in entities if e.system_domain.value == dom)
                for dom in sorted({e.system_domain.value for e in entities})
            },
            "dependency_families": len({r.dependency_family for r in relations}),
        },
        "outcome_date_provenance": provenance,
        "outcome_dates": [d.isoformat() for d in outcome_dates],
        "verdicts": {k: v["assessment"]["verdict"] for k, v in results.items()},
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"verdicts": payload["verdicts"], "provenance": provenance,
                      "strong_ids": strong, "entities": len(entities),
                      "relations": len(relations)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
