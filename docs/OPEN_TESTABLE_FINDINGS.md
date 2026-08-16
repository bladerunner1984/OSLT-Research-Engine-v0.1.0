# Candidate findings for the sixteen open-testable propositions

**Run:** 2026-08-16. **Script:** `scripts/answer_open_testable.py`.
**Output:** `data/open_testable_findings.json`.
**Maximum claim tier reached anywhere below: DESCRIPTIVE_EVIDENCE_ONLY.**

**Nothing here is a released claim.** `governance/claim_release.py` declines every claim pending human review, and zero human-coded evidence lanes exist in this repository. These are CANDIDATE findings, produced by an engine, for an academic to adjudicate, reject or re-run. No line below has passed a human gate.

**The ballot is unequal and no tally over it means what it looks like.** Twelve of these sixteen propositions belong to ASCERTAINMENT_SERVICE and four to MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL. INTRINSIC_RECOGNITION, MIXTURE_HETEROGENEITY and NULL_OR_ALTERNATIVE have **zero** open-testable propositions between them. Producing twelve ascertainment findings and no rival findings is an artefact of what is cheap to measure from open sources, not a result about which family explains anything. A comparative support index computed over this set measures data access.

- `MODEL_FAMILIES_WITH_NO_OPEN_TESTABLE_PROPOSITION:INTRINSIC_RECOGNITION,MIXTURE_HETEROGENEITY,NULL_OR_ALTERNATIVE`
- `OPEN_TESTABLE_SET_DOMINATED_BY:ASCERTAINMENT_SERVICE:12/16`
- `COMPARATIVE_SUPPORT_OVER_AN_UNEQUAL_BALLOT_MEASURES_DATA_ACCESS_NOT_EXPLANATION`

## Tally, and why the tally is not the point

| Direction | Propositions |
|---|---|
| SUPPORTS | AS10, AS11 (2) |
| WEAKENS | AS06, AS08, AS09, TH07 (4) |
| INCONCLUSIVE | AS01, AS02, AS03, AS04, AS05, AS07, AS12, TH04, TH05, TH08 (10) |

Read the WEAKENS column first. It is the column carrying the kind of information this engine is licensed to produce: `compare_mechanisms` refutes mechanisms and stays silent among survivors, so a mechanism that could not reproduce a real series is genuinely disfavoured while one that could is merely compatible. The two SUPPORTS below attach to literal arithmetic claims - a denominator contributes; an instrument's response options change its estimate - and neither supports ASCERTAINMENT_SERVICE as an account of anything.

## Summary table

