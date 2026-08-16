# Background referral growth in England, 2009/10 – 2024/25

**Script:** `scripts/referral_baseline.py`. **Output:** `data/referral_baseline.json`.
**Source:** OHID Fingertips, retrieved live 2026-08-16. **Status:** descriptive, no
mechanism calibrated.

## Why this exists

Half of the comparator test set out in `W02_FINGERTIPS_HARVEST.md`. The other half — the
gender-service referral series — is not yet obtainable, being the subject of the FOI request
at `studies/foi_requests/nhs_gender_service_referrals.md` and of the MHSDS download recorded
in `SOURCE_ACCESS_NOTES.md`. This establishes the baseline **now**, so that when the target
series arrives the comparison is a single step and the baseline cannot be accused of having
been chosen after seeing it.

That ordering is the point. A comparator selected after the fact is not a comparator.

## The finding

Urgent suspected cancer referrals, England, rate per 100,000, and the proportion of those
referrals that found a cancer:

| Year | Referrals per 100k | Diagnostic yield |
|---|---|---|
| 2009/10 | 1,643.4 | 10.8% |
| 2011/12 | 1,977.7 | 10.0% |
| 2013/14 | 2,396.6 | 9.0% |
| 2015/16 | 2,975.1 | 7.8% |
| 2017/18 | 3,262.9 | 7.5% |
| 2019/20 | 3,895.6 | 6.6% |
| 2020/21 | 3,389.1 | 7.0% |
| 2021/22 | 4,322.5 | 6.2% |
| 2023/24 | 4,770.4 | 6.0% |
| 2024/25 | 4,899.2 | 6.0% |

- **Referral rate ×2.98** (CAGR +7.6%), population-adjusted — the denominator rises from
  54.8M to 63.8M over the window, so this is not population growth.
- **Diagnostic yield ×0.55** (CAGR −3.9%), declining **monotonically** in all but one year;
  2020/21 is the single reversal and is the COVID year, where referrals fell.
- **Absolute referrals ×3.47** (899,938 → 3,123,758) while **cancers found ×1.92**
  (97,462 → 186,799).

By tumour site: skin ×4.12, lower GI ×3.02, breast ×2.43, lung ×1.67.

## What it means, stated conservatively

Referral volumes into a specialist clinical pathway rose roughly threefold in fifteen years
while the proportion of referrals that found the condition nearly halved, monotonically.
That is the arithmetic signature of a **lowered referral threshold**: more people referred,
a smaller share of them having the thing referred for. Cases found did rise — real disease
was detected — but far more slowly than referrals.

This document makes no claim about what caused it. Successive NICE guideline revisions and
awareness campaigns over the same period are widely described in the clinical literature as
having been intended to lower the referral threshold, and a reader may find that a natural
reading — but this analysis calibrated no mechanism and cannot adjudicate it. What is
recorded here is the arithmetic, and what the arithmetic implies for **method**.

## Why it matters to this project

The claim it constrains is of this form:

> Referrals to service X rose N-fold over period P; therefore something changed about the
> population X serves.

That inference requires the background referral rate to have been stable. **In England,
between 2009/10 and 2024/25, it was not.** A domain sharing nothing with gender services
except the referral system itself — the same GPs, the same commissioning, the same recording
infrastructure, the same fifteen years — tripled.

So a threefold rise in any English specialist referral series over this window is, on its
own, **unremarkable**. It is roughly what the system did generally. Establishing that a
domain-specific cause is needed requires showing the domain of interest departs from this
baseline, not merely that it rose.

This bears on the ballot between model families:

- **ASCERTAINMENT_SERVICE** is specified such that referral growth with falling yield, and
  appearing across domains, would be consistent with it. The baseline does not discriminate:
  compatibility is not support, and this family has not been run against a target series.
- **INTRINSIC_RECOGNITION** is specified such that it would require the domain of interest
  to diverge from the general trend. The baseline cannot supply that margin either way.

Neither statement above is a result. Both describe what the model families are *specified*
to entail, not what the data shows — the distinction matters because a reader skimming for
conclusions will otherwise take the first bullet as support for a family this document has
not tested.

**Neither is tested here, and nothing above is a result about gender services.** Per the
engine's own rule in `compare_mechanisms`, compatibility is not support, and no mechanism has
been run. What has been established is the denominator for a comparison, not the comparison.

## The trap this run caught

