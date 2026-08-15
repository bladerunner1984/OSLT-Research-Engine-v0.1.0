from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from oslt_research.connectors.base import HarvestQuery, SourceConnector
from oslt_research.domain.models import EvidenceObject, KernelResult
from oslt_research.evidence.journal import ResearchComputationJournal
from oslt_research.evidence.provenance import canonical_json_hash
from oslt_research.kernels.academic_knowledge import AcademicKnowledgeProductionKernel
from oslt_research.persistence.sqlite import SQLiteStore

from .harvest import execute_harvest


@dataclass(frozen=True)
class PilotOneOutput:
    run_id: str
    evidence: list[EvidenceObject]
    kernel_results: list[KernelResult]
    corpus_manifest_path: Path


async def run_pilot_one(
    *,
    run_id: str,
    connectors: Iterable[SourceConnector],
    query: HarvestQuery,
    store: SQLiteStore,
    output_root: str | Path,
) -> PilotOneOutput:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    journal = ResearchComputationJournal(output_root / "computation-journal.jsonl")
    journal.append("PILOT_ONE_STARTED", {"run_id": run_id, "query": query.model_dump()})

    connector_list = list(connectors)
    evidence: list[EvidenceObject] = []
    source_counts: dict[str, int] = {}
    for connector in connector_list:
        harvested = await execute_harvest(connector, query, store=store)
        evidence.extend(harvested.evidence)
        source_counts[connector.source_name] = len(harvested.evidence)
        journal.append(
            "SOURCE_HARVEST_COMPLETED",
            {
                "source": connector.source_name,
                "admitted": len(harvested.admitted),
                "rejected": len(harvested.rejected),
            },
        )

    # Preserve source-specific records but collapse shared study families during analysis.
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "query": query.model_dump(mode="json"),
        "record_count": len(evidence),
        "admitted_count": sum(1 for item in evidence if item.admitted),
        "dependency_families": sorted({item.dependency_family for item in evidence}),
        "evidence_ids": [item.evidence_id for item in evidence],
        "connector_versions": {
            connector.source_name: connector.connector_version
            for connector in connector_list
        },
        "source_record_counts": source_counts,
    }
    manifest["manifest_sha256"] = canonical_json_hash(manifest)
    manifest_path = output_root / "corpus-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    journal.append("CORPUS_SEALED", {"manifest_path": str(manifest_path), **manifest})

    kernel = AcademicKnowledgeProductionKernel()
    period = f"{query.from_date or 'UNBOUNDED'}..{query.to_date or 'PRESENT'}"
    results = kernel.analyse(run_id=run_id, evidence=evidence, period=period)
    for result in results:
        store.save_kernel_result(result)
        journal.append("KERNEL_RESULT_CREATED", result.model_dump(mode="json"))

    if not journal.verify():
        raise RuntimeError("COMPUTATION_JOURNAL_VERIFICATION_FAILED")
    return PilotOneOutput(
        run_id=run_id,
        evidence=evidence,
        kernel_results=results,
        corpus_manifest_path=manifest_path,
    )