| ID | Family | Domain | Direction | Falsifier | One-line basis |
|---|---|---|---|---|---|
| **AS01** | AS | Referral threshold | **INCONCLUSIVE** | INCONCLUSIVE | W09 anchor months carry no larger a break in the fitted log-slope of the coverage-fixed series than any other month (permutation p=0.76), but 32 of 60 testable months carry an anchor, so the test has almost no power. |
| **AS02** | AS | Service capacity | **INCONCLUSIVE** | NOT_TESTED | Over 53 overlapping months the IAPT mean wait fell 31.5 to 20.2 days while access rose 15.2% to 18.3% of estimated need (levels r=-0.24), but month-to-month changes are unrelated (r=0.08). |
| **AS03** | AS | Coding change | **INCONCLUSIVE** | PARTIALLY_TRIGGERED | At the only documented definition-label change in the archive (2026-04, MHS01 renamed from 'People in contact with services' to 'People with an open referral with services'), a coverage-fixed provider cohort steps by x0.9996 - no discontinuity - while the England headline steps x1.0914. |
| **AS04** | AS | Disclosure | **INCONCLUSIVE** | NOT_TESTED | No disclosure or help-seeking indicator exists in any workstream in hand, so the prediction - that disclosure changes before referral without a corresponding shift in objective onset - has neither of its two terms. |
| **AS05** | AS | Awareness | **INCONCLUSIVE** | NOT_TESTED | The awareness predictor AS05 names - search volume, media attention, professional awareness - sits in W11, which is not one of AS05's required workstreams and has not been harvested. |
| **AS06** | AS | Case mix | **WEAKENS** | TRIGGERED | Age composition explains 1.4% of the log growth in the MHS32 referral rate between 2022/23 and 2024/25. Directly standardising to the 2022 England age structure moves the ratio from x1.1117 to x1.1100. |
| **AS07** | AS | Geographic access | **INCONCLUSIVE** | NOT_TESTED | MHSDS carries ICB and provider geography, but no workstream in hand carries distance-to-service or a need proxy, so an access gradient cannot be distinguished from a need gradient. |
| **AS08** | AS | Administrative completeness | **WEAKENS** | TRIGGERED | Restricted to the 71 providers submitting a usable MHS01 value in every one of the 84 months, the England open-referral series still rises x1.411 across 2017/18-2023/24, against x1.517 unrestricted, while submitting providers rose x4.32. The rise is not wholly a coverage artefact. |
| **AS09** | AS | Diagnostic substitution | **WEAKENS** | TRIGGERED | Across four QOF diagnostic categories on the same instrument over 10 common years, all four rose (x1.15 to x1.95) and 0 of 6 pairs of year-on-year changes are negatively correlated. No compensating pattern appears. |
| **AS10** | AS | Survey measurement | **SUPPORTS** | NOT_TRIGGERED | Within a single census, the same category read off a 7-category and an 8-category response list differs by x2.67 (18,074 against 48,331); the estimate varies 6-fold across ethnic groups in the order of English proficiency; and the Office for Statistics Regulation removed accreditation on 2024-09-12 because the question 'did not work as intended'. |
| **AS11** | AS | Historical denominator | **SUPPORTS** | NOT_TRIGGERED | England's population rose x1.0426 across 2017/18-2023/24 while the MHS01 raw count rose x1.511. The denominator contributes 10.1% of the log growth; 89.9% is a rise in the rate per head. |
| **AS12** | AS | Follow-up attrition | **INCONCLUSIVE** | NOT_TESTED | Persistence and detransition rates require follow-up of individuals. No workstream in hand carries a cohort, so there is no estimate for a missingness model to move. |
| **TH04** | TH | Policy embedding | **INCONCLUSIVE** | INCONCLUSIVE | Annual W09 document counts cross-correlate best at lag -2 (r=0.80), which is the practice layer leading the policy layer - but 72% of the policy peak in 2024 comes from one source's API, so the series measures archival depth as much as policy activity. |
| **TH05** | TH | Network effects | **INCONCLUSIVE** | NOT_TESTED | The institutional graph gives network structure, but there is no per-node adoption outcome and no baseline-similarity control, so centrality cannot be shown to predict anything. |
| **TH07** | TH | Structural coupling | **WEAKENS** | TRIGGERED | On an 824-entity, 1,286-relation graph at STRONG_IDENTIFIER, assessed against 29 Parliament-fixed dates, no date returned MD15_COUPLING_SUPPORTED and ten returned MX09_ISOLATED_PROCESSES_BETTER. Not one connected component mixes more than one relation type. |
| **TH08** | TH | Cultural displacement | **INCONCLUSIVE** | NOT_TESTED | Census 2021 gives a religion cross-tab at one instant. TH08 requires macro longitudinal or cross-jurisdiction models, and neither dimension exists in any workstream in hand. |

---

## AS01 - Referral threshold

> Changing referral thresholds contribute materially to observed referral growth.

**Direction: INCONCLUSIVE.** Falsifier: INCONCLUSIVE. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Policy/service changes create discontinuities in referral rates independent of prevalence measures.

**Registered falsifier.** Referral growth mirrors population prevalence with no threshold discontinuity.

**Finding.** W09 anchor months carry no larger a break in the fitted log-slope of the coverage-fixed series than any other month (permutation p=0.76), but 32 of 60 testable months carry an anchor, so the test has almost no power.

**Basis.** The 121 W09 anchors are undifferentiated: they include every dated NHS England, GOV.UK, NICE and professional-body document the harvest found, not the subset that changed a referral threshold. With anchors on 53% of testable months, 'anchor' and 'month' are nearly the same variable, so a null here is uninformative rather than negative. The cancer comparator does show the threshold signature - referrals x2.98 against conversion x0.55, monotonic - but in a different domain.

**Evidence used.**

- W09: data/w09_clinical_guidance.json, 121 distinct anchor dates 2013-2026
- W02: MHSDS MHS01 continuous-cohort monthly series (DS077)
- W02: docs/REFERRAL_BASELINE.md cancer referral and conversion series

**Limits.**

- Anchor density is the binding limit, not sample size.
- Selecting the threshold-relevant anchors requires human coding of the 121 documents. governance/claim_release.py records zero human-coded lanes, so the selection cannot be made inside this engine without inventing it.
- MHS01 is general secondary mental health and is not the target domain.

**What would settle it.** Human coding of the W09 anchors into 'changes a referral threshold' and 'does not', pre-registered before the series is looked at, then the same permutation test on the coded subset.