Indicator **91344**, "Urgent suspected cancer referrals (indirectly age-gender
standardised)", carries a value of exactly 100.0 in every one of its 15 periods, with
`count == denominator` throughout. It is an **England-indexed standardisation ratio, not a
time series** — England compared against itself is 100 by construction.

Its first-to-last ratio is therefore 1.00. Read naively alongside the others it says
"referrals did not change", which **inverts the finding**. It is excluded by id in the
script with the reason recorded inline.

This is the sixth confirmed case in this project of a field meaning something other than it
appears, and the first where the misreading would have reversed a conclusion rather than
merely degrading it.

## Limits

- Cancer referrals are a comparator, not a control. The two domains share a referral system;
  they do not share a case definition, a guideline history, or a public awareness campaign
  schedule. This bounds how much weight the comparison can carry, and it should be reported
  alongside any use of it.
- One comparator domain is weak. Before the comparison is run, at least one further
  unrelated referral series should be added — the IAPT access series (90592, 78 monthly
  points) is the obvious second, and it is already harvested.
- The window ends 2024/25 and begins 2009/10; a gender-service series covering a different
  window is not directly comparable and must be aligned or the overlap restricted.
- Financial years throughout. "2009/10" is not 2009.

---

# Second comparator: secondary mental health referrals by age, 2017/18 – 2023/24

> ## ⚠️ SEVERELY CONFOUNDED — added 2026-08-16, read before anything below
>
> **This comparator is very likely a coverage artefact and should not be relied on.**
>
> Fingertips indicator 93623 declares its source as *"OHID, based on NHS England and Office
> for National Statistics data"*. NHS England's mental health referral collection is the
> **Mental Health Services Data Set (MHSDS)**, now downloaded and read directly. MHSDS
> provider participation was incomplete in the early years and grew steadily:
>
> | Financial year | Providers submitting to MHSDS |
> |---|---|
> | 2016/17 | 94 |
> | **2017/18** | **103** |
> | 2018/19 | 137 |
> | 2019/20 | 243 |
> | 2020/21 | 300 |
> | 2021/22 | 334 |
> | 2022/23 | 372 |
> | **2023/24** | **389** |
>
> Across the exact window used below, **submitting providers rose ×3.76 while the referral
> rate rose ×2.02.** The ascertainment ramp is nearly twice the apparent trend.
>
> **What this does to the finding.** The under-18 rise, the monotonic age gradient and the
> emerging female excess are all consistent with a growing share of activity simply becoming
> *visible* to the collection, rather than with any change in referral behaviour. If the
> providers joining later were disproportionately children and young people's services — which
> is plausible and has not been checked — that would inflate the under-18 band specifically,
> which is precisely the stratum the argument rested on.
>
> **The claim built on this comparator is withdrawn.** The section below argued that
> adolescent-concentrated, female-predominant referral growth is not domain-specific. That
> argument is not currently supported, because the comparator itself may not describe a real
> rise. It is retained unaltered for the record and because the *method* remains right — but
> the conclusion does not stand on this evidence.
>
> **What would settle it.** A coverage-adjusted series: restrict to providers submitting
> continuously across the whole window, or model participation explicitly. MHSDS supports
> this and it has not been done. Until then, treat every figure below as an upper bound on a
> real change and quite possibly as no change at all.
>
> The cancer comparator is **unaffected** — it comes from a separate, mature collection with
> no comparable participation ramp — and the diabetes and epilepsy negative controls are
> likewise unaffected, being hospital admissions rather than MHSDS submissions.


Added because one comparator domain is weak, and because cancer — while sharing the referral
system — is remote from the target in every other respect. This one is not.

**Source:** OHID Fingertips indicator 93623, "New referrals to secondary mental health
services", rate per 100,000, England, seven complete financial years. Recovered by naming an
age band; see `W02_FINGERTIPS_RECOVERY.md`.

## The age gradient

| Stratum | 2017/18 | 2023/24 | Ratio |
|---|---|---|---|
| Under 18 | 4,849.4 | 9,817.8 | **×2.02** |
| Under 25 | 6,047.9 | 10,584.0 | ×1.75 |
| All ages | 5,947.5 | 8,602.0 | ×1.45 |
| 25–64 | 5,528.5 | 7,981.9 | ×1.44 |
| 65+ | 6,944.9 | 7,492.2 | ×1.08 |

Growth falls monotonically with age. Under-18 referrals doubled in six years while referrals
for the over-65s barely moved.

## The sex ratio, under 18

