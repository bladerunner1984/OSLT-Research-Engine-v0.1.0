# Census 2021 gender identity harvest (England and Wales)

**Run:** 2026-08-16, England and Wales, live, keyless.
**Script:** `scripts/harvest_census_gender_identity.py`.
**Output:** `runtime/census_2021_gender_identity.json`.
**Source:** NOMIS query API, via `oslt_research.connectors.nomis.NomisConnector`.

13 of the 24 gender identity tables pulled as 13 whole-table queries. **517 cells, zero
missing, zero refusals.**

---

## Read this before any figure below

Four caveats, in order of how badly each one gets ignored.

### 1. This is a cross-section. It cannot show a trend.

Census 2021 `date=2021` is the **census reference date, 21 March 2021**. It is not a
calendar year, not a mid-year estimate, and not comparable with one. **The gender identity
question was new in Census 2021**, so there is no prior measurement of the same thing by
the same instrument. Nothing here can establish that any quantity rose or fell, because
there is no second point. The age gradient below (1.00% at 16–24 falling to 0.22% at 75+)
is a **cross-sectional age pattern at one instant**. It is not a time series, and reading
it as one — as though today's 75-year-olds are yesterday's 20-year-olds measured earlier —
is the single most likely way these figures get misused. A cohort effect, a period effect
and a life-course effect all produce that same curve, and this table cannot separate them.

### 2. ONS has withdrawn accreditation from these statistics.

This is material and is recorded against the evidence here rather than discovered later.

- **8/13 November 2023** — ONS, *Quality of Census 2021 gender identity data*. ONS found
  patterns "consistent with some respondents not interpreting the question as we had
  intended" (ONS). Among people answering "different gender identity" with no write-in,
  around 13% did not speak English well, against roughly 2% of the cisgender population.
  ONS also said it "cannot say with certainty whether the census estimates are more likely
  to be an overestimate or an underestimate" (ONS).
- **9 October 2023** — Office for Statistics Regulation interim report opens a review.
- **12 September 2024** — OSR final report concludes the question "did not work as
  intended" (OSR). **Accreditation was removed.** The gender identity estimates are no
  longer accredited official statistics and are now classified as **official statistics in
  development**. ONS's own letter of the same date accepts there is "potential for bias in
  how the question was answered by those who did not speak English well" (Rourke, ONS).
- **26 March 2025** — ONS additional guidance on uncertainty and appropriate use: trans
  identification was **2.24%** among people whose main language was not English and who did
  not speak it well, against **0.42%** among English speakers. ONS states the figures
  "should not be used as precise estimates to support service delivery" (ONS), and suggests
  users consider excluding non-English speakers when comparing by geography, ethnicity or
  religion.
- **Sexual orientation was *not* downgraded** and remains accredited. The asymmetry matters:
  the two questions rode the same form, the same voluntariness and the same 16+ restriction,
  and only one of them failed review. That constrains which explanations of the failure are
  available — it is not a generic "sensitive question on a census" problem.
- No evidence was found that any RM-series table was withdrawn, corrected or reissued. What
  changed is the **status notice**, not the data.

**The ethnic-group cross-tab in this harvest independently reproduces the exact signature
ONS identified.** See below. That is a reason to distrust the geography- and
ethnicity-varying part of the estimate, not a reason to discard the table — the table is
now partly evidence *about the instrument*.

### 3. Voluntary, 16+, 6.0% non-response, and proxy answers.

The question was voluntary and asked only of usual residents **aged 16 and over**. In this
harvest **2,914,625 people did not answer — 6.00% of the 48,566,373 base**, matching ONS's
published 6.0%. Two denominators are therefore available and give different answers, and
this document states which is in use every time:

| Denominator | Value |
|---|---|
| All usual residents aged 16+ | 48,566,373 |
| Those who answered the question | 45,651,748 |

A census form can be completed by one household member on behalf of others. ONS warns that
"proxy responses for these sensitive topics may be less accurate than for other topics"
(ONS). Non-response is not random across the tables below: it runs 5.05% among White
British respondents and 9.95% in the Other ethnic group.

