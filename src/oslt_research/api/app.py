from __future__ import annotations

from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from oslt_research.domain.models import KernelResult, SynthesisOutcome
from oslt_research.governance.preflight import run_preflight
from oslt_research.governance.sample_size import AttainableInferenceEnvelope, attainable_envelope
from oslt_research.persistence.sqlite import SQLiteStore
from oslt_research.pipelines.registries import registry_summary
from oslt_research.pipelines.synthesis import MasterSynthesisKernel
from oslt_research.settings import database_path, repository_root


@asynccontextmanager
async def lifespan(_: FastAPI):
    SQLiteStore(database_path()).initialise()
    yield


app = FastAPI(
    title="OSLT Research Engine",
    version="0.1.0",
    description="Governed competing-model research synthesis API",
    lifespan=lifespan,
)


class SynthesisRequest(BaseModel):
    run_id: str = Field(min_length=1)
    results: list[KernelResult]


class SampleEnvelopeRequest(BaseModel):
    available_n: int = Field(gt=0)
    effective_parameters: int = Field(gt=0)
    outcome_events: int | None = Field(default=None, ge=0)
    design_effect: float = Field(default=1.0, ge=1.0)
    attrition_fraction: float = Field(default=0.0, ge=0.0, lt=1.0)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_gateway": "disabled"}


@app.get("/constitution")
def constitution() -> dict[str, object]:
    path = repository_root() / "config/constitution.yaml"
    if not path.exists():
        raise HTTPException(status_code=500, detail="constitution missing")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@app.get("/registries/summary")
def registries_summary() -> dict[str, object]:
    summary = registry_summary(repository_root() / "registries")
    return {"valid": summary.valid, "counts": summary.counts, "failures": summary.failures}


@app.get("/preflight")
def preflight() -> dict[str, object]:
    return run_preflight(repository_root()).as_dict()


@app.post("/sample-size/envelope", response_model=AttainableInferenceEnvelope)
def sample_size_envelope(request: SampleEnvelopeRequest) -> AttainableInferenceEnvelope:
    return attainable_envelope(
        available_n=request.available_n,
        effective_parameters=request.effective_parameters,
        outcome_events=request.outcome_events,
        design_effect_value=request.design_effect,
        attrition_fraction=request.attrition_fraction,
    )


@app.post("/synthesis", response_model=SynthesisOutcome)
def synthesise(request: SynthesisRequest) -> SynthesisOutcome:
    try:
        result = MasterSynthesisKernel().synthesise(
            run_id=request.run_id,
            results=request.results,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    SQLiteStore(database_path()).save_synthesis(result)
    return result