| Year | Female | Male | F:M |
|---|---|---|---|
| 2017/18 | 5,017.6 | 4,659.8 | 1.077 |
| 2018/19 | 6,296.8 | 5,614.5 | 1.122 |
| 2019/20 | 7,431.5 | 6,083.7 | 1.222 |
| 2020/21 | 7,687.6 | 5,307.4 | 1.448 |
| 2021/22 | 11,034.4 | 7,093.3 | 1.556 |
| 2022/23 | 11,096.9 | 7,731.0 | 1.435 |
| 2023/24 | 11,015.2 | 8,338.7 | 1.321 |

Female ×2.20 against male ×1.79. The sex ratio rises from near parity to a female excess,
peaking in 2021/22 and easing since.

## Why this is the more demanding comparator

The most frequently cited feature of gender-service referral data is that growth was **rapid,
concentrated in adolescents, and disproportionately in natal females**. That conjunction is
routinely treated as the signature requiring a domain-specific explanation.

**The same conjunction is present in general secondary mental health referrals over the same
period, in a service with no relation to gender identity.** Growth concentrated in
under-18s; a female excess emerging within the adolescent band; both developing across the
same six years.

This does not explain the gender-service pattern and does not refute any account of it.
What it does is remove the conjunction's status as self-evidently domain-specific. An
argument that runs "adolescent, female-predominant, rapid growth — therefore a cause peculiar
to this domain" now has to explain why the same shape appears in a domain where that cause
does not apply. That is a higher bar than the argument has usually been asked to clear, and
it applies symmetrically: accounts appealing to social transmission within the domain face
it too, because this comparator is outside the domain.

## What it cannot support

- **Seven years, not fifteen.** The window is 2017/18–2023/24 and does not reach back to the
  period over which gender-service referrals are usually described as having risen. Any
  comparison must be restricted to the overlap.
- **It contains the pandemic.** The sharpest movement in both the age gradient and the sex
  ratio falls in 2020/21 and 2021/22. Adolescent mental health referral patterns changed
  markedly then for reasons no one disputes. Neither series is clean of it, and a comparison
  that ignores this will mistake a shared shock for a shared mechanism.
- **Referrals, not diagnoses or need.** A referral is an act by a clinician within a service
  whose capacity, thresholds and guidance all changed over the window.
- **Rates, not individuals.** Nothing here identifies whether the same young people appear in
  both series; that requires linked individual-level data, which remains access-gated.
- **No mechanism has been run.** As with the cancer baseline, this is the denominator for a
  comparison, not the comparison, and per `compare_mechanisms` compatibility is never support.

## Standing note on the two comparators together

Cancer supplies length (16 years) and independence from anything psychosocial. Mental health
supplies proximity — the same population, the same age structure, plausibly overlapping
young people — but only seven years and a pandemic through the middle. They fail in
different directions, which is why both are kept. A single comparator would have been
mistaken for a control.

Two further comparators worth adding before the comparison is run: **92622 and 92623**,
paediatric diabetes and epilepsy admissions by 0–9 and 10–18 over twelve years, which no
social-transmission account is specified to affect at all, and **91871**, school SEMH needs
across ten academic years, the longest adolescent series available.

---

# Third comparator class: negative controls, 2013/14 – 2024/25 and 2015/16 – 2024/25

**Script:** `scripts/negative_controls.py`. **Output:** `data/negative_controls.json`.
**Source:** OHID Fingertips, already harvested in `data/fingertips_w02_recovery.json`.
**Status:** descriptive, no mechanism calibrated.

## Why this exists

The two comparators above establish that adolescent-concentrated, female-skewed referral
growth is not unique to gender services. That finding has one obvious rival reading, and it
is a good one:

> Adolescent mental health genuinely deteriorated over the period. The "background" is
> therefore itself a real signal, not a measurement or threshold artefact, and comparator 2
> shows only that the deterioration was broad.

Neither comparator can discriminate, because both are subjectively ascertained: a cancer
referral and a mental health referral are both acts of clinical judgement about a presenting
person. A negative control can. What is needed is a condition **objectively ascertained**,
where diagnosis does not depend on presentation, help-seeking or clinician threshold — and
a series recorded **outside the NHS altogether**.

- **92622, 92623** — paediatric diabetes and epilepsy admissions, 0–9 and 10–18, by sex,
  twelve financial years. Type 1 diabetes and epilepsy are diagnosed on objective criteria;
  a child in ketoacidosis or status epilepticus is admitted whatever the cultural climate.
  If these had also risen sharply in under-18s with a female excess, the pattern would be an
  artefact of the health system, the population denominator or the recording, and comparator
  2 would mean much less than it appears to.