The "Aged 15 years and under" row returns **0 in every table**. That is a **structural
zero** — the question was not asked — not a measurement that nobody under 16 is trans.

### 4. Disclosure control means the totals disagree with each other.

ONS applies **record swapping** and **cell perturbation** to Census 2021. The effect is
visible in this harvest: the same England and Wales 16+ population reads **48,566,373**
(TS070), **48,566,372** (TS078, RM036, RM038), **48,566,371** (RM035) and **48,566,374**
(RM174, RM039). Those are the same number, perturbed independently per table. Consequences:

- Cells do not reconcile exactly across tables and are not meant to.
- Small cells are the perturbed ones. Precision beyond three significant figures is not
  real, and the smallest cells here (White Irish, 2,533) carry the most of it.
- **A suppressed or non-normal cell is missing, never zero.** `obs_status` is carried into
  the JSON for every cell. None were non-normal in this run.

---

## What was NOT summed, and why the JSON says so

Every codelist NOMIS serves for these tables contains **its own total, code `0`, sitting
beside the parts that make it up**. Two carry a *second* aggregate as well:
`c2021_disability_4` code **1001** ("Disabled under the Equality Act") is codes 1 + 2, and
`c2021_eth_8` code **1001** ("White") is codes 4 + 5 + 6. Summing either codelist
double-counts millions of people with no error raised.

The harvest therefore never sums. Each cell in the JSON records a `role` per axis
(`total` / `aggregate` / `component`) and a `cell_kind` (`grand_total` / `margin` /
`aggregate_cell` / `cross_cell`). **Every total quoted below is read from the published
total cell**, not derived.

One label collision is worth naming, because it silently changes a number by 2.7×:

> **"All other gender identities" means two different things.** In TS070's 8-category
> codelist it is **18,074** and excludes non-binary, which has its own row. In TS078 and
> every RM table's 7-category codelist it is **48,331** and *includes* non-binary
> (30,257 + 18,074 = 48,331). Same words, different populations. All cross-tabs below use
> the 7-category version, so "all other gender identities" there **includes non-binary**.

---

## The 24 datasets

`search="*gender identity*"` returned exactly 24. Harvested ones are marked.

| Table | NOMIS id | Title | Pulled |
|---|---|---|---|
| TS070 | NM_2087_1 | Gender identity (detailed) | ✅ |
| TS078 | NM_2061_1 | Gender identity | ✅ |
| RM035 | NM_2135_1 | by age | ✅ |
| RM036 | NM_2136_1 | by disability | ✅ |
| RM037 | NM_2137_1 | by economic activity status | ✅ |
| RM038 | NM_2138_1 | by ethnic group | ✅ |
| RM039 | NM_2139_1 | by general health | ✅ |
| RM040 | NM_2140_1 | by legal partnership status | — |
| RM041 | NM_2141_1 | by occupation | — |
| RM163 | NM_2263_1 | by age by sex | ✅ |
| RM164 | NM_2264_1 | by type of central heating in household | — |
| RM165 | NM_2265_1 | by dwelling type | — |
| RM166 | NM_2266_1 | by family composition | — |
| RM167 | NM_2267_1 | by highest qualification held | ✅ |
| RM168 | NM_2268_1 | by hours worked | — |
| RM169 | NM_2269_1 | by industry | — |
| RM170 | NM_2270_1 | by NS-SEC | — |
| RM171 | NM_2271_1 | by occupancy rating (bedrooms) | — |
| RM172 | NM_2272_1 | by occupancy rating (rooms) | — |
| RM173 | NM_2273_1 | by religion | ✅ |
| RM174 | NM_2274_1 | by sex | ✅ |
| RM175 | NM_2275_1 | by sexual orientation | ✅ |
| RM176 | NM_2276_1 | by tenure | — |
| RM191 | NM_2291_1 | by unpaid carer status | ✅ |

