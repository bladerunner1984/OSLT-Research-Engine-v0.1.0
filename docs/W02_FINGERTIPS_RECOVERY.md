# W02 recovery: the 39 Fingertips indicators the connector refused

**Run:** 2026-08-16, live, 197s wall clock at the standing 1 req/s throttle (~150 requests).
**Script:** `scripts/harvest_fingertips_recovery.py`. **Output:** `data/fingertips_w02_recovery.json` (0.6 MB).

## What it did

54 indicators attempted: the 39 the first harvest refused, plus the 15 it never reached
because of its 120-indicator cap. **429 series retrieved, 162 usable** as calibration
targets (complete, non-pooled, ≥3 points). Combined with the first harvest's 56, W02 now
holds **218 usable series**.

Nothing in `fingertips.py` was touched and no check was loosened. Every refusal in the
first run was the connector telling us the *question* was ambiguous; the recovery asked a
specific question instead — one series per (area, sex, age) stratum, pulled from the same
single CSV per indicator, never merged.

| Class | Indicators | Produced series | Produced ≥1 usable series |
|---|---|---|---|
| (a) "published for several age bands" | 22 | 22 | 20 |
| (b) "no rows at area E92000001" | 17 | 4 | 2 |
| (c) never attempted (the 120-cap remainder) | 15 | 15 | 5 |

**Correction to the first harvest doc.** `W02_FINGERTIPS_HARVEST.md` records the split as
25 age-band / 13 no-England-rows. The run's own `skipped_reasons` says **22 / 17**. The
totals agree (39); the split in that table is wrong. This run reads the ids from the JSON
rather than the prose.

## (a) Age bands — 22 attempted, 20 recovered

These are the valuable ones. Several propositions are about whether change is
*concentrated in particular age groups*, and a pooled "All ages" series cannot address that
at all. The bands are kept strictly separate; the "All ages" row is retained as its own
series and is **not** the sum of the bands published beside it. Never add these together.

The strongest new age-banded evidence, all England, all complete:

| Indicator | ID | Bands recovered | Points | Span | Basis |
|---|---|---|---|---|---|
| **New referrals to secondary mental health services, per 100,000** | 93623 | `<18`, `<25`, `25-64`, `65+`, `All ages` (+ M/F at `<18`) | 7 each | 2017/18 – 2023/24 | Financial |
| Attended contacts with community and outpatient mental health services | 93622 | same 9 strata | 7 each | 2017/18 – 2023/24 | Financial |
| Inpatient stays in secondary mental health services | 93624 | 7 strata incl. `<18`, `<25` | 7 each | 2017/18 – 2023/24 | Financial |
| Hospital admissions for drug-related mental/behavioural disorders | 94199 | `<16`, `16-24`, `25-34` … `75+` | 5 each | 2019/20 – 2023/24 | Financial |
| Hospital admissions where drug-related disorders were a factor | 94201 | same 11 bands | 5 each | 2019/20 – 2023/24 | Financial |
| School pupils with social, emotional and mental health needs | 91871 | Primary / Secondary / School age | 10 each | 2015/16 – 2024/25 | **Academic** |
| IAPT referrals, rate per 100,000 (quarterly) | 90747 | `18+` | 25 | 2013/14 Q2 – 2019/20 Q2 | Financial |
| Completion of IAPT treatment, rate per 100,000 (quarterly) | 90748 | `18+` | 25 | 2013/14 Q2 – 2019/20 Q2 | Financial |
| Hospital admissions for diabetes / epilepsy (under 19) | 92622 / 92623 | `0-9`, `10-18`, `0-18` × M/F/Persons | 12 each | 2013/14 – 2024/25 | Financial |
| % reporting depression or anxiety | 93376 | `18-24` … `85+` | 3 each | 2014/15 – 2016/17 | Financial |
| Odds ratio of reporting a mental health condition (MSK comparison) | 93742 | `16-24` … `85+` | 6 each | 2018 – 2023 | **Calendar** |

**93623 is the single most useful thing in this run.** It is a *referral count into
secondary mental health services*, split `<18` and `<25` against `25-64` and `65+`, seven
consecutive financial years to 2023/24 — the same mechanism, the same period and the same
recording infrastructure as the referrals the ascertainment propositions are actually
about, with the age contrast the propositions need. Paired with 93622 (contacts) and 93624
(inpatient stays) it separates *referral* volume from *treatment* volume, which is exactly
the distinction ASCERTAINMENT_SERVICE and INTRINSIC_RECOGNITION disagree about.