- **91871** — school SEMH (social, emotional and mental health) needs, ten academic years.
  A different institution, different professionals, different incentives, a different
  recording system. Tests whether the pattern is NHS-specific.

## Diabetes admissions (92622), rate per 100,000, England

| Stratum | 2013/14 | 2024/25 | Ratio | CAGR | Population denominator |
|---|---|---|---|---|---|
| 10–18 Persons | 90.92 | 64.47 | **×0.71** | −3.1% | ×1.153 |
| 10–18 Female | 102.51 | 66.17 | ×0.65 | −3.9% | ×1.151 |
| 10–18 Male | 79.87 | 61.79 | ×0.77 | −2.3% | ×1.156 |
| 0–9 Persons | 28.63 | 28.76 | ×1.01 | +0.0% | ×0.983 |
| 0–9 Female | 28.30 | 29.87 | ×1.06 | +0.5% | ×0.984 |
| 0–9 Male | 28.95 | 27.65 | ×0.96 | −0.4% | ×0.983 |
| 0–18 Persons (parent band) | 57.11 | 46.51 | ×0.81 | −1.9% | ×1.061 |

## Epilepsy admissions (92623), rate per 100,000, England

| Stratum | 2013/14 | 2024/25 | Ratio | CAGR | Population denominator |
|---|---|---|---|---|---|
| 10–18 Persons | 58.53 | 61.72 | **×1.05** | +0.5% | ×1.153 |
| 10–18 Female | 61.00 | 53.80 | ×0.88 | −1.1% | ×1.151 |
| 10–18 Male | 56.17 | 68.22 | ×1.21 | +1.8% | ×1.156 |
| 0–9 Persons | 94.11 | 94.93 | ×1.01 | +0.1% | ×0.983 |
| 0–9 Female | 85.18 | 89.89 | ×1.06 | +0.5% | ×0.984 |
| 0–9 Male | 102.59 | 98.75 | ×0.96 | −0.4% | ×0.983 |
| 0–18 Persons (parent band) | 77.84 | 78.43 | ×1.01 | +0.1% | ×1.061 |

All rates, with published denominators. The under-18 population denominator itself rose
×1.06 over the window and the 10–18 band ×1.15, so a flat rate corresponds to a modestly
rising count. Counts are recorded in `data/negative_controls.json` (`count_ratio`) and do
not change the reading: diabetes admissions in 10–18s fell in rate and were roughly level in
count; epilepsy admissions in 10–18s rose ×1.22 in count against a ×1.15 denominator.

## The sex ratio in the negative controls, 10–18

Computed exactly as for 93623 above.

| Year | Diabetes F:M | Epilepsy F:M |
|---|---|---|
| 2013/14 | 1.283 | 1.086 |
| 2015/16 | 1.169 | 0.980 |
| 2017/18 | 1.139 | 0.975 |
| 2019/20 | 1.104 | 0.909 |
| 2020/21 | 0.980 | 0.906 |
| 2021/22 | 1.172 | 0.904 |
| 2022/23 | 1.121 | 0.828 |
| 2023/24 | 1.128 | 0.832 |
| 2024/25 | 1.071 | 0.789 |

**Both sex ratios move towards males, not females.** Diabetes 1.283 → 1.071, epilepsy
1.086 → 0.789. In 93623 the same statistic over an overlapping window moved from 1.077 to
1.321, having peaked at 1.556. The negative controls move the opposite way.

## School SEMH needs (91871), % of pupils, England, ACADEMIC years

| Stratum | 2015/16 | 2024/25 | Ratio | CAGR |
|---|---|---|---|---|
| Secondary school age, Persons | 2.36% | 4.29% | **×1.82** | +6.9% |
| School age, Persons (parent band) | 2.33% | 4.04% | ×1.73 | +6.3% |
| Primary school age, Persons | 2.08% | 3.55% | ×1.70 | +6.1% |

Sex split is published only from 2020/21 and only at the parent "School age" level:

| Academic year | Female | Male | F:M |
|---|---|---|---|
| 2020/21 | 1.632% | 3.909% | 0.418 |
| 2021/22 | 1.847% | 4.092% | 0.451 |
| 2022/23 | 2.100% | 4.400% | 0.477 |
| 2023/24 | 2.439% | 4.752% | 0.513 |
| 2024/25 | 2.811% | 5.223% | 0.538 |