The eleven not pulled are housing, employment and household-structure tables. They are
reachable by the same script by adding the table code; none was refused.

---

## The headline (TS070, 8 categories)

Denominator: **all usual residents aged 16 and over**, England and Wales, 21 March 2021.

| Category | Count | % of all 16+ |
|---|---|---|
| **Total: all usual residents aged 16+** | **48,566,373** | 100% |
| Gender identity same as sex registered at birth | 45,389,635 | 93.46% |
| Gender identity different, no specific identity given | 117,775 | 0.24% |
| Trans woman | 47,572 | 0.10% |
| Trans man | 48,435 | 0.10% |
| Non-binary | 30,257 | 0.06% |
| All other gender identities | 18,074 | 0.04% |
| Not answered | 2,914,625 | 6.00% |

The **published** combined figure for "gender identity different from sex registered at
birth" is **262,113** — taken from the 4-category codelist in RM038 and RM163, not derived
by addition here. That is **0.54% of all 16+**, or **0.57% of those who answered**.

---

## Gender identity by age and sex (RM163)

Published "different from sex registered at birth", by age band, both sexes:

| Age | Base (16+) | Different | % of all | % of answered |
|---|---|---|---|---|
| 16–24 | 6,318,310 | 63,192 | 1.000% | 1.076% |
| 25–34 | 8,050,540 | 61,670 | 0.766% | 0.814% |
| 35–44 | 7,737,376 | 49,453 | 0.639% | 0.677% |
| 45–54 | 7,912,154 | 36,992 | 0.468% | 0.493% |
| 55–64 | 7,484,645 | 25,042 | 0.335% | 0.353% |
| 65–74 | 5,923,120 | 14,689 | 0.248% | 0.263% |
| 75+ | 5,140,224 | 11,075 | 0.215% | 0.235% |
| **All 16+** | **48,566,369** | **262,113** | **0.540%** | **0.574%** |

A **monotonic decline with age, roughly 4.6× from the youngest band to the oldest.** Not a
trend (see caveat 1).

Split by census sex, the youngest band is the only place the sexes diverge sharply:

| Age | Female % of answered | Male % of answered |
|---|---|---|
| 16–24 | **1.241%** | 0.913% |
| 25–34 | 0.786% | 0.843% |
| 35–44 | 0.623% | 0.734% |
| 45–54 | 0.425% | 0.563% |
| 55–64 | 0.322% | 0.385% |
| 65–74 | 0.244% | 0.284% |
| 75+ | 0.210% | 0.268% |
| **All 16+** | 0.555% | 0.595% |

**The female excess exists only at 16–24 and reverses at every older band.** Overall the
totals are near-identical (130,915 female, 131,198 male). This is the cross-tab with the
most discriminating shape in the harvest, and it is also the one most exposed to caveat 1:
an age-specific sex asymmetry at a single instant is compatible with a cohort effect, a
life-course effect and a period effect alike.

### A trap in the sex variable

`c_sex` here is the **census sex question**, not a verified record of sex registered at
birth. RM174 shows what that means: of 47,572 trans women, **31,471 are recorded as Female
and 16,101 as Male**; of 48,435 trans men, 32,697 are Male and 15,738 Female. Most
respondents answered the sex question as they identify. So "gender identity by sex" is
**gender identity by census sex response**, and the two are not independent measurements.
Any analysis treating `c_sex` as birth-registered sex is wrong for roughly two-thirds of
the trans respondents in this table.

---

## Disability (RM036) and general health (RM039)

This is the pair the task flagged as answering, at population scale and with nobody
identifiable, a question that otherwise needed individual-level exposure data behind an
ethics gate.

Disabled under the Equality Act (the 1001 aggregate), within each gender identity group:

