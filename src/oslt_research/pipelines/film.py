from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from oslt_research.domain.models import FilmSceneRecord, ReleasedClaim


def build_scene_records(claims: Iterable[ReleasedClaim]) -> list[FilmSceneRecord]:
    scenes: list[FilmSceneRecord] = []
    for index, claim in enumerate(claims, start=1):
        _, limiting_score = claim.certainty.minimum()
        scenes.append(
            FilmSceneRecord(
                scene_id=f"SCENE-{index:03d}",
                narrated_claim=claim.wording,
                released_claim_id=claim.claim_id,
                evidence_ids=claim.evidence_ids,
                counterevidence_ids=claim.counterevidence_ids,
                certainty_label=f"{claim.claim_tier.value} (floor={limiting_score:.2f})",
                permitted_wording=claim.permitted_phrases,
                prohibited_wording=claim.prohibited_phrases,
                uncertainty_disclosure=claim.uncertainty_disclosure,
                human_review_reference=claim.human_review_reference,
            )
        )
    return scenes


def write_claim_scene_register(
    claims: Iterable[ReleasedClaim],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scenes = build_scene_records(claims)
    fields = [
        "scene_id",
        "narrated_claim",
        "released_claim_id",
        "evidence_ids",
        "counterevidence_ids",
        "certainty_label",
        "permitted_wording",
        "prohibited_wording",
        "uncertainty_disclosure",
        "human_review_reference",
        "visual_source_ids",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for scene in scenes:
            row = scene.model_dump()
            for key in [
                "evidence_ids",
                "counterevidence_ids",
                "permitted_wording",
                "prohibited_wording",
                "visual_source_ids",
            ]:
                row[key] = ";".join(row[key])
            writer.writerow(row)
    return path
