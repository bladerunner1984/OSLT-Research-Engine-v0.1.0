from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from oslt_research.connectors.base import HarvestQuery, SourceConnector
from oslt_research.domain.models import EvidenceObject, KernelResult, RunManifest
from oslt_research.evidence.journal import ResearchComputationJournal
from oslt_research.evidence.provenance import canonical_json_hash
from oslt_research.evidence.study_family import StudyFamilyResolver
from oslt_research.kernels.academic_knowledge import AcademicKnowledgeProductionKernel
from oslt_research.persistence.sqlite import SQLiteStore

from .harvest import execute_harvest
from .run_manifest import build_run_manifest


@dataclass(frozen=True)
class PilotOneOutput:
    run_id: str
    evidence: list[EvidenceObject]
    kernel_results: list[KernelResult]
    corpus_manifest_path: Path
    family_resolution: object | None = None
    run_manifest: RunManifest | None = None


async def run_pilot_one(
    *,
    run_id: str,
    connectors: Iterable[SourceConnector],
    query: HarvestQuery,
    store: SQLiteStore,
    output_root: str | Path,
    cohort_lexicon: Iterable[str] = (),
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
    # Identifier equality only finds the same paper twice; research dependence (shared
    # trial, cohort, dataset or research group) has to be resolved explicitly or the
    # synthesis layer will read a single sample as many independent sources.
    naive_families = len({item.dependency_family for item in evidence})
    evidence, family_resolution = StudyFamilyResolver(
        cohort_lexicon=tuple(cohort_lexicon)
    ).apply(evidence)
    journal.append(
        "DEPENDENCY_FAMILIES_RESOLVED",
        {
            "naive_family_count": naive_families,
            "resolved_family_count": family_resolution.family_count,
            "collapse_rate": round(family_resolution.collapse_rate, 4),
            "signal_counts": family_resolution.signal_counts,
            "cohort_lexicon": list(cohort_lexicon),
            "links": [link.__dict__ for link in family_resolution.links],
        },
    )
    for item in evidence:
        store.save_evidence(item)

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "query": query.model_dump(mode="json"),
        "record_count": len(evidence),
        "admitted_count": sum(1 for item in evidence if item.admitted),
        "dependency_families": sorted({item.dependency_family for item in evidence}),
        "naive_dependency_family_count": naive_families,
        "dependency_collapse_rate": round(family_resolution.collapse_rate, 4),
        "dependency_collapse_signals": family_resolution.signal_counts,
        "cohort_lexicon": list(cohort_lexicon),
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

    # The reproducibility manifest is point 8 of the claim release standard. It is
    # written before analysis so a run that later fails still leaves a record of what it
    # was, rather than only successful runs being reproducible.
    run_manifest = build_run_manifest(
        run_id=run_id,
        objective=query.concept,
        proposition_ids=query.proposition_ids,
        connectors=connector_list,
        corpus_hashes={"corpus_manifest": manifest["manifest_sha256"]},
    )
    store.save_run(run_manifest)
    journal.append("RUN_MANIFEST_SEALED", run_manifest.model_dump(mode="json"))

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
        family_resolution=family_resolution,
        run_manifest=run_manifest,
    )