---

## AS02 - Service capacity

> Capacity/waiting-list/service configuration affects observed case counts.

**Direction: INCONCLUSIVE.** Falsifier: NOT_TESTED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Capacity expansions/restrictions alter recorded referrals or throughput.

**Registered falsifier.** No relationship to service capacity after denominator control.

**Finding.** Over 53 overlapping months the IAPT mean wait fell 31.5 to 20.2 days while access rose 15.2% to 18.3% of estimated need (levels r=-0.24), but month-to-month changes are unrelated (r=0.08).

**Basis.** The level relationship has the sign a capacity account predicts and the first-difference relationship is null. Compatibility is not support, and no design here separates capacity causing throughput from throughput causing waits or from a common trend.

**Evidence used.**

- W02: OHID Fingertips 92010 (mean wait to enter IAPT) and 90592 (access to IAPT), England, monthly

**Limits.**

- Waiting time is an OUTCOME of capacity and demand jointly, not a measure of capacity. Using it as a capacity proxy builds the simultaneity in.
- The overlap ends September 2019 and does not reach the period the MHSDS work covers.
- The mean-wait series has 1 hole(s) inside the overlap (Sep 2017 to Feb 2018). First differences are taken within contiguous runs only - a missing month is not a month of no change.
- IAPT is a self-referral service; its access dynamics are not those of a GP-gated specialist pathway.

**What would settle it.** A commissioned-capacity series - funded establishment, clinic count, contracted activity - which no required workstream carries, plus variation in it that is not itself a response to demand.

---

## AS03 - Coding change

> Diagnostic/coding changes create artefactual time trends.

**Direction: INCONCLUSIVE.** Falsifier: PARTIALLY_TRIGGERED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Trend discontinuities align with coding/definition changes.

**Registered falsifier.** Harmonised coding leaves trend unchanged.

**Finding.** At the only documented definition-label change in the archive (2026-04, MHS01 renamed from 'People in contact with services' to 'People with an open referral with services'), a coverage-fixed provider cohort steps by x0.9996 - no discontinuity - while the England headline steps x1.0914.

**Basis.** AS03 predicts that trend discontinuities align with coding or definition changes. At the one change available, the coverage-fixed series shows no step at all. But this is a single instance, and a change of LABEL is not demonstrably a change of SPECIFICATION, so the test has little power and the falsifier is recorded as only partially triggered.

**Evidence used.**

- W02: MHSDS MHS01 England and Provider cells with measure names carried per month (DS077); the rename was located by scanning the archive, not assumed

**Limits.**

- n=1. One label change, in one measure, in one collection.
- The England headline's step at the same month is NOT evidence of a definition effect: England and the cohort differ precisely by the providers outside the cohort, so that step is a joiner effect and is AS08's subject, not AS03's.
- Fifteen months either side, of which only three fall after the change; a step estimated on three months is fragile.
- ICD and OPCS coding revisions, which are what AS03 is really about, are not carried by any workstream in hand.

**What would settle it.** A dated register of coding and specification changes - MHSDS technical output specification versions, ICD-10 to ICD-11 transition dates - tested against coverage-fixed series. None of the four required workstreams carries one.

---

## AS04 - Disclosure

> Reduced stigma increases disclosure/help-seeking.

**Direction: INCONCLUSIVE.** Falsifier: NOT_TESTED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Disclosure indicators change before referral without corresponding objective symptom onset shift.

**Registered falsifier.** Onset measures rise similarly before disclosure changes.

**Finding.** No disclosure or help-seeking indicator exists in any workstream in hand, so the prediction - that disclosure changes before referral without a corresponding shift in objective onset - has neither of its two terms.

**Basis.** AS04 needs a disclosure measure and an onset measure, separately timed. W01, W02, W09 and W10 carry population, service activity, policy dates and parliamentary material. None is a disclosure indicator, and no onset measure exists outside individual-level records.

**Evidence used.**

- W01, W02, W09, W10 enumerated and searched; see data/feasibility_census.json

**Limits.**

- feasibility marks this OPEN_TESTABLE on required-workstream availability, but no required workstream carries the predictor the prediction names

**What would settle it.** A repeated population survey carrying both disclosure and onset items - primary collection, which is a different reachability class.

---

## AS05 - Awareness

> Public/professional awareness changes ascertainment.

**Direction: INCONCLUSIVE.** Falsifier: NOT_TESTED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Search/media/clinical awareness predicts presentation after service controls.

**Registered falsifier.** No independent association or reverse ordering.

