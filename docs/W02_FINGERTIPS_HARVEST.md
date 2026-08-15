# W02 harvest: OHID Fingertips

**Run:** 2026-08-16, England, live.
**Script:** `scripts/harvest_fingertips_w02.py`. **Output:** `runtime/fingertips_w02.json`.

## What it did

15 searches → **135 distinct indicators**; 120 attempted → **81 series retrieved**, of which
**56 are usable as calibration targets** (complete, non-pooled, ≥3 points).

W02 — NHS referrals, diagnoses and service pathways — is required by 40 of the 64
propositions and was empty, because individual-level NHS data is access-gated behind
processes measured in months. It is no longer empty. Fingertips cannot supply
individual-level records, but the ascertainment propositions are claims about **rates**, and
rates are what this provides.

## The most useful series

| Indicator | ID | Points | Span | Basis |
|---|---|---|---|---|
| Access to IAPT services: people entering IAPT (in month) | 90592 | 78 | Apr 2013 – Sep 2019 | Financial |
| IAPT recovery: completed treatment | 90593 | 75 | Jul 2013 – Sep 2019 | Financial |
| IAPT DNAs: % of appointments | 91920 | 57 | Jan 2015 – Sep 2019 | Financial |
| People subject to the Mental Health Act, rate per 100,000 | 90413 | 24 | 2013/14 Q1 – 2019/20 Q2 | Financial |
| Urgent suspected cancer referrals | 91882 | 16 | 2009/10 – 2024/25 | Financial |
| Hospital admissions, unintentional and deliberate injury | 90285 | 15 | 2010/11 – 2024/25 | Financial |
| Emergency hospital admissions for intentional self-harm | 21001 | 14 | 2010/11 – 2023/24 | Financial |
| Hospital admissions for mental health conditions, under 18 | 90812 | 14 | 2010/11 – 2023/24 | Financial |
| Hospital admissions as a result of self-harm, 10–24 | 90813 | 13 | 2011/12 – 2023/24 | Financial |

90592 is a **monthly service-entry volume** — the closest openly published analogue to a
referral count, at 78 consecutive points.

## The comparator that matters most

The harvest returned **seven urgent-suspected-cancer referral series**, each 15–16 points
spanning 2009/10 to 2024/25. These are worth more than their subject suggests.

They are referral volumes from a clinical domain that shares **nothing** with gender
services except the referral system itself — the same GPs, the same two-week-wait
mechanics, the same period, the same recording infrastructure. That makes them a
**discriminating comparator** between two of the five model families:

- If referral volumes rose steeply across unrelated domains over the same period, then
  growth in any single domain is weak evidence for a domain-specific cause. That is
  ASCERTAINMENT_SERVICE's prediction — a change in the referral *system*, not in what is
  being referred.
- If the domain of interest diverges sharply from the general referral trend, the general
  trend cannot explain it, and INTRINSIC_RECOGNITION survives a test it could have failed.

This is a genuine falsification opportunity rather than a supporting illustration, and it
is available now with no access application. It should be prosecuted through
`mechanism_simulation.compare_mechanisms`, which is already built and already enforces the
right asymmetry: a compatible mechanism returns INCONCLUSIVE, never SUPPORTS.

**The test is not yet run and nothing here should be read as a result.** What is established
is that the comparator exists, is complete, and is long enough to be informative.

## What was refused, and why that is the connector working

39 of 120 indicators produced no series. Every refusal was deliberate:

| Reason | Count | What it means |
|---|---|---|
| published for several age bands | 25 | The connector refused to mix overlapping populations. Passing `age=` picks one. |
| no rows at area E92000001 | 13 | Not published at England level; available below it. |
| pooled window | (flagged, not skipped) | Rolling windows such as "2016/17 – 20/21" are not independent observations and are refused as calibration targets by default. |

Not one of these became a zero, an average, or a silently truncated series. The 25
age-band refusals are recoverable by naming a band; the 13 England-level absences are
recoverable by requesting a lower geography.

## Cautions carried forward

**Financial years.** Nearly every series is on a financial basis. "2020/21" is not 2020 and
must not be coerced. The metadata `YearType` is authoritative — the label alone cannot tell
you, and 41001 (suicide) is Calendar while 90813 is Financial.

**The IAPT series stop in Sep 2019.** That is a real end, not a harvest failure; the
collection changed. Any trend spanning it crosses a definitional break.

**Fingertips is a proxy, not the target.** These are service-contact and admission rates,
not gender-service referrals. They constrain and comparate; they do not substitute. The
direct figures remain the subject of the FOI request drafted at
`studies/foi_requests/nhs_gender_service_referrals.md`, which is free and carries a
20-working-day statutory deadline.
