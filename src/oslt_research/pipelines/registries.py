from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from oslt_research.domain.enums import ClaimTier, ModelFamily
from oslt_research.domain.models import HypothesisProposition


EXPECTED_COUNTS = {
    "hypotheses.csv": 64,
    "variables.csv": 640,
    "sources.csv": 65,
    "methods.csv": 100,
    "workstreams.csv": 13,
}


@dataclass(frozen=True)
class RegistrySummary:
    counts: dict[str, int]
    failures: list[str]

    @property
    def valid(self) -> bool:
        return not self.failures


def _split_semicolon(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def load_hypotheses(path: str | Path) -> list[HypothesisProposition]:
    result: list[HypothesisProposition] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            result.append(
                HypothesisProposition(
                    proposition_id=row["proposition_id"],
                    model_family=ModelFamily(row["model_family"]),
                    domain=row["domain"],
                    statement=row["statement"],
                    prediction=row["prediction"],
                    falsifier=row["falsifier"],
                    required_workstreams=_split_semicolon(row["required_workstreams"]),
                    primary_outcome_construct=row["primary_outcome_construct"],
                    temporal_requirement=row["temporal_requirement"],
                    maximum_claim_state=ClaimTier(row["maximum_claim_state"]),
                    status=row["status"],
                )
            )
    return result


def registry_summary(registry_root: str | Path) -> RegistrySummary:
    root = Path(registry_root)
    counts: dict[str, int] = {}
    failures: list[str] = []
    for name, expected in EXPECTED_COUNTS.items():
        path = root / name
        if not path.exists():
            failures.append(f"MISSING_REGISTRY:{name}")
            counts[name] = 0
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            count = sum(1 for _ in csv.DictReader(handle))
        counts[name] = count
        if count != expected:
            failures.append(f"REGISTRY_COUNT_DRIFT:{name}:{count}!={expected}")

    try:
        hypotheses = load_hypotheses(root / "hypotheses.csv")
        ids = [item.proposition_id for item in hypotheses]
        if len(ids) != len(set(ids)):
            failures.append("DUPLICATE_PROPOSITION_ID")
        if not all(item.prediction.strip() and item.falsifier.strip() for item in hypotheses):
            failures.append("PROPOSITION_WITHOUT_PREDICTION_OR_FALSIFIER")
        families = {item.model_family for item in hypotheses}
        missing_families = set(ModelFamily) - families
        if missing_families:
            failures.append(
                "MISSING_COMPETING_MODEL_FAMILIES:"
                + ",".join(sorted(item.value for item in missing_families))
            )
    except Exception as exc:  # fail closed on malformed registry
        failures.append(f"HYPOTHESIS_REGISTRY_INVALID:{exc}")

    return RegistrySummary(counts=counts, failures=failures)