**Finding.** The awareness predictor AS05 names - search volume, media attention, professional awareness - sits in W11, which is not one of AS05's required workstreams and has not been harvested.

**Basis.** AS05 requires W01, W02, W09 and W10, and predicts that search, media or clinical awareness predicts presentation after service controls. No required workstream carries an awareness measure. The GDELT connector (media_discourse.py) exists and is unharvested; even harvested it would supply an association, not the ordering AS05 needs.

**Evidence used.**

- registries/hypotheses.csv AS05 required_workstreams = W01;W02;W09;W10
- connectors/media_discourse.py present, no harvested output under data/

**Limits.**

- feasibility marks this OPEN_TESTABLE on required-workstream availability, but no required workstream carries the predictor the prediction names

**What would settle it.** Correcting the registry so AS05 requires W11, harvesting GDELT, and pre-registering the direction test - because a correlation between media attention and presentation is equally predicted by the rival families.

---

## AS06 - Case mix

> Changing case mix explains part of outcome change.

**Direction: WEAKENS.** Falsifier: TRIGGERED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Age/sex/psychiatric/neurodevelopmental composition shifts explain part of aggregate trend.

**Registered falsifier.** Standardisation/decomposition shows minimal contribution.

**Finding.** Age composition explains 1.4% of the log growth in the MHS32 referral rate between 2022/23 and 2024/25. Directly standardising to the 2022 England age structure moves the ratio from x1.1117 to x1.1100.

**Basis.** AS06's falsifier is 'standardisation/decomposition shows minimal contribution'. A contribution of this size is minimal on any reading. Every age band except 16-17 rose in rate; the growth is within bands, not between them.

**Evidence used.**

- W02: MHSDS MHS32 England; Age monthly cells, 2022-04 to 2026-06 (DS077)
- W01: NOMIS NM_2002_1 England population by age band, 2022 and 2024

**Limits.**

- AGE composition only. AS06 also names psychiatric and neurodevelopmental composition, and no required workstream carries either at England level. The verdict is about the one component that could be measured.
- Two financial years. MHS32 does not exist at England level before April 2022, so a longer window is not available.
- The UNKNOWN age band rose x10.8 between the two periods (5181 to 56160 referrals). It is excluded from the standardisation because a missing age is not an age band. That drift is itself a data-quality signal and it points, weakly, AS08's way.
- Six coarse bands, set by what the NOMIS codelist offers as a partition.

**What would settle it.** MHSDS carries no England-level psychiatric or neurodevelopmental co-occurrence breakdown. The rest of AS06 needs individual-level records, which is a different reachability class.

---

## AS07 - Geographic access

> Distance/provider distribution affects referral likelihood.

**Direction: INCONCLUSIVE.** Falsifier: NOT_TESTED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Natural variation in access predicts referral after need proxies.

**Registered falsifier.** No access gradient after adjustment.

**Finding.** MHSDS carries ICB and provider geography, but no workstream in hand carries distance-to-service or a need proxy, so an access gradient cannot be distinguished from a need gradient.

**Basis.** AS07 predicts that natural variation in access predicts referral AFTER need proxies. The geography exists; the need proxy does not. A raw between-area referral gradient computed without one would measure deprivation and case mix and be reported as access.

**Evidence used.**

- W02: MHSDS Provider, ICB and Sub-ICB breakdowns present in the archive
- W02: the Fingertips harvest is England-level only; no sub-national cross-section was retrieved

**Limits.**

- feasibility marks this OPEN_TESTABLE on required-workstream availability, but no required workstream carries the predictor the prediction names

**What would settle it.** Sub-national Fingertips extraction plus IMD and an independent need measure, with the access variation shown not to be itself a response to need.

---

## AS08 - Administrative completeness

> Submission/coverage changes in administrative datasets create apparent changes.

**Direction: WEAKENS.** Falsifier: TRIGGERED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Data-quality metadata explain discontinuities.

**Registered falsifier.** Trends persist in stable-coverage subsets and independent data.

**Finding.** Restricted to the 71 providers submitting a usable MHS01 value in every one of the 84 months, the England open-referral series still rises x1.411 across 2017/18-2023/24, against x1.517 unrestricted, while submitting providers rose x4.32. The rise is not wholly a coverage artefact.

**Basis.** 82.6% of the log growth survives restriction to a fixed provider cohort; 17.4% is attributable to changing coverage and composition. The COVERAGE_ONLY mechanism, which predicts a flat cohort-restricted series, was refuted by compare_mechanisms - no point in its declared grid reproduced the observed cohort series. AS08's own falsifier, 'trends persist in stable-coverage subsets', is triggered.

