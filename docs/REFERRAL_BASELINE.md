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

This is not a claim about cancer policy, and it is not in dispute; it is the intended and
documented effect of successive NICE guideline revisions and awareness campaigns. It is
recorded here because of what it implies for **method**.

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

- **ASCERTAINMENT_SERVICE** predicts referral growth accompanied by falling yield or
  threshold-consistent shifts, and predicts it should appear across domains. The baseline
  is consistent with that mechanism operating in the English referral system generally.
- **INTRINSIC_RECOGNITION** requires the domain of interest to diverge from the general
  trend by a margin the baseline cannot supply.

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
social-transmission account predicts should move at all, and **91871**, school SEMH needs
across ten academic years, the longest adolescent series available.