Female ×1.72 against male ×1.34 across five academic years. SEMH identification remains
**male-predominant throughout** — roughly two boys per girl even at the end — but the female
share rises monotonically.

Primary-school and secondary-school sex splits exist for 2020/21 and 2024/25 only. Two
points is below the three-point floor and they are **excluded**, not interpolated. Four
strata were dropped for this reason and are listed in `exclusions` in the output.

## Which way the evidence came out

**The negative controls held. They do not undercut the second comparator.**

Diabetes and epilepsy admissions in under-18s did not double, did not rise sharply, and did
not develop a female excess. Over twelve years spanning the same period, diabetes admissions
in 10–18s **fell** ×0.71 and epilepsy admissions were essentially flat at ×1.05, both against
a 10–18 population denominator that grew ×1.15. Over an overlapping window, secondary mental
health referrals in under-18s rose ×2.02 in seven years. The sex ratios in the negative
controls moved **towards males**, in the opposite direction to 93623.

This eliminates a specific and serious rival explanation. If the growth in comparator 2 were
produced by the health system generally — more admissions, more coding, better data capture,
a rising or misspecified child denominator, a post-pandemic surge in all paediatric contact —
it would appear in these series too, because they run through the same hospitals, the same
coding, the same denominators and the same pandemic. It does not appear. The growth is
confined to conditions whose ascertainment runs through presentation, help-seeking and
clinician judgement.

**This is not the same as showing the growth is artefactual.** It narrows the field to two
survivors and does not choose between them:

- adolescent psychological distress genuinely rose, in a way that objectively ascertained
  paediatric conditions would not register; or
- the threshold, recognition and recording of that distress changed, as the cancer baseline
  above shows demonstrably happened in a different subjectively ascertained domain.

Both remain live. Nothing here separates them.

**The SEMH result cuts both ways and should not be reported as a clean confirmation.**
SEMH needs rose ×1.82 in secondary-age pupils across ten academic years, entirely outside
the NHS, with female growth outpacing male — a partial echo of the comparator-2 shape in a
system with different professionals, incentives and records. That the pattern crosses the
NHS boundary weakens any account that locates it in NHS referral behaviour specifically.
But SEMH identification is a school judgement about a presenting child, so it is **not** a
negative control: it belongs on the subjectively ascertained side, with the first two
comparators. It extends the reach of the pattern; it does not test it. It should be read as
a third comparator, not as a control.

## What it cannot support

- **Three different year bases.** Cancer and mental health are financial years; the SEMH
  series is on **academic** years. A 7-year financial series (93623, 2017/18–2023/24), a
  12-year financial series (92622/92623, 2013/14–2024/25) and a 10-year academic series
  (91871, 2015/16–2024/25) do **not** share period boundaries. "2020/21" denotes three
  different intervals across these tables. Nothing here aligns them and nothing downstream
  should.
- **Windows differ.** The negative controls start 2013/14 and comparator 2 starts 2017/18.
  The comparison above is between trends within each series over its own window, not between
  point-matched values across series.
- **Admissions, not incidence.** 92622 and 92623 count hospital admissions, which are
  objectively triggered but still mediated by service capacity and admission policy. A flat
  admission rate is not proof of flat disease incidence; it is evidence that the *recording
  and access* machinery did not itself inflate.
- **The 10–18 band is not the under-18 band.** 92622/92623 publish 0–9 and 10–18; 93623
  publishes <18. These are not the same denominator and are not merged anywhere in the
  script or in these tables. Parent bands (0–18, School age) are reported separately and are
  never summed with their children.
- **Five years of SEMH sex split, at the parent level only.** The F:M trend for 91871 rests
  on 2020/21–2024/25 at "School age". It cannot be attributed to secondary-age pupils
  specifically, because that split has only two published points.
- **No mechanism has been run.** As above, and per `compare_mechanisms`, compatibility is
  never support.

## Index-not-trend check

Every stratum was tested for the 91344 failure mode — a constant value across all periods, or
`count == denominator` in every period — before use. **No series in 92622, 92623 or 91871
failed it.** All three carry genuine denominators distinct from their counts and genuine
period-to-period variation. Four strata were excluded for having fewer than three points and
none for pooling: no series in these three indicators is a pooled rolling window. The tallies
are recorded as `index_not_trend_excluded` and `pooled_excluded` in the output.