**Evidence used.**

- W02: MHSDS Apr-2016-Jun-2026 time-series archive, MHS01, Provider and England breakdowns (DS077), read locally, no network
- W02: docs/REFERRAL_BASELINE.md second-comparator withdrawal notice
- governance/mechanism_simulation.compare_mechanisms

**Limits.**

- MHS01 is a STOCK (people with an open referral at period end), not the referral FLOW the withdrawn comparator measured. MHS32, the flow measure, is only published at England level from April 2022 and cannot cover this window.
- The cohort is defined by continuous submission, which selects for organisational stability. Providers that merged, split or changed org code leave the cohort by construction, so the cohort is not a random sample and its growth need not equal true national growth.
- The cohort carries 92.2% of unrestricted activity in 2017/18 and 85.8% in 2023/24 - large, but a majority-not-all subset.
- Counts, not rates. The population correction is AS11's job and is small (see AS11), but it is not applied here.
- Refuting COVERAGE_ONLY disfavours that mechanism on this series. The surviving mechanism is COMPATIBLE and is not thereby supported.

**What would settle it.** The same restriction applied to a gender-service referral series. MHSDS carries no such measure - a full scan of all 121 England-level measures found none - so this remains a comparator result about secondary mental health, and the FOI request under studies/foi_requests/ is still the route to the target series.

---

## AS09 - Diagnostic substitution

> Changes reflect substitution/reclassification among diagnostic categories.

**Direction: WEAKENS.** Falsifier: TRIGGERED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Inverse or compensating trends appear across related categories.

**Registered falsifier.** No substitution pattern is observed.

**Finding.** Across four QOF diagnostic categories on the same instrument over 10 common years, all four rose (x1.15 to x1.95) and 0 of 6 pairs of year-on-year changes are negatively correlated. No compensating pattern appears.

**Basis.** AS09's falsifier is 'no substitution pattern is observed'. Substitution predicts that a category gains at another's expense; here every category gains and the year-on-year movements are weakly positively correlated throughout.

**Evidence used.**

- W02: OHID Fingertips indicators 200, 848, 90581, 90646 (QOF prevalence and incidence), England, data/fingertips_w02.json

**Limits.**

- Four QOF categories are not the diagnostic space. Substitution between, say, an autism code and a gender-related code would appear in none of them.
- QOF prevalence is a register count and is itself exposed to recording incentives; a common recording drift would produce exactly this pattern of everything rising together, which is an AS08-shaped confound on an AS09 test.
- Ten common annual points, so the correlations rest on nine differences.

**What would settle it.** Paired series for categories that plausibly substitute for one another, coded as such in advance. No workstream in hand carries a substitution map.

---

## AS10 - Survey measurement

> Survey wording/response options affect prevalence estimates.

**Direction: SUPPORTS.** Falsifier: NOT_TRIGGERED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Mode/wording experiments or harmonisation change prevalence estimates materially.

**Registered falsifier.** Estimates invariant to wording/mode.

**Finding.** Within a single census, the same category read off a 7-category and an 8-category response list differs by x2.67 (18,074 against 48,331); the estimate varies 6-fold across ethnic groups in the order of English proficiency; and the Office for Statistics Regulation removed accreditation on 2024-09-12 because the question 'did not work as intended'.

**Basis.** AS10's prediction is that wording, mode or harmonisation changes prevalence estimates materially. Here the response-option set alone changes one category by 167% with no change of respondent, question or date, and the national regulator has adjudicated the instrument as having failed. Its falsifier, 'estimates invariant to wording/mode', is decisively not met.

**Evidence used.**

- W01: ONS Census 2021 gender identity tables TS070, TS078, RM038, RM163, RM174, RM175 via NOMIS (517 cells, none missing, none non-normal)
- W09/W10: OSR final report 2024-09-12; ONS quality report November 2023; ONS additional guidance 2025-03-26

**Limits.**

- This is a measurement finding about a survey instrument. It says the census estimate is unreliable; it does NOT say the service-referral series is, and the two are separate collections.
- One cross-section. It cannot show change, so nothing here bears on any trend.
- The 6-fold ethnic spread is the ONS-identified signature, but this analysis did not harvest a language cross-tab (no language table was among the 13 pulled); the 2.24% / 0.42% figures are ONS's own, quoted.
- SUPPORTS attaches to AS10 as written - that survey wording and response options affect prevalence estimates. It is not support for ASCERTAINMENT_SERVICE as an account of service referrals.