| Group | Base | Disabled (EqA) | % | Limited a lot | % |
|---|---|---|---|---|---|
| Same as sex registered at birth | 45,389,635 | 9,028,276 | 19.89% | 3,819,185 | 8.41% |
| Different, no specific identity | 117,775 | 19,025 | 16.15% | 9,326 | 7.92% |
| Trans woman | 47,572 | 13,966 | **29.36%** | 6,170 | 12.97% |
| Trans man | 48,434 | 13,833 | **28.56%** | 5,982 | 12.35% |
| All other GI (incl. non-binary) | 48,331 | 26,721 | **55.29%** | 9,190 | 19.01% |
| Not answered | 2,914,625 | 646,748 | 22.19% | 327,786 | 11.25% |
| **All 16+** | 48,566,372 | 9,748,569 | 20.07% | 4,177,639 | 8.60% |

General health, categories reported **separately and never summed**:

| Group | Very good | Fair | Bad | Very bad |
|---|---|---|---|---|
| Same as sex registered at birth | 41.20% | 14.93% | 4.77% | 1.39% |
| Different, no specific identity | 42.42% | 13.46% | 5.43% | 2.19% |
| Trans woman | 34.98% | 18.37% | 6.76% | 2.22% |
| Trans man | 38.13% | 17.13% | 6.09% | 1.86% |
| All other GI (incl. non-binary) | 24.65% | 23.52% | 9.53% | 2.55% |
| Not answered | 36.18% | 18.28% | 6.21% | 2.17% |
| **All 16+** | 40.88% | 15.14% | 4.87% | 1.44% |

Three things worth stating plainly:

1. **The association is large and it is not age-adjusted.** Disability and bad health rise
   steeply with age, and the trans population here is much younger than the general
   population. An age-standardised comparison would move these numbers *further apart*, not
   closer, because the raw comparison flatters the older cisgender group. This harvest does
   not perform that standardisation; RM036 and RM039 do not carry an age axis. **RM163 has
   age but not disability, so a census-only age-standardised disability rate is not
   constructible from these tables.** That is a real limit, not an oversight.
2. **The "all other gender identities" row is the extreme on every measure** — 55.29%
   disabled, 24.65% in very good health. It is also the row that includes non-binary, is
   overwhelmingly young, and is the row nearest the write-in behaviour ONS found hardest to
   interpret. Treat it as the least stable row in the harvest.
3. The **"different, no specific identity given"** row is the anomaly: 16.15% disabled, the
   *lowest* of any group including cisgender respondents, while every other trans category
   is far above. That is the row ONS identified as most contaminated by respondents who did
   not understand the question. Its deviation from the other trans rows is consistent with
   it containing a substantial number of people who are not trans.

**This is an association in a cross-section.** At least three model families predict it and
this document does not adjudicate between them: a shared-vulnerability account, a
minority-stress account in which the association is downstream of treatment, and an
ascertainment account in which both variables partly index willingness to report a
non-standard answer on a form. Cell counts are large enough that sampling noise is not the
issue; the issue is that the data cannot order the arrows. That is what the mechanism
simulation is for.

---

## Sexual orientation (RM175)

| Group | Base | LGB+ | % of all | % of answered |
|---|---|---|---|---|
| Same as sex registered at birth | 45,389,635 | 1,403,216 | 3.09% | 3.19% |
| Different, no specific identity | 117,775 | 21,581 | 18.32% | 21.03% |
| Trans woman | 47,572 | 13,521 | 28.42% | 34.16% |
| Trans man | 48,435 | 13,137 | 27.12% | 32.35% |
| All other GI (incl. non-binary) | 48,331 | 40,552 | 83.90% | **91.61%** |
| **All 16+** | 48,566,373 | 1,536,614 | 3.16% | 3.42% |

Note the two questions share a non-response population: 2,199,328 people answered neither.
The 91.61% LGB+ share in the "all other gender identities" row is the strongest association
in the harvest and also the one most likely to be partly an artefact of who writes in a
non-standard answer to *any* identity question on a form.

---

## Ethnic group (RM038) — where the instrument shows its damage