91871 (school SEMH needs, 10 academic years, primary vs secondary) is the longest
adolescent series recovered, and the only one on an **Academic** year basis in either
harvest. 92622/92623 (diabetes and epilepsy admissions in `0-9` and `10-18`, 12 years) are
paediatric admission comparators from domains with no plausible social-contagion story —
the same discriminating role the cancer-referral series play for adults.

Two age-band indicators produced series but none usable:

* **93581, 93582** (premature / excess under-75 mortality in adults with severe mental
  illness) — every point is a **pooled rolling window** ("2015 - 17"). 34 pooled series
  were retrieved across the run and are flagged `"pooled": true`. Consecutive points share
  underlying years; they are not independent observations and are not calibration targets.

Most remaining non-usable strata (233 of them) are simply short — one or two published
periods for a band, typically because the age breakdown was introduced in a single year
(90535 publishes `18+` for seven years but every finer band only for 2018/19). Short is
short; nothing was padded.

## (b) Not published at England level — 17 attempted, 2 recovered, 13 unrecoverable

Route: `available_area_types(indicator_id)` first, then pull at the **most aggregated
level the indicator is actually published at** (preference: England → region → ICB →
county/UTLA → district).

* **90776** (chlamydia detection rate per 100,000 aged 15-24) and **90777** (proportion of
  females 15-24 screened) — the England rows exist; the first harvest missed them because
  it asked for `sex=Persons` and these are published **Female only**. Enumerating the sex
  stratum recovered both: 14 points, 2012–2025, **Calendar** basis. 90776 is the only
  recovered 15–24 series spanning the whole period.
* **92275** (mental health detection at antenatal booking) — England, Female, `15-44 yrs`,
  but a **single period**. Retrieved, not usable.
* **93587** (estimated number of children and young people with mental disorders, 5-17) —
  published **only at area type 502** (lower-tier LA). 147 LA series were pulled from one
  CSV, so the volume cost nothing extra; but each has **one period, 2017/18**. They are
  reported as 147 LA-level one-point series. **They were not summed to an England figure**
  and must not be: LAs and regions nest, and naive summing is the error that once read
  Leeds as 2.86M against a true 715,609. A modelled prevalence *estimate* is doubly
  unsafe to add up.
* **2024, 2051, 2057, 2060, 2071, 2072, 2076, 2077, 2551, 2568, 2569, 2570, 2573 — 13
  indicators, unrecovered.** `available_data` lists them at area types 202 and 15, but
  *both* return an empty CSV, and `indicator_metadata` returns `{}` for all of them — no
  name, no `YearType`, nothing. They are stale entries in the search index for indicators
  that have been withdrawn: registered, discoverable, and carrying no data at any level.
  There is no stratum that makes the question answerable, so they are recorded as
  unrecovered rather than worked around.

## (c) The 15 never attempted

Run through the same path. 5 produced usable series — 94199 and 94201 (the drug-related
admission age ladders above), 93884/93886 (learning-disability employment, 7 points) and
94311 (less active children and young people, `5-16`, 8 academic years). The other 10 are
single-period model-based prevalence estimates (94103, 94237, 94118) or pooled/short
series (93972 suicide by age and sex is entirely pooled three-year windows).

## Cautions carried forward

**"All ages" is a stratum, not a total to check the bands against.** The published bands
often do not exhaust the population and are not required to sum to it. The file keeps them
side by side because they are separate published series, not because they reconcile.

**Three year bases now in play.** Financial (most), Calendar (90776, 93742) and
**Academic** (91871, 94311). `YearType` from metadata decides it; the labels are preserved
verbatim and never coerced.

**Pooled windows.** 34 series are flagged pooled. `observed()` refuses them unless
`allow_pooled=True` is passed deliberately, and nothing here should pass it without the
calibration explicitly modelling the overlap.

**No hole became a zero.** Zero series in this run carry missing periods — the strata that
would have had holes are absent from the published CSV entirely rather than suppressed,
and short strata are recorded as short.

**Still a proxy.** 93623 is a referral count into secondary mental health services, not
into gender services. It constrains and comparates; it does not substitute. The direct
figures remain the subject of the FOI request at
`studies/foi_requests/nhs_gender_service_referrals.md`.
