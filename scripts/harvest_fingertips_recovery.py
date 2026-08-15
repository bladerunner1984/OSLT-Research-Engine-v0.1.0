"""Recovery pass over the W02 Fingertips harvest.

`scripts/harvest_fingertips_w02.py` attempted 120 of 135 discovered indicators and got 81
series. The other 39 were *refused* by the connector, in two classes:

* 22 refused with "published for several age bands" - selecting without `age=` would have
  mixed overlapping populations (an "All ages" total sitting alongside its own parts).
* 17 refused with "no rows at area E92000001" - not published at England level, or
  published there only for a stratum other than the default (sex=Persons).

Neither refusal is loosened here. The recovery makes the question *specific* instead:
enumerate the strata the indicator actually publishes and pull one series per stratum,
keeping them separate. Age bands are never merged. Local-authority series are never summed
to make an England figure - regions and LAs nest, and naive summing is exactly the error
that once read Leeds as 2.86M against a true 715,609.

The 15 never-attempted indicators from the original discovery are run through the same path.

Output: data/fingertips_w02_recovery.json
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
from oslt_research.connectors.fingertips import (  # noqa: E402
    ENGLAND_AREA_TYPE_ID,
    FingertipsConnector,
    FingertipsError,
)

PRIOR = Path("data/fingertips_w02.json")
OUT = Path("data/fingertips_w02_recovery.json")

# Same search terms as the original run, so the discovered id set is the same 135.
TERMS = [
    "self-harm", "mental health", "children and young people mental health",
    "hospital admissions self-harm", "referral", "gender", "eating disorder",
    "autism", "learning disability", "depression", "anxiety", "suicide",
    "looked after children", "school readiness", "young people",
]
ORIGINAL_LIMIT = 120

# Most aggregated first. Fingertips area type ids: 15 England, 6 region, 221/202 county &
# UA / upper-tier LA, 501/502 current UTLA/LTLA, 401/402 district, 301/302 CCG/ICB style.
# The most aggregated level available is the one that needs no nesting arithmetic to read.
AREA_TYPE_PREFERENCE = (15, 6, 301, 302, 221, 202, 501, 502, 401, 402)

MAX_STRATA_PER_INDICATOR = 500  # guard on output volume, not on truth


def load_refusals() -> tuple[list[int], list[int]]:
    payload = json.loads(PRIOR.read_text(encoding="utf-8"))
    age_band, no_rows = [], []
    for reason in payload["skipped_reasons"]:
        match = re.search(r"indicator (\d+) is published for several age bands", reason)
        if match:
            age_band.append(int(match.group(1)))
            continue
        match = re.search(r"no rows for indicator (\d+) at area E92000001", reason)
        if match:
            no_rows.append(int(match.group(1)))
    return sorted(age_band), sorted(no_rows)


def discover(conn: FingertipsConnector) -> dict[int, list[str]]:
    found: dict[int, list[str]] = {}
    for term in TERMS:
        try:
            res = conn.search_indicators(term)
            ids: set[int] = set()
            for area_type, indicator_ids in res.items():
                if int(area_type) == ENGLAND_AREA_TYPE_ID:
                    ids.update(int(i) for i in indicator_ids)
            if not ids:
                for indicator_ids in res.values():
                    ids.update(int(i) for i in indicator_ids)
            for i in ids:
                found.setdefault(i, []).append(term)
            print(f"search {term!r:52} -> {len(ids)}", flush=True)
        except Exception as exc:  # a failed search must not look like "no indicators"
            print(f"search {term!r:52} FAILED {type(exc).__name__}: {exc}", flush=True)
    return found


def recover(conn: FingertipsConnector, indicator_id: int, klass: str) -> dict:
    """Enumerate the strata this indicator actually publishes, one series each."""

    record: dict = {
        "indicator_id": indicator_id,
        "recovery_class": klass,
        "series": [],
        "unrecovered_reason": None,
        "area_type_used": None,
        "available_area_types": [],
        "strata_found": 0,
        "strata_pulled": 0,
        "truncated": False,
    }
    # YearType from metadata is the only authoritative basis; labels cannot tell you.
    try:
        basis = conn.year_type(indicator_id)
    except Exception as exc:
        basis = "Unknown"
        print(f"  {indicator_id} metadata failed: {type(exc).__name__}: {exc}", flush=True)
    record["year_type"] = basis

    try:
        available = list(conn.available_area_types(indicator_id))
    except Exception as exc:
        record["unrecovered_reason"] = f"available_data failed: {type(exc).__name__}: {exc}"
        return record
    record["available_area_types"] = available

    order = [a for a in AREA_TYPE_PREFERENCE if a in available]
    order += [a for a in available if a not in order]
    rows: tuple = ()
    for area_type in order:
        try:
            rows = conn.observations(
                indicator_id=indicator_id,
                child_area_type_id=area_type,
                parent_area_type_id=ENGLAND_AREA_TYPE_ID,
                year_type=basis,
            )
        except Exception as exc:
            print(f"  {indicator_id} at area type {area_type}: "
                  f"{type(exc).__name__}: {exc}", flush=True)
            continue
        if rows:
            record["area_type_used"] = area_type
            break
    if not rows:
        record["unrecovered_reason"] = (
            "no rows returned at any area type the API lists as available "
            f"({available}); the indicator is registered but publishes no data"
        )
        return record

    # One stratum = one (area, sex, age). Category Type must stay blank: non-blank rows
    # are deprivation-decile partitions of the same people.
    strata = sorted({(r.area_code, r.sex, r.age) for r in rows if not r.category_type})
    record["strata_found"] = len(strata)
    if len(strata) > MAX_STRATA_PER_INDICATOR:
        strata = strata[:MAX_STRATA_PER_INDICATOR]
        record["truncated"] = True

    for area_code, sex, age in strata:
        try:
            series = conn.series(
                indicator_id=indicator_id,
                area_code=area_code,
                child_area_type_id=record["area_type_used"],
                parent_area_type_id=ENGLAND_AREA_TYPE_ID,
                sex=sex,
                age=age,
                year_type=basis,
                observations=rows,          # no extra request; re-selects the same CSV
            )
        except FingertipsError as exc:
            record["series"].append(
                {"area_code": area_code, "sex": sex, "age": age, "refused": str(exc)}
            )
            continue
        record["series"].append({
            "indicator_name": series.indicator_name,
            "area_code": series.area_code,
            "area_name": series.area_name,
            "area_type_id": record["area_type_used"],
            "sex": series.sex,
            "age": series.age,
            "year_type": basis,
            "pooled": series.pooled,
            "complete": series.complete,
            "n_points": len(series.observations),
            "missing_periods": list(series.missing_periods),
            "points": [
                {"period": o.period.label, "value": o.value, "count": o.count,
                 "denominator": o.denominator, "value_note": o.value_note}
                for o in series.observations
            ],
        })
    record["strata_pulled"] = len(record["series"])
    return record


def usable(entry: dict) -> bool:
    return bool(
        entry.get("complete") and not entry.get("pooled") and entry.get("n_points", 0) >= 3
    )


def main() -> int:
    started = time.time()
    conn = FingertipsConnector()  # 1 req/s throttle from the first request

    age_band_ids, no_rows_ids = load_refusals()
    print(f"refused in original run: {len(age_band_ids)} age-band, "
          f"{len(no_rows_ids)} no-England-rows", flush=True)

    found = discover(conn)
    ordered = sorted(found)
    never_attempted = ordered[ORIGINAL_LIMIT:]
    print(f"{len(found)} indicators discovered; {len(never_attempted)} never attempted",
          flush=True)

    work = (
        [(i, "age_bands") for i in age_band_ids]
        + [(i, "no_england_rows") for i in no_rows_ids]
        + [(i, "never_attempted") for i in never_attempted]
    )

    records = []
    for n, (indicator_id, klass) in enumerate(work, 1):
        rec = recover(conn, indicator_id, klass)
        rec["matched_terms"] = found.get(indicator_id, [])
        records.append(rec)
        good = [s for s in rec["series"] if usable(s)]
        name = next((s.get("indicator_name", "") for s in rec["series"]
                     if s.get("indicator_name")), "")
        tail = " UNRECOVERED" if rec["unrecovered_reason"] else ""
        print(f"[{n}/{len(work)}] {indicator_id} {klass:15} {name[:44]:44} "
              f"areatype={rec['area_type_used']} strata={rec['strata_found']} "
              f"usable={len(good)}{tail}", flush=True)

    all_series = [s for r in records for s in r["series"] if "points" in s]
    good_series = [s for s in all_series if usable(s)]
    by_class = {}
    for klass in ("age_bands", "no_england_rows", "never_attempted"):
        subset = [r for r in records if r["recovery_class"] == klass]
        by_class[klass] = {
            "indicators": len(subset),
            "recovered_usable": sum(1 for r in subset if any(usable(s) for s in r["series"])),
            "any_series": sum(1 for r in subset
                              if any("points" in s for s in r["series"])),
            "no_series_at_all": [r["indicator_id"] for r in subset
                                 if not any("points" in s for s in r["series"])],
        }

    payload = {
        "source": "OHID Fingertips",
        "run": "W02 recovery pass",
        "prior_output": str(PRIOR),
        "indicators_attempted": len(records),
        "series_retrieved": len(all_series),
        "series_usable_as_calibration_target": len(good_series),
        "by_class": by_class,
        "wall_clock_seconds": round(time.time() - started, 1),
        "indicators": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n=== {len(all_series)} series retrieved, {len(good_series)} usable "
          f"(complete, non-pooled, >=3 points) ===", flush=True)
    for klass, stats in by_class.items():
        print(f"  {klass:16} {stats['recovered_usable']}/{stats['indicators']} with usable "
              f"series; no series at all: {stats['no_series_at_all']}", flush=True)
    print(f"written to {OUT} in {payload['wall_clock_seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