**What would settle it.** A split-ballot or mode experiment on the same population. ONS has not run one; the 2021 census is a single-instrument enumeration, and the 2031 question design is the live decision this bears on.

---

## AS11 - Historical denominator

> Population denominator change contributes to raw-count growth.

**Direction: SUPPORTS.** Falsifier: NOT_TRIGGERED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Age/sex demographic standardisation attenuates raw growth.

**Registered falsifier.** Standardised rates remain unchanged.

**Finding.** England's population rose x1.0426 across 2017/18-2023/24 while the MHS01 raw count rose x1.511. The denominator contributes 10.1% of the log growth; 89.9% is a rise in the rate per head.

**Basis.** The proposition's literal claim - that population denominator change CONTRIBUTES to raw-count growth - is directly measurable arithmetic and the measured contribution is positive and non-zero. Its prediction, that standardisation attenuates raw growth, holds: x1.511 raw becomes x1.449 per head. Its falsifier, read as 'standardisation leaves the growth unchanged', is not triggered.

**Evidence used.**

- W01: NOMIS NM_2002_1 England mid-year population estimates 2016-2025, one pinned stratum per band, published total reconciled against the sum of the disjoint parts
- W02: MHSDS MHS01 England series (DS077)

**Limits.**

- SUPPORTS here attaches ONLY to the literal claim that the denominator contributes. It is 10.1% of the growth. Nine parts in ten of the rise are not population, so this must not be read as ascertainment explaining the trend - it is closer to the opposite.
- All-ages denominator against an all-ages numerator. The age-specific version is AS06 and returns a similarly small magnitude.
- ONS mid-year estimates are as at 30 June and are matched to the financial year that contains them; no interpolation is performed.
- The registry's falsifier wording ('standardised rates remain unchanged') is ambiguous between 'unchanged from raw' and 'flat over time'. It is read here as the former, the only reading on which it falsifies rather than confirms the statement. An adjudicator should fix the wording.

**What would settle it.** Nothing further for this series - the decomposition is exact arithmetic. The open question is whether it holds for a gender-service series, whose relevant denominator is an age-and-sex band rather than the whole population.

---

## AS12 - Follow-up attrition

> Observed persistence/detransition rates are biased by differential follow-up.

**Direction: INCONCLUSIVE.** Falsifier: NOT_TESTED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** IPW/MNAR sensitivity materially changes estimates.

**Registered falsifier.** Results stable under plausible missingness models.

**Finding.** Persistence and detransition rates require follow-up of individuals. No workstream in hand carries a cohort, so there is no estimate for a missingness model to move.

**Basis.** AS12 predicts that inverse-probability weighting or an MNAR sensitivity analysis materially changes an estimate. Every input to that sentence - the cohort, the follow-up, the attrition pattern - is individual-level, and aggregate published statistics supply none of them.

**Evidence used.**

- W01, W02, W09 and W10 are aggregate collections throughout

**Limits.**

- feasibility marks this OPEN_TESTABLE on required-workstream availability, but no required workstream carries the predictor the prediction names

**What would settle it.** Individual-level linked records under a TRE, which the feasibility census classifies as NEEDS_INDIVIDUAL_LEVEL for this proposition's neighbours and arguably should for this one.

---

## TH04 - Policy embedding

> Policy adoption precedes and predicts downstream institutional implementation.

**Direction: INCONCLUSIVE.** Falsifier: INCONCLUSIVE. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Process tracing and event timing support policy→infrastructure→practice sequence.

**Registered falsifier.** Practice precedes policy or non-adopters show same changes.

**Finding.** Annual W09 document counts cross-correlate best at lag -2 (r=0.80), which is the practice layer leading the policy layer - but 72% of the policy peak in 2024 comes from one source's API, so the series measures archival depth as much as policy activity.

**Basis.** TH04 predicts a policy to infrastructure to practice sequence, and its falsifier is 'practice precedes policy'. The ordering statistic points at the falsifier, but the input is a count of documents that six heterogeneous websites still serve, harvested through four different routes with different archival depth. A recency-weighted publication count is not policy adoption, and a finding either way would be an artefact of the harvest.

**Evidence used.**

- W09: data/w09_clinical_guidance.json, 152 dated documents, 121 distinct anchor dates, six publishers
- W10: legislation.gov.uk enactment years via LegislationConnector

**Limits.**

