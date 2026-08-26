from __future__ import annotations

import csv
from pathlib import Path

import pytest

from oslt_research.governance.feasibility import (
    EXPECTED_PROGRAMME_COUNTS,
    ProgrammeFeasibilityClass,
    load_programme_feasibility,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRIES = ROOT / "registries"


def test_programme_register_accounts_for_every_scientific_proposition_once() -> None:
    register = load_programme_feasibility(REGISTRIES)
    with (REGISTRIES / "hypotheses.csv").open(encoding="utf-8-sig") as handle:
        hypothesis_ids = {row["proposition_id"] for row in csv.DictReader(handle)}

    assert len(register.results) == 64
    assert set(register.by_id()) == hypothesis_ids
    assert register.counts() == EXPECTED_PROGRAMME_COUNTS


def test_primary_human_research_is_preserved_but_parked() -> None:
    register = load_programme_feasibility(REGISTRIES)

    assert [item.proposition_id for item in register.parked()] == [
        "MD04",
        "MD05",
        "MD06",
        "MD20",
        "TH02",
        "TH03",
        "TH06",
    ]
    assert all(item.programme_status == "PARKED_NO_PRIMARY_IMPLEMENTATION" for item in register.parked())


def test_th07_is_preserved_and_mapped_to_md15() -> None:
    register = load_programme_feasibility(REGISTRIES)
    item = register.by_id()["TH07"]

    assert item.classification is ProgrammeFeasibilityClass.DUPLICATIVE
    assert item.mapped_to == "MD15"
    assert item.programme_status == "PRESERVED_MAPPED"


def test_count_drift_fails_closed(tmp_path: Path) -> None:
    for name in ("hypotheses.csv", "proposition_feasibility.csv"):
        (tmp_path / name).write_bytes((REGISTRIES / name).read_bytes())

    rows = (tmp_path / "proposition_feasibility.csv").read_text(encoding="utf-8").splitlines()
    rows[1] = rows[1].replace(",B,", ",A,", 1)
    (tmp_path / "proposition_feasibility.csv").write_text(
        "\n".join(rows) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="authorised programme feasibility count drift"):
        load_programme_feasibility(tmp_path)

