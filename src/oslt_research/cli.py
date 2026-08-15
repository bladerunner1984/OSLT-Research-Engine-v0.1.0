from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from oslt_research.connectors.base import HarvestQuery
from oslt_research.connectors.clinicaltrials import ClinicalTrialsConnector
from oslt_research.connectors.crossref import CrossrefConnector
from oslt_research.connectors.openalex import OpenAlexConnector
from oslt_research.connectors.pubmed import PubMedConnector
from oslt_research.governance.preflight import run_preflight
from oslt_research.governance.sample_size import attainable_envelope
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.harvest import execute_harvest
from oslt_research.pipelines.pilot1 import run_pilot_one
from oslt_research.pipelines.registries import registry_summary
from oslt_research.pipelines.synthesis import MasterSynthesisKernel
from oslt_research.settings import database_path, repository_root


app = typer.Typer(help="OSLT governed research engine")
console = Console()


def _connector(name: str):
    lowered = name.casefold()
    if lowered == "openalex":
        return OpenAlexConnector(
            mailto=os.getenv("OSLT_OPENALEX_MAILTO"),
            api_key=os.getenv("OSLT_OPENALEX_API_KEY"),
        )
    if lowered == "crossref":
        return CrossrefConnector(mailto=os.getenv("OSLT_CROSSREF_MAILTO"))
    if lowered == "pubmed":
        return PubMedConnector(api_key=os.getenv("OSLT_NCBI_API_KEY"))
    if lowered in {"clinicaltrials", "clinicaltrials.gov", "ctgov"}:
        return ClinicalTrialsConnector()
    raise typer.BadParameter(
        "source must be openalex, crossref, pubmed or clinicaltrials"
    )


@app.command("preflight")
def preflight_command() -> None:
    report = run_preflight(repository_root())
    console.print_json(data=report.as_dict())
    if not report.passed:
        raise typer.Exit(1)


@app.command("registry-summary")
def registry_summary_command() -> None:
    summary = registry_summary(repository_root() / "registries")
    table = Table("Registry", "Rows")
    for name, count in summary.counts.items():
        table.add_row(name, str(count))
    console.print(table)
    if summary.failures:
        console.print("[red]Failures:[/red]")
        for failure in summary.failures:
            console.print(f"- {failure}")
        raise typer.Exit(1)


@app.command("init-db")
def init_db(path: Annotated[Path | None, typer.Option()] = None) -> None:
    resolved = path or database_path()
    SQLiteStore(resolved).initialise()
    console.print(f"Initialised {resolved}")


@app.command("harvest")
def harvest_command(
    source: Annotated[str, typer.Option(help="openalex, crossref, pubmed or clinicaltrials")],
    concept: Annotated[str, typer.Option()],
    max_records: Annotated[int, typer.Option(min=1, max=1000)] = 25,
    proposition: Annotated[list[str] | None, typer.Option()] = None,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    query = HarvestQuery(
        query_id=f"CLI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        concept=concept,
        proposition_ids=proposition or [],
        max_records=max_records,
    )
    result = asyncio.run(
        execute_harvest(_connector(source), query, store=SQLiteStore(database_path()))
    )
    payload = {
        "query": query.model_dump(mode="json"),
        "admitted": len(result.admitted),
        "rejected": len(result.rejected),
        "evidence": [item.model_dump(mode="json") for item in result.evidence],
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        console.print(f"Wrote {output}")
    else:
        console.print_json(data=payload)


@app.command("pilot1")
def pilot_one_command(
    concept: Annotated[str, typer.Option()],
    sources: Annotated[str, typer.Option()] = "openalex,crossref,pubmed,clinicaltrials",
    max_records: Annotated[int, typer.Option(min=1, max=1000)] = 25,
    output_root: Annotated[Path, typer.Option()] = Path(
        "studies/pilot_01_academic_knowledge/outputs/latest"
    ),
) -> None:
    run_id = f"P1-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    query = HarvestQuery(
        query_id=f"{run_id}-Q1",
        concept=concept,
        proposition_ids=["MD11", "MX14"],
        max_records=max_records,
    )
    connectors = [_connector(name.strip()) for name in sources.split(",") if name.strip()]
    result = asyncio.run(
        run_pilot_one(
            run_id=run_id,
            connectors=connectors,
            query=query,
            store=SQLiteStore(database_path()),
            output_root=output_root,
        )
    )
    console.print(
        f"Pilot complete: run={run_id}, evidence={len(result.evidence)}, "
        f"kernel_results={len(result.kernel_results)}, manifest={result.corpus_manifest_path}"
    )


@app.command("synthesise")
def synthesise_command(run_id: Annotated[str, typer.Option()]) -> None:
    store = SQLiteStore(database_path())
    results = store.list_kernel_results(run_id)
    outcome = MasterSynthesisKernel().synthesise(run_id=run_id, results=results)
    store.save_synthesis(outcome)
    console.print_json(data=outcome.model_dump(mode="json"))


@app.command("sample-envelope")
def sample_envelope_command(
    available_n: Annotated[int, typer.Option(min=1)],
    effective_parameters: Annotated[int, typer.Option(min=1)],
    outcome_events: Annotated[int | None, typer.Option(min=0)] = None,
    design_effect: Annotated[float, typer.Option(min=1.0)] = 1.0,
    attrition: Annotated[float, typer.Option(min=0.0, max=0.99)] = 0.0,
) -> None:
    envelope = attainable_envelope(
        available_n=available_n,
        effective_parameters=effective_parameters,
        outcome_events=outcome_events,
        design_effect_value=design_effect,
        attrition_fraction=attrition,
    )
    console.print_json(data=envelope.__dict__)


if __name__ == "__main__":
    app()