- Document COUNT is not adoption. One guideline can change practice nationally and a hundred blog posts can change nothing.
- The harvest routes differ by source: a WordPress REST API returns recent posts far more completely than a sitemap scrape returns old ones, which manufactures an upward trend in the policy layer specifically.
- Sixteen annual points, and the correlation is driven by two spikes.
- Legislation dates resolve to 1 January of the enactment year and cannot order events within a year.
- W05 (education) is a required workstream for TH04 and supplies nothing here; no education series was found that measures institutional implementation.

**What would settle it.** A dated register of implementation events - service specifications issued, commissioning policies adopted, clinics opened - rather than publications. None of W05, W09 or W10 carries one, so TH04 is not answerable from a publication corpus however many anchors it holds.

---

## TH05 - Network effects

> Formal networks increase diffusion/standardisation of concepts or practices.

**Direction: INCONCLUSIVE.** Falsifier: NOT_TESTED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Network centrality/exposure predicts adoption controlling for baseline similarity.

**Registered falsifier.** No diffusion beyond homophily/common shocks.

**Finding.** The institutional graph gives network structure, but there is no per-node adoption outcome and no baseline-similarity control, so centrality cannot be shown to predict anything.

**Basis.** TH05 predicts that network centrality or exposure predicts adoption CONTROLLING for baseline similarity. The graph exists (824 entities, 1,286 relations) and centrality is computable, but 'adoption' is recorded for no node and homophily cannot be controlled without node attributes - 647 of 824 nodes are domain UNKNOWN.

**Evidence used.**

- W07: 7,071-record literature corpus in runtime/oslt.db
- W09/W10: institutional graph as re-adjudicated in docs/COUPLING_READJUDICATION.md

**Limits.**

- feasibility marks this OPEN_TESTABLE on required-workstream availability, but no required workstream carries the predictor the prediction names

**What would settle it.** Coding, per institution, the date it adopted a named practice - which is human coding, and governance/claim_release.py records zero human-coded lanes.

---

## TH07 - Structural coupling

> Separate institutions transmit mutually reinforcing content without central coordination.

**Direction: WEAKENS.** Falsifier: TRIGGERED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Graph/process-tracing finds repeated cross-domain transfer and feedback.

**Registered falsifier.** Content/timing is independent and no cross-system coupling is observed.

**Finding.** On an 824-entity, 1,286-relation graph at STRONG_IDENTIFIER, assessed against 29 Parliament-fixed dates, no date returned MD15_COUPLING_SUPPORTED and ten returned MX09_ISOLATED_PROCESSES_BETTER. Not one connected component mixes more than one relation type.

**Basis.** TH07's falsifier is 'content/timing is independent and no cross-system coupling is observed'. That is what the re-adjudication found, on a graph quadrupled in size, without lowering the resolution tier, against dates fixed by Parliament rather than chosen.

**Evidence used.**

- W07/W09/W10: institutional ontology graph from runtime/oslt.db (360Giving, UKRI GtR, Contracts Finder, GOV.UK publications, Parliament written evidence)
- W10: LegislationConnector outcome dates, live from legislation.gov.uk
- docs/COUPLING_READJUDICATION.md

**Limits.**

- This is an absence claim about THIS graph, at THIS tier, over FIVE registers. 434 of 824 entities carry no strong identifier and cannot be merged at all, so a genuine shared body appearing under two spellings is invisible.
- 647 of 824 entities are domain UNKNOWN and can never widen cross-system spread, so more than three quarters of the graph is inert for the test.
- Company filings, board memberships, personnel overlap, sub-awards and correspondence are absent. Coupling running through any of those channels is not measured here.
- Enactment dates resolve to 1 January of the enactment year; day-level precision would be invented.
- W11 (media) is a required workstream for TH07 and contributes nothing to this verdict - the graph carries no media entities.

**What would settle it.** Registers carrying strong identifiers for the 52.7% of entities that have none - Companies House officer appointments in particular - which would let a bridge appear if one exists. Lowering the tier is barred: every historical positive here evaporated once name-only merges were disallowed.

---

## TH08 - Cultural displacement

> Changes in institutional religious authority are one contextual predictor among broader cultural transformations.

**Direction: INCONCLUSIVE.** Falsifier: NOT_TESTED. Claim tier: DESCRIPTIVE_EVIDENCE_ONLY. Released: no.

**Prediction as registered.** Macro longitudinal/cross-jurisdiction models show independent contextual moderation.

**Registered falsifier.** Effect disappears under confounding/measurement controls.

**Finding.** Census 2021 gives a religion cross-tab at one instant. TH08 requires macro longitudinal or cross-jurisdiction models, and neither dimension exists in any workstream in hand.

