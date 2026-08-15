"""Live W02 harvest from Fingertips.

W02 (NHS referrals, diagnoses, service pathways) is required by 40 of 64 propositions
and is empty. This pulls every complete, non-pooled England series Fingertips will give
for the mental-health / self-harm / young-people cluster, which is the closest openly
published proxy for service contact.
"""
from __future__ import annotations
import json, sys, traceback
from pathlib import Path

sys.path.insert(0, "src")
from oslt_research.connectors.fingertips import (
    FingertipsConnector, FingertipsError, ENGLAND_AREA_TYPE_ID, ENGLAND_AREA_CODE,
)

TERMS = [
    "self-harm", "mental health", "children and young people mental health",
    "hospital admissions self-harm", "referral", "gender", "eating disorder",
    "autism", "learning disability", "depression", "anxiety", "suicide",
    "looked after children", "school readiness", "young people",
]

out = Path("runtime/fingertips_w02.json")
out.parent.mkdir(parents=True, exist_ok=True)

conn = FingertipsConnector()
found: dict[int, list[str]] = {}
for term in TERMS:
    try:
        res = conn.search_indicators(term)
        ids = set()
        for area_type, indicator_ids in res.items():
            if int(area_type) == ENGLAND_AREA_TYPE_ID:
                ids.update(int(i) for i in indicator_ids)
        if not ids:  # some indicators are published only below England
            for indicator_ids in res.values():
                ids.update(int(i) for i in indicator_ids)
        for i in ids:
            found.setdefault(i, []).append(term)
        print(f"search {term!r:52} -> {len(ids)} indicators", flush=True)
    except Exception as exc:
        print(f"search {term!r:52} FAILED {type(exc).__name__}: {exc}", flush=True)

print(f"\n{len(found)} distinct indicators across {len(TERMS)} searches", flush=True)

series_out = []
skipped: dict[str, int] = {}
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 120
for n, indicator_id in enumerate(sorted(found)[:LIMIT], 1):
    try:
        s = conn.series(
            indicator_id=indicator_id,
            area_code=ENGLAND_AREA_CODE,
            child_area_type_id=ENGLAND_AREA_TYPE_ID,
            parent_area_type_id=ENGLAND_AREA_TYPE_ID,
        )
    except FingertipsError as exc:
        reason = str(exc).split("(")[0].strip()[:60]
        skipped[reason] = skipped.get(reason, 0) + 1
        continue
    except Exception as exc:
        skipped[f"{type(exc).__name__}"] = skipped.get(type(exc).__name__, 0) + 1
        continue

    rec = {
        "indicator_id": indicator_id,
        "indicator_name": s.observations[0].indicator_name if s.observations else "",
        "matched_terms": found[indicator_id],
        "sex": s.observations[0].sex if s.observations else "",
        "age": s.observations[0].age if s.observations else "",
        "year_type": s.observations[0].period.year_type if s.observations else "",
        "pooled": s.pooled,
        "complete": s.complete,
        "n_points": len(s.observations),
        "missing_periods": list(s.missing_periods),
        "points": [
            {"period": o.period.label, "value": o.value,
             "count": o.count, "denominator": o.denominator,
             "value_note": o.value_note}
            for o in s.observations
        ],
    }
    series_out.append(rec)
    flag = "COMPLETE" if (s.complete and not s.pooled) else (
        "pooled" if s.pooled else f"holes={len(s.missing_periods)}")
    print(f"[{n}] {indicator_id} {rec['indicator_name'][:56]:56} "
          f"{rec['n_points']:>3}pts {flag}", flush=True)

usable = [r for r in series_out if r["complete"] and not r["pooled"] and r["n_points"] >= 3]
payload = {
    "source": "OHID Fingertips",
    "area": "England",
    "indicators_discovered": len(found),
    "series_retrieved": len(series_out),
    "series_usable_as_calibration_target": len(usable),
    "skipped_reasons": skipped,
    "series": series_out,
}
out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"\n=== retrieved {len(series_out)} series, {len(usable)} usable as calibration "
      f"targets (complete, non-pooled, >=3 points) ===", flush=True)
print("skipped:", skipped, flush=True)
print(f"written to {out}", flush=True)
