"""Negative controls for the referral-growth comparators.

The first two comparators (docs/REFERRAL_BASELINE.md) show that adolescent-concentrated,
female-skewed referral growth is not unique to gender services. That has an obvious rival
reading: adolescent mental health genuinely deteriorated, so the "background" is itself a
real signal rather than a threshold or ascertainment artefact.

A negative control discriminates. Two are used here:

  92622 / 92623  Paediatric diabetes and epilepsy admissions, 0-9 and 10-18, by sex,
                 twelve financial years. Type 1 diabetes and epilepsy are ascertained on
                 objective criteria; a child in ketoacidosis or status epilepticus is
                 admitted whatever the cultural climate. If these ALSO doubled in
                 under-18s with a female excess, the pattern is an artefact of the health
                 system, the population denominator or the recording, and the second
                 comparator means much less than it appears to.

  91871          School pupils with social, emotional and mental health (SEMH) needs, ten
                 ACADEMIC years. Outside the NHS entirely: different institution,
                 different professionals, different incentives, different recording
                 system. Tests whether the pattern is NHS-specific.

Descriptive only. No mechanism is calibrated here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SOURCE = Path("data/fingertips_w02_recovery.json")
OUTPUT = Path("data/negative_controls.json")

MIN_POINTS = 3

CONTROLS: dict[int, str] = {
    92622: "Hospital admissions for diabetes (under 19 years)",
    92623: "Hospital admissions for epilepsy (under 19 years)",
    91871: "School pupils with social, emotional and mental health needs",
}

#: Parent bands. "0-18 yrs" is the parent of 0-9 and 10-18; "School age" is the parent of
#: primary and secondary. They are reported separately and NEVER summed with their
#: children, and no two age bands are merged.
PARENT_BANDS = {"0-18 yrs", "School age"}


def index_not_trend(points: list[dict[str, Any]]) -> str | None:
    """Return an exclusion reason if the series is an index rather than a time series.

    The 91344 failure: value 100.0 in all 15 periods with count == denominator, an
    England-indexed standardisation ratio whose flat 1.00x ratio inverted the finding.
    """
    values = [p["value"] for p in points]
    if any(v is None for v in values):
        return "missing value present"
    if len(set(values)) == 1:
        return f"constant value {values[0]} in all {len(values)} periods - index, not trend"
    paired = [
        p for p in points
        if p["count"] is not None and p["denominator"] is not None
    ]
    if paired and len(paired) == len(points) and all(
        p["count"] == p["denominator"] for p in paired
    ):
        return "count == denominator in every period - index, not trend"
    return None


def describe(points: list[dict[str, Any]]) -> dict[str, Any]:
    first, last = points[0], points[-1]
    steps = len(points) - 1
    ratio = last["value"] / first["value"]
    count_ratio = (
        last["count"] / first["count"]
        if first["count"] not in (None, 0) and last["count"] is not None
        else None
    )
    denom_ratio = (
        last["denominator"] / first["denominator"]
        if first["denominator"] not in (None, 0) and last["denominator"] is not None
        else None
    )
    return {
        "first_period": first["period"],
        "last_period": last["period"],
        "n_periods": len(points),
        "first_value": first["value"],
        "last_value": last["value"],
        "ratio": ratio,
        "cagr": ratio ** (1 / steps) - 1,
        "min_value": min(p["value"] for p in points),
        "max_value": max(p["value"] for p in points),
        "count_ratio": count_ratio,
        "denominator_ratio": denom_ratio,
        "series_kind": (
            "rate or proportion with published denominator"
            if first["denominator"] is not None else "value only, denominator absent"
        ),
    }


def sex_ratio_trend(
    female: list[dict[str, Any]], male: list[dict[str, Any]]
) -> list[dict[str, Any]] | None:
    """F:M by period, exactly as REFERRAL_BASELINE.md computes it for 93623."""
    female_by_period = {p["period"]: p["value"] for p in female}
    male_by_period = {p["period"]: p["value"] for p in male}
    shared = [p["period"] for p in female if p["period"] in male_by_period]
    if len(shared) < MIN_POINTS:
        return None
    return [
        {
            "period": period,
            "female": female_by_period[period],
            "male": male_by_period[period],
            "f_to_m": female_by_period[period] / male_by_period[period],
        }
        for period in shared
    ]


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_id = {
        int(item["indicator_id"]): item
        for item in data["indicators"]
        if str(item["indicator_id"]).isdigit()
    }

    exclusions: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "source": str(SOURCE),
        "purpose": "negative controls for docs/REFERRAL_BASELINE.md comparators 1 and 2",
        "rules": [
            "complete, non-pooled series with >= 3 points only",
            "missing points are never filled; the series is skipped",
            "index-not-trend series excluded with a recorded reason",
            "age bands are never merged and nesting levels are never summed",
            "year bases are never aligned across indicators",
        ],
        "exclusions": exclusions,
        "indicators": {},
    }

    for indicator_id, name in CONTROLS.items():
        indicator = by_id[indicator_id]
        year_type = indicator["year_type"]
        block: dict[str, Any] = {
            "indicator_id": indicator_id,
            "name": name,
            "year_type": year_type,
            "year_basis_note": (
                "ACADEMIC years (2015/16 = a school year, Sep-Jul). Period boundaries do "
                "NOT coincide with the financial years used by 92622, 92623, 93623 or the "
                "cancer baseline."
                if year_type == "Academic" else
                "Financial years (2013/14 = 1 Apr 2013 to 31 Mar 2014)."
            ),
            "strata": {},
            "sex_ratio": {},
        }
        kept: dict[tuple[str, str], list[dict[str, Any]]] = {}

        for series in indicator["series"]:
            key = f"{series['age']} | {series['sex']}"
            if series["pooled"]:
                exclusions.append({
                    "indicator_id": indicator_id, "stratum": key,
                    "reason": "pooled rolling window - not independent observations",
                })
                continue
            if not series["complete"] or series["missing_periods"]:
                exclusions.append({
                    "indicator_id": indicator_id, "stratum": key,
                    "reason": f"incomplete: missing {series['missing_periods']}",
                })
                continue
            if series["n_points"] < MIN_POINTS:
                exclusions.append({
                    "indicator_id": indicator_id, "stratum": key,
                    "reason": f"only {series['n_points']} points, need {MIN_POINTS}",
                })
                continue
            reason = index_not_trend(series["points"])
            if reason is not None:
                exclusions.append({
                    "indicator_id": indicator_id, "stratum": key, "reason": reason,
                })
                continue
            block["strata"][key] = describe(series["points"]) | {
                "age": series["age"],
                "sex": series["sex"],
                "is_parent_band": series["age"] in PARENT_BANDS,
            }
            kept[(series["age"], series["sex"])] = series["points"]

        for age, sex in list(kept):
            if sex != "Female":
                continue
            male = kept.get((age, "Male"))
            if male is None:
                continue
            trend = sex_ratio_trend(kept[(age, "Female")], male)
            if trend is None:
                exclusions.append({
                    "indicator_id": indicator_id, "stratum": f"{age} | F:M",
                    "reason": f"fewer than {MIN_POINTS} periods with both sexes present",
                })
                continue
            block["sex_ratio"][age] = {
                "by_period": trend,
                "first_f_to_m": trend[0]["f_to_m"],
                "last_f_to_m": trend[-1]["f_to_m"],
                "female_ratio": trend[-1]["female"] / trend[0]["female"],
                "male_ratio": trend[-1]["male"] / trend[0]["male"],
            }

        report["indicators"][str(indicator_id)] = block

    report["pooled_excluded"] = sum(
        1 for e in exclusions if e["reason"].startswith("pooled")
    )
    report["index_not_trend_excluded"] = sum(
        1 for e in exclusions if "index, not trend" in e["reason"]
    )

    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    for indicator_id, block in report["indicators"].items():
        print(f"\n== {indicator_id} {block['name']} ({block['year_type']} years)")
        for key, stat in block["strata"].items():
            print(
                f"  {key:34s} {stat['first_period']}->{stat['last_period']} "
                f"{stat['first_value']:9.3f} -> {stat['last_value']:9.3f} "
                f"x{stat['ratio']:.3f}  CAGR {stat['cagr'] * 100:+.2f}%  "
                f"denom x{stat['denominator_ratio']:.3f}"
            )
        for age, sex_ratio in block["sex_ratio"].items():
            print(
                f"  F:M {age:22s} {sex_ratio['first_f_to_m']:.3f} -> "
                f"{sex_ratio['last_f_to_m']:.3f} "
                f"(F x{sex_ratio['female_ratio']:.3f}, M x{sex_ratio['male_ratio']:.3f})"
            )
    print(
        f"\nexclusions: {len(exclusions)} (pooled {report['pooled_excluded']}, "
        f"index-not-trend {report['index_not_trend_excluded']})"
    )
    for exclusion in exclusions:
        print(f"  {exclusion['indicator_id']} {exclusion['stratum']}: {exclusion['reason']}")


if __name__ == "__main__":
    main()
