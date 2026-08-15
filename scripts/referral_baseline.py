"""Background referral growth in England, 2009/10-2024/25.

Half of the comparator test described in docs/W02_FINGERTIPS_HARVEST.md. The other
half - the gender-service referral series - is not yet obtainable, so this establishes
the baseline against which it will be read when it arrives.

Deliberately descriptive. No mechanism is calibrated here, because a mechanism run
against the comparator alone would answer a question nobody asked.
"""
from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path("data/fingertips_w02.json")

#: 91344 is "indirectly age-gender standardised" and its value is 100.0 in every one of
#: 15 periods, with count == denominator throughout. It is an England-indexed
#: standardisation ratio, not a time series. Reading its flat 1.00x as "referrals did not
#: change" would invert the finding, so it is excluded by id and the reason recorded.
INDEX_NOT_TREND = {91344}

VOLUME_ID = 91882   # Urgent suspected cancer referrals, rate per 100,000
YIELD_ID = 91845    # Referrals resulting in a diagnosis of cancer, %


def main() -> None:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    series = {item["indicator_id"]: item for item in data["series"]}

    volume, yield_ = series[VOLUME_ID], series[YIELD_ID]
    periods = [point["period"] for point in volume["points"]]
    assert periods == [point["period"] for point in yield_["points"]], "period misalignment"

    v0, v1 = volume["points"][0]["value"], volume["points"][-1]["value"]
    y0, y1 = yield_["points"][0]["value"], yield_["points"][-1]["value"]
    steps = len(periods) - 1

    referrals0 = volume["points"][0]["count"]
    referrals1 = volume["points"][-1]["count"]
    found0 = yield_["points"][0]["count"]
    found1 = yield_["points"][-1]["count"]

    monotonic_down = all(
        a["value"] >= b["value"]
        for a, b in zip(yield_["points"], yield_["points"][1:])
        if a["value"] is not None and b["value"] is not None
    )

    report = {
        "window": f"{periods[0]} to {periods[-1]}",
        "n_periods": len(periods),
        "referral_rate_per_100k": {"first": v0, "last": v1, "ratio": v1 / v0,
                                   "cagr": (v1 / v0) ** (1 / steps) - 1},
        "diagnostic_yield_pct": {"first": y0, "last": y1, "ratio": y1 / y0,
                                 "cagr": (y1 / y0) ** (1 / steps) - 1,
                                 "monotonic_decline": monotonic_down},
        "absolute_referrals": {"first": referrals0, "last": referrals1,
                               "ratio": referrals1 / referrals0},
        "cancers_diagnosed": {"first": found0, "last": found1, "ratio": found1 / found0},
        "excluded_as_index_not_trend": sorted(INDEX_NOT_TREND),
        "by_tumour_site": {
            item["indicator_id"]: {
                "name": item["indicator_name"],
                "ratio": item["points"][-1]["value"] / item["points"][0]["value"],
            }
            for item in data["series"]
            if "suspected" in item["indicator_name"].lower()
            and item["complete"] and not item["pooled"]
            and item["indicator_id"] not in INDEX_NOT_TREND
            and item["points"][0]["value"]
        },
    }
    out = Path("data/referral_baseline.json")
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