| Ethnic group | Base | Different | % of answered | Not answered |
|---|---|---|---|---|
| Other ethnic group | 970,123 | 19,026 | **2.178%** | 9.95% |
| Black, Black British, Black Welsh, Caribbean or African | 1,812,794 | 29,035 | **1.749%** | 8.41% |
| White: Gypsy or Irish Traveller, Roma or Other White | 3,243,222 | 34,377 | **1.174%** | 9.69% |
| Asian, Asian British or Asian Welsh | 4,203,219 | 41,037 | 1.076% | 9.27% |
| Mixed or Multiple ethnic groups | 966,734 | 9,203 | 1.026% | 7.24% |
| White: Irish | 481,573 | 2,533 | 0.560% | 6.00% |
| White: English, Welsh, Scottish, N. Irish or British | 36,888,707 | 126,902 | **0.362%** | 5.05% |
| *White (AGGREGATE — contains the three rows above it)* | *40,613,502* | *163,812* | *0.427%* | *5.43%* |
| **All 16+** | 48,566,372 | 262,113 | 0.574% | 6.00% |

**A 6× spread, ordered almost exactly by likely English-language proficiency**, with
non-response tracking it in the same direction. This is the signature ONS itself identified
and which cost these statistics their accreditation. The "White: Gypsy or Irish Traveller,
Roma or Other White" category — which contains most recent European migration — sits at
1.174%, more than three times the White British rate, which is difficult to explain on any
substantive account and easy to explain on the measurement account.

**This table should not be read as evidence about ethnic variation in gender identity.** It
should be read as the best available public measurement of *how badly the instrument
misfired*, and as a reason to treat the national total of 262,113 as an upper bound with an
unquantified positive bias. ONS declined to say whether the overall figure is an over- or
under-estimate; this cross-tab is the reason that question is open.

---

## Which propositions this bears on

Named, not adjudicated.

- **Prevalence and denominator propositions.** This is the only national enumeration
  available: 262,113 of 48.57m aged 16+, with a documented upward measurement bias of
  unknown size and a 6.00% non-response floor. It sets a denominator, with a warning
  attached.
- **Age-structure propositions.** The 4.6× young/old gradient and the female-specific
  excess confined to 16–24 are the sharpest cross-sectional facts here — and the ones most
  vulnerable to being misread as a trend.
- **Co-occurring disability and health propositions.** Answered at population scale, without
  an ethics gate and without anyone identifiable. Not age-adjusted, and not adjustable from
  census tables alone.
- **Ascertainment and measurement-artefact propositions.** The ethnicity and non-response
  patterns are *direct evidence about the instrument*. For anything in the ascertainment
  family, the quality failure is not a caveat on the data — it is the data.
- **Overlap-with-sexual-orientation propositions.** RM175 gives the joint distribution
  nationally, which no sample survey in this project reaches.

---

## What raised, what was refused

**Nothing raised, and nothing was refused.** 13 of 13 tables returned complete, untruncated,
fully-pinned results; 517 cells, none missing, none non-normal.

That is worth stating precisely because it is not the connector being lenient. Each pull
named **every code of every selectable dimension explicitly** — the connector rejects an
unpinned dimension, and an unpinned dimension here would have mixed each codelist's own
total in with its parts. The four discovery constraints the connector enforces were all
load-bearing and all satisfied in advance:

- `dimension_keys()` supplied the real query keys (`c2021_genderid_8`, `c2021_age_9`,
  `c_sex`, `c2021_disability_4`, `c2021_health_7`, `c2021_sexor_4`, `c2021_eth_8`). None is
  guessable from its display name, and a wrong key returns HTTP 200 with zero rows.
- `dimension_values()` exposed the total at code `0` in all 13 tables and the second-level
  aggregates at code `1001` in two, before any data was requested.
- Whole-table cross-products are small (8 to 108 cells), so `header.truncated` never fired.
- Geography was pinned to the single England-and-Wales code, not to a level selector — the
  countries codelist contains overlapping nested areas.

Had any query raised, the correct response would have been to make the question more
specific, not to loosen the query. No such case arose.
