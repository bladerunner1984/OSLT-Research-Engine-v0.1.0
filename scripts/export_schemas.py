from __future__ import annotations

import json
from pathlib import Path

from oslt_research.connectors.base import HarvestQuery, RawRecord
from oslt_research.domain.models import (
    EvidenceObject,
    FilmSceneRecord,
    KernelResult,
    ReleasedClaim,
    RunManifest,
    SynthesisOutcome,
)
from oslt_research.governance.continuity import ContinuityHandoff, ResearchState


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "schemas"
MODELS = {
    "evidence-object.schema.json": EvidenceObject,
    "kernel-result.schema.json": KernelResult,
    "synthesis-outcome.schema.json": SynthesisOutcome,
    "run-manifest.schema.json": RunManifest,
    "released-claim.schema.json": ReleasedClaim,
    "film-scene.schema.json": FilmSceneRecord,
    "harvest-query.schema.json": HarvestQuery,
    "raw-record.schema.json": RawRecord,
    "continuity-handoff.schema.json": ContinuityHandoff,
    "research-state.schema.json": ResearchState,
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, model in MODELS.items():
        path = OUTPUT / filename
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(path)


if __name__ == "__main__":
    main()