**Basis.** TH08 predicts independent contextual moderation in longitudinal or cross-jurisdiction models. The only religion-linked measure available is Census 2021 RM173, a single cross-section of a question the Office for Statistics Regulation subsequently de-accredited. A cross-section cannot carry a moderation claim, and one jurisdiction cannot carry a cross-jurisdiction one.

**Evidence used.**

- W01: Census 2021 RM173 gender identity by religion (cross-section)
- W05/W10/W11: no repeated religiosity or cross-jurisdiction series harvested

**Limits.**

- feasibility marks this OPEN_TESTABLE on required-workstream availability, but no required workstream carries the predictor the prediction names

**What would settle it.** Repeated cross-national attitude series - successive waves of a comparable social survey - plus a pre-registered specification, since a contextual-moderation claim tested after seeing the data is not a test.

---

## Appendix: the AS08 continuous-provider computation in full

This is the computation `docs/REFERRAL_BASELINE.md` named as the thing that would settle its withdrawn second comparator: restrict to providers submitting continuously across the whole window. It was not asserted; it was run.

Window: 2017-04 to 2024-03 (financial years 2017/18 to 2023/24), 84 months, measure MHS01 (people with an open referral at period end).

- Providers appearing at any point in the window: **539**
- Providers submitting a usable value in **every** month: **71**
- Providers present in the first month 92, in the last month 397 (x4.32)

| Financial year | Continuous cohort | Unrestricted provider sum | England published |
|---|---:|---:|---:|
| 2017/18 | 1,165,965 | 1,264,237 | 1,225,177 |
| 2018/19 | 1,207,930 | 1,339,674 | 1,300,444 |
| 2019/20 | 1,217,740 | 1,395,124 | 1,353,628 |
| 2020/21 | 1,211,032 | 1,390,973 | 1,348,436 |
| 2021/22 | 1,350,517 | 1,555,213 | 1,504,431 |
| 2022/23 | 1,496,383 | 1,705,608 | 1,648,368 |
| 2023/24 | 1,645,291 | 1,918,474 | 1,851,271 |

- Continuous cohort **x1.411**; unrestricted x1.517; England published x1.511; submitting providers x4.32.
- **82.6% of the log growth survives** restriction to the fixed cohort; 17.4% is attributable to coverage and composition.
- The cohort holds 92.2% of unrestricted activity in the first year and 85.8% in the last.

### Mechanism comparison

Run through `governance/mechanism_simulation.compare_mechanisms` against the cohort series at a declared tolerance of 15% of the observed range. Both grids were fixed before the run.

| Mechanism | Grid | Accepted | Best distance | Direction |
|---|---:|---:|---:|---|
| `COVERAGE_ONLY` | 25 | 0 | 36.0% | WEAKENS |
| `REAL_GROWTH_WITHIN_FIXED_COHORT` | 45 | 2 | 12.5% | INCONCLUSIVE |

- Refuted: COVERAGE_ONLY
- Compatible: REAL_GROWTH_WITHIN_FIXED_COHORT

> Refuted mechanisms failed to reproduce a real observed series and are genuinely disfavoured. Compatible mechanisms are NOT ranked against each other: reproducing one aggregate series is a weak constraint that many mechanisms satisfy. No compatible mechanism may be reported as supported.

### What this does to the withdrawn comparator

`docs/REFERRAL_BASELINE.md` withdrew its second comparator on the ground that the apparent rise might be entirely a coverage artefact, and said every figure there should be treated as an upper bound and quite possibly as no change at all. On the coverage-fixed series a real rise remains: roughly four fifths of the log growth survives. That does **not** reinstate the withdrawn claim - the withdrawn argument was about the age gradient and the female excess within under-18s, and this computation is on an all-ages stock measure, so the stratum-specific claims remain untested. What it establishes is that the comparator series is not *wholly* an artefact, which was the live possibility.

---

## Provenance

- **MHSDS**: runtime\mhsds\MHSDS Time_Series_data_Apr_2016_Jun_2026_Perf.zip (local read, no network; DS077)
- **population**: NOMIS NM_2002_1, England, 2016-2025, live
- **W09**: w09_clinical_guidance.json: 171 documents, 121 distinct anchor dates
- **W02_fingertips**: fingertips_w02.json: 81 series
- **W10_legislation**: 28 enactment years via legislation.gov.uk, as recorded in data/coupling_readjudication.json
- **census**: data/census_2021_gender_identity.json and docs/CENSUS_2021_GENDER_IDENTITY.md
