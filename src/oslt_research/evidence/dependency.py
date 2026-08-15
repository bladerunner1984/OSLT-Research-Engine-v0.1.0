from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from oslt_research.domain.models import EvidenceObject, KernelResult


@dataclass(frozen=True)
class DependencySummary:
    raw_count: int
    effective_independent_families: int
    family_members: dict[str, list[str]]
    shared_bias_signatures: dict[str, list[str]]


class EvidenceDependencyGraph:
    """Tracks evidence and research-lineage dependence before triangulation."""

    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def add_evidence(self, evidence: EvidenceObject) -> None:
        self.graph.add_node(
            evidence.evidence_id,
            node_type="evidence",
            dependency_family=evidence.dependency_family,
            bias_signature=evidence.metadata.get("bias_signature"),
        )
        family_node = f"family:{evidence.dependency_family}"
        self.graph.add_node(family_node, node_type="family")
        self.graph.add_edge(evidence.evidence_id, family_node, relation="depends_on")

        for parent_id in evidence.metadata.get("parent_evidence_ids", []):
            self.graph.add_node(parent_id, node_type="evidence")
            self.graph.add_edge(evidence.evidence_id, parent_id, relation="derived_from")

    def add_result(self, result: KernelResult) -> None:
        self.graph.add_node(result.result_id, node_type="kernel_result")
        for evidence_id in result.evidence_ids + result.counterevidence_ids:
            self.graph.add_node(evidence_id, node_type="evidence")
            self.graph.add_edge(result.result_id, evidence_id, relation="uses")

    @staticmethod
    def summarise(evidence: Iterable[EvidenceObject]) -> DependencySummary:
        items = list(evidence)
        families: dict[str, list[str]] = defaultdict(list)
        bias_signatures: dict[str, list[str]] = defaultdict(list)
        for item in items:
            families[item.dependency_family].append(item.evidence_id)
            signature = item.metadata.get("bias_signature")
            if signature:
                bias_signatures[str(signature)].append(item.evidence_id)

        shared = {key: value for key, value in bias_signatures.items() if len(value) > 1}
        return DependencySummary(
            raw_count=len(items),
            effective_independent_families=len(families),
            family_members=dict(families),
            shared_bias_signatures=shared,
        )

    @staticmethod
    def effective_result_weight(result: KernelResult) -> float:
        families = set(result.dependency_families)
        evidence_count = max(1, len(result.evidence_ids) + len(result.counterevidence_ids))
        independence_ratio = min(1.0, len(families) / evidence_count) if families else 0.25
        _, certainty_floor = result.certainty.minimum()
        return certainty_floor * (0.5 + 0.5 * independence_ratio)
