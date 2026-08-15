"""Live harvest of the Census 2021 gender identity tables for England and Wales.

Why this harvest exists: every other source reaching the population the 64 propositions
concern is a sample, a clinic series or a self-selected survey. Census 2021 is an
*enumeration* — it attempted to count everyone — and it asked a voluntary gender identity
question of usual residents aged 16 and over. The cross-tabulations (RM035-RM191) put that
answer beside age, sex registered at birth, disability, general health, sexual orientation
and ethnic group. The disability and health cross-tabs in particular answer a version of a
question that otherwise needed individual-level exposure data behind an ethics gate, and
they answer it with nobody identifiable.

Why it is written the way it is:

* **Nothing is summed.** Every dimension NOMIS serves here carries its own Total in the
  same codelist as the parts that make it up (code ``0``), and two of them carry a *second*
  intermediate aggregate as well (``c2021_disability_4`` code 1001 "Disabled under the
  Equality Act" is 1 + 2; ``c2021_eth_8`` code 1001 "White" is 4 + 5 + 6). Adding a codelist
  up would double- or triple-count. Each cell is therefore emitted with its role recorded —
  ``total``, ``aggregate`` or ``component`` — and totals are read from the published total
  cell rather than derived.
* **Every dimension is pinned explicitly**, by naming every code, because an omitted
  dimension defaults to all codes silently and the connector refuses that.
* **A refusal is not routed around.** If the connector raises, the query was ambiguous or
  the response was mutilated; the failure is recorded in the output and the query is not
  loosened to make it pass.
* **A suppressed cell stays missing.** ``obs_status`` is carried through; the connector
  already converts any non-normal status to ``None``, and this script never fills it.

Output: ``runtime/census_2021_gender_identity.json``. Findings:
``docs/CENSUS_2021_GENDER_IDENTITY.md``.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

sys.path.insert(0, "src")

from oslt_research.connectors.nomis import (  # noqa: E402
    CENSUS_GENDER_IDENTITY_DATASETS,
    GEOGRAPHY_ENGLAND_AND_WALES,
    MEASURE_VALUE,
    NomisConnector,
    NomisError,
)

#: Census 2021 has exactly one date code. It is the census reference date, 21 March 2021 —
#: a single cross-section, not a year and not a series. There is no neighbouring point.
CENSUS_DATE = "2021"

#: Code 0 is the Total in every gender identity, age, sex, disability, health, sexual
#: orientation and ethnic group codelist NOMIS serves for these tables.
TOTAL_CODE = "0"

#: NOMIS uses 1001+ for intermediate aggregates that sit beside their own parts in the same
#: flat codelist: "Disabled under the Equality Act" (= limited a lot + limited a little) and
#: "White" (= British + Irish + Gypsy/Traveller/Roma/Other White). Summing a codelist that
#: contains one of these counts those people twice.
AGGREGATE_CODES = {"1001", "1002", "1003"}

#: Pulled in the priority order set by the research question. All are England and Wales at
#: the census reference date; each is one whole-table cross-product, which is a few hundred
#: cells at most, so one well-formed query per table rather than many small ones.
TABLES: tuple[str, ...] = (
    "TS070",  # headline, 8 detailed categories
    "RM035",  # by age
    "RM174",  # by sex registered at birth
    "RM163",  # by age by sex
    "RM036",  # by disability
    "RM039",  # by general health
    "RM175",  # by sexual orientation
    "RM038",  # by ethnic group
    "TS078",  # headline, 4 categories
)

#: Not in :data:`CENSUS_GENDER_IDENTITY_DATASETS`; ids read from the live dataset list.
#: Kept separate so nothing here is mistaken for a connector-verified constant.
EXTRA_DATASETS: dict[str, str] = {
    "RM037": "NM_2137_1",  # by economic activity status
    "RM167": "NM_2267_1",  # by highest qualification held
    "RM173": "NM_2273_1",  # by religion
    "RM191": "NM_2291_1",  # by unpaid carer status
}


def code_role(code: str) -> str:
    """Classify a code as ``total``, ``aggregate`` or ``component``.

    This is the whole defence against the overlapping-aggregate trap. A consumer of the
    output cannot tell from a description alone that "White" and "White: Irish" sit in one
    flat list and overlap; the role says so.
    """

    if code == TOTAL_CODE:
        return "total"
    if code in AGGREGATE_CODES:
        return "aggregate"
    return "component"


def harvest_table(
    connector: NomisConnector, table: str, dataset_id: str
) -> dict[str, Any]:
    """Pull one whole gender identity table for England and Wales as a single query.

    Every dimension is pinned by naming every one of its codes, so the selection is
    explicit rather than defaulted. The description-to-code map is built from the codelist
    first, because the data response returns descriptions and only descriptions, and
    matching cells back to codes by eye is exactly how a total gets treated as a category.
    """

    dimensions = connector.selectable_dimensions(dataset_id)
    codes: dict[str, list[tuple[str, str]]] = {}
    for dimension in dimensions:
        values = connector.dimension_values(dataset_id, dimension)
        codes[dimension] = [(item.value, item.description) for item in values]

    selection = {dim: ",".join(code for code, _ in pairs) for dim, pairs in codes.items()}
    observations = connector.observations(
        dataset_id,
        geography=GEOGRAPHY_ENGLAND_AND_WALES,
        dates=[CENSUS_DATE],
        dimensions=selection,
        measure=MEASURE_VALUE,
    )

    # Description -> (code, role) per dimension, so each returned cell can be labelled with
    # what it actually is rather than what it is called.
    lookup = {
        dimension: {desc: (code, code_role(code)) for code, desc in pairs}
        for dimension, pairs in codes.items()
    }

    cells: list[dict[str, Any]] = []
    for observation in observations:
        entry: dict[str, Any] = {
            "value": observation.value,
            "obs_status": observation.status,
            "missing": observation.missing,
        }
        roles: list[str] = []
        for dimension in dimensions:
            description = observation.dimensions.get(dimension, "")
            code, role = lookup[dimension].get(description, ("", "unknown"))
            entry[dimension] = {"code": code, "description": description, "role": role}
            roles.append(role)
        # A cell is a margin if ANY of its axes is a total, and a pure cross-tab cell only
        # if none is. Mixing the two in one list and summing it is the trap.
        entry["cell_kind"] = (
            "grand_total"
            if all(role == "total" for role in roles)
            else "margin"
            if "total" in roles
            else "aggregate_cell"
            if "aggregate" in roles
            else "cross_cell"
        )
        cells.append(entry)

    return {
        "table": table,
        "dataset_id": dataset_id,
        "geography": "England and Wales",
        "geography_code": GEOGRAPHY_ENGLAND_AND_WALES,
        "date_code": CENSUS_DATE,
        "date_meaning": "Census reference date 21 March 2021; a single cross-section",
        "measure": "value (count of usual residents)",
        "dimensions": list(dimensions),
        "dimension_codes": {
            dimension: [
                {"code": code, "description": desc, "role": code_role(code)}
                for code, desc in pairs
            ]
            for dimension, pairs in codes.items()
        },
        "cell_count": len(cells),
        "missing_cell_count": sum(1 for cell in cells if cell["missing"]),
        "cells": cells,
    }


def main() -> int:
    """Harvest every prioritised table, recording refusals rather than working around them."""

    connector = NomisConnector()
    catalogue = connector.list_datasets("*gender identity*")
    ids = {**CENSUS_GENDER_IDENTITY_DATASETS, **EXTRA_DATASETS}

    results: dict[str, Any] = {}
    refusals: dict[str, str] = {}
    for table in TABLES + tuple(EXTRA_DATASETS):
        dataset_id = ids[table]
        try:
            results[table] = harvest_table(connector, table, dataset_id)
            print(
                f"{table} {dataset_id}: {results[table]['cell_count']} cells "
                f"({results[table]['missing_cell_count']} missing)",
                flush=True,
            )
        except (NomisError, Exception) as exc:  # noqa: BLE001 - refusals are the record
            refusals[table] = f"{type(exc).__name__}: {exc}"
            print(f"{table} {dataset_id} REFUSED {type(exc).__name__}: {exc}", flush=True)
            traceback.print_exc()

    payload = {
        "source": "NOMIS (ONS) query API, keyless",
        "connector": "oslt_research.connectors.nomis.NomisConnector",
        "geography": "England and Wales",
        "reference_date": "2021-03-21",
        "caveat": (
            "Census 2021 is a single cross-section at the reference date. The gender "
            "identity question was NEW in 2021 and voluntary, asked only of usual "
            "residents aged 16 and over, so these counts cannot by themselves establish "
            "any trend: there is no comparable prior measurement. Disclosure control and "
            "record swapping are applied by ONS, so small cells are perturbed. A missing "
            "or non-normal cell is missing, never zero."
        ),
        "catalogue": [
            {
                "dataset_id": item.dataset_id,
                "table": item.census_table,
                "name": item.name,
                "harvested": item.census_table in results,
            }
            for item in sorted(catalogue, key=lambda entry: entry.name)
        ],
        "tables": results,
        "refusals": refusals,
    }

    out = Path("runtime/census_2021_gender_identity.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {out} ({len(results)} tables, {len(refusals)} refusals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
