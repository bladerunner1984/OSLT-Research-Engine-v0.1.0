# OSLT 64-Proposition Feasibility Reconciliation

**Founder constraint applied:** no recruitment, experiment, survey, interview, exposure, or longitudinal follow-up of new human participants  
**Review date:** 26 August 2026  
**Registry reviewed:** `registries/hypotheses.csv` (64/64 propositions)  
**Canonical remote:** `https://github.com/bladerunner1984/OSLT-Research-Engine-v0.1.0.git`  
**Canonical base:** `refs/heads/main` at `4eef48894672504bb1661ec47b6c51c0ad246549` after fetch on 2026-08-26  
**Disposition:** companion feasibility register only; the scientific registry is preserved and was not edited

## Decision

OSLT remains scientifically viable under the no-new-human-research constraint, but its immediate programme must become much narrower.

The reconciled portfolio is:

| Class | Meaning | Count | Programme treatment |
|---|---|---:|---|
| A | `EXECUTABLE_NOW_PUBLIC_DATA` | **26** | Eligible for the result queue now |
| B | `EXECUTABLE_WITH_EXISTING_SECONDARY_DATA_ACCESS` | **25** | Variable audit and lawful access only; does not block A studies |
| C | `PRIMARY_HUMAN_RESEARCH_REQUIRED` | **7** | Preserved and parked; no implementation machinery |
| D | `NOT_IDENTIFIABLE_WITH_CURRENT_DATA` | **5** | Preserved; no result claim unless the identification problem changes |
| E | `DUPLICATIVE` | **1** | Preserved for lineage; execution mapped to its parent proposition |
|  | **Total** | **64** | Registry retained in full |

The old OSLT feasibility census is not fit for this decision. It mechanically treats workstream tags such as W12/W13 as a requirement for primary collection, and reused temporal text as a requirement for individual-level data. That incorrectly pushes public bibliometric, guideline, media, and institutional-network questions into human-research classes. The reconciliation below instead asks whether a bounded estimand is identifiable from a named source and states the maximum claim that source can support.

The immediate result queue should contain five studies, in this order:

1. Census gender-identity instrument sensitivity and validity.
2. Public-service time-series measurement decomposition.
3. Longitudinal minority-stress-to-distress systematic review and meta-analysis.
4. Guideline ancestry and institutional document diffusion.
5. Media semantic diffusion and public-attention event study.

The current OSLT repository reports 64 propositions and substantial evidence infrastructure, but **zero answered propositions and zero released claims**. Existing calculations are therefore inputs to the first releases, not completed results. The programme should stop expanding general architecture until at least the first two signed result packages are complete.

## Non-negotiable interpretation rules

1. **“Consciousness” is not an OSLT outcome.** There is no registry construct, validated instrument, or observable counterfactual for it.
2. **A “meme” is usable only after operationalisation** as a prespecified token, phrase, frame, recommendation, image label, or document fragment with a dated source and an observable transmission or adoption event.
3. **Exposure/diffusion and individual causation are different questions.** A term appearing in news, guidance, or search data does not establish that a person saw it, interpreted it, or changed identity, distress, beliefs, or behaviour because of it.
4. **Aggregate associations remain aggregate.** Area-, institution-, or time-level correlations cannot be translated into individual psychological effects.
5. **B does not mean OSLT already holds the data.** It means a named, existing dataset has a lawful secondary-use route and a plausible field combination. A field-level audit remains mandatory before an access application.
6. **A can be partial only when the claim ceiling is explicit.** For example, MD12 is publicly testable for terminology availability and attention, not for individual interpretation.
7. **Nulls are bounded.** Equivalence or minimum-effect tests can rule out effects larger than a prespecified margin in a specified design; they cannot establish universal absence.

## Current data reality

The repository inventory is useful but must not be confused with topic-complete evidence:

- The local implementation status records 6,428 admitted evidence records, 824 entities, 1,286 relations, 64 propositions, and 0 released results.
- The local MHSDS archive has a complete 123-month England MHS01 series from April 2016 to June 2026, but it **does not contain a gender-service or gender-clinic referral measure**. It is a measurement-system/comparator source only.
- The Census 2021 harvest contains 517 cells across 13 gender-identity tables. The Office for Statistics Regulation cancelled accreditation of the gender-identity estimates in September 2024 because of unresolved response-quality concerns; these are now official statistics in development. This makes the data especially informative for AS10/MX10, not a precise national prevalence gold standard. [OSR final report](https://osr.statisticsauthority.gov.uk/publications/review-of-statistics-on-gender-identity-based-on-data-collected-as-part-of-the-2021-england-and-wales-census-final-report/)
- OpenAlex exposes a CC0 scholarly graph and a free bulk snapshot; its API now requires a key at scale and is freemium. [OpenAlex documentation](https://developers.openalex.org/)
- Crossref exposes public scholarly, funding, licence, update, reference, and integrity metadata without registration for ordinary public API use. [Crossref REST documentation](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- GDELT is openly downloadable, and GDELT 2.0 updates every 15 minutes, but source growth, automated coding, and news-volume normalisation are material design issues. [GDELT data documentation](https://www.gdeltproject.org/data.html)
- Wikimedia provides open pageview data from July 2015 onward, with documented treatment of automated traffic. [Wikimedia Analytics API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html)
- The UK Government Web Archive is public, retains multiple snapshots, and is Memento-compatible, but capture gaps remain. [UK Government Web Archive](https://www.nationalarchives.gov.uk/webarchive/about/)
- NICE publishes guidance and evidence reviews and documents a systematic, transparent evidence-review process; its syndication API may require a licence, so ordinary public documents should be the default source. [NICE evidence-review manual](https://www.nice.org.uk/process/pmg20/chapter/reviewing-evidence)
- The Millennium Cohort Study Age 23 release contains more than 9,700 respondents and includes gender identity, social networks/support, health, and other longitudinal domains; most data are available through the UK Data Service and selected sensitive fields through secure access. [MCS Age 23 release](https://cls.ucl.ac.uk/cls-studies/millennium-cohort-study/mcs-age-23-sweep/)
- UK Data Service SecureLab and the ONS Secure Research Service provide governed secondary-use routes for approved public-good research. These are access routes, not guarantees of approval or of the necessary variables. [UKDS SecureLab requirements](https://ukdataservice.ac.uk/find-data/access-conditions/secure-application-requirements/apply-to-access-non-ons-data/), [ONS Secure Research Service](https://www.ons.gov.uk/aboutus/whatwedo/statistics/requestingstatistics/secureresearchservice/aboutthesecureresearchservice)

## Proposition-by-proposition reconciliation

The machine-readable companion is `registries/proposition_feasibility.csv`. The classifications below apply to each proposition as currently written; the final column states the executable scope or the blocking reason.

### Intrinsic/recognition family

| ID | Class | Executable scope or reason |
|---|---|---|
| IR01 | B | Existing cohorts can estimate adjusted associations between measured prior exposures and later presentation; they cannot establish identity origin or independence from unmeasured exposure. |
| IR02 | B | Existing longitudinal cohorts or governed clinical data can estimate recorded continuity, transitions, and persistence, with attrition and instrument-change sensitivity. |
| IR03 | B | Separating recognition/access from coding, coverage, capacity, and demand requires restricted administrative data plus existing surveys; public proxies are insufficient for the “major portion” claim. |
| IR04 | B | Existing survey/cohort microdata can support harmonised measured prevalence; “underlying prevalence” must be replaced in the estimand by prevalence under common observed definitions. |
| IR05 | B | Published evidence and governed cohort/genomic data permit systematic review or secondary analysis of contribution to variation, not biological determinism. |
| IR06 | D | No current source observes a complete prior media, peer, and institutional exposure history; “no identifiable exposure” cannot be treated as verified non-exposure. |
| IR07 | B | Item-level secondary data permit measurement-invariance testing; aggregate tables do not. |
| IR08 | D | Current data do not observe “origin” validly or separate acceptance-to-disclosure effects from cohort, period, selection, and measurement processes. |

### Multi-domain mechanism family

| ID | Class | Executable scope or reason |
|---|---|---|
| MD01 | B | Existing cohorts/clinical data can test phenotype modification of recorded distress and trajectory, subject to confounding and timing. |
| MD02 | B | Repeated secondary measures can order recorded symptoms and distress; record time is not necessarily onset time. |
| MD03 | B | Birth cohorts contain pubertal/body-development and later outcome measures; field-level validation is required. |
| MD04 | C | No confirmed existing source jointly provides a temporally resolved peer network, topic-specific exposure, and repeated outcome adequate to separate influence from homophily. |
| MD05 | C | A valid test needs person-specific recommendation exposure logs before an individual outcome and a design separating passive exposure from active search. |
| MD06 | C | No confirmed existing source links versioned historical school-policy exposure to repeated individual terminology, disclosure, transition, or help-seeking outcomes. |
| MD07 | B | Governed clinical records linked to guidance versions can compare recorded formulation/pathway decisions; framing is imperfectly observed. |
| MD08 | B | Restricted clinical records may support assessment-depth and allocation analyses after a validated depth measure is defined. |
| MD09 | B | Public documents date guidance, but patient/provider secondary data are needed to estimate practice change beyond contemporaneous case mix. |
| MD10 | A | Versioned guidance, policy, consultation, funding, governance, and citation records support dated institutional diffusion analysis. |
| MD11 | A | Registration, publication, citation, funding, and guideline metadata support a bounded science-system analysis; framework-direction coding must be preregistered and audited. |
| MD12 | A | Public media and attention data test framing, terminology availability, and attention only—not individual interpretation. |
| MD13 | A | Public policy, media, legal, and institutional corpora support harmonised macro-cultural availability/legitimacy comparisons. |
| MD14 | A | Public institutional-religion, policy, and discourse series support contextual macro-level tests; the proposition already excludes individual causation. |
| MD15 | A | Public citation, funding, personnel, procurement, consultation, and document-lineage ties support structural-coupling tests; ties do not prove coordination. |
| MD16 | B | Existing longitudinal sequences permit preregistered trajectory/mixture analysis; inferred classes are descriptive and model-dependent. |
| MD17 | B | Sufficiently powered existing microdata permit prespecified interaction tests after the scale and subgroup are frozen. |
| MD18 | B | Published longitudinal evidence and existing cohorts permit baseline-adjusted tests of stigma/discrimination and later distress; identity origin is outside the claim. |
| MD19 | B | Existing cohorts support family/social-context modification analyses with non-blaming language and no universal causal claim. |
| MD20 | C | No confirmed source repeatedly measures person-level vocabulary adoption and distress with adequate timing; retrospective timing would retain severe recall bias. |

### Ascertainment family

| ID | Class | Executable scope or reason |
|---|---|---|
| AS01 | A | Public referral series, eligibility rules, service changes, and policy dates support bounded interrupted-time-series/event studies. |
| AS02 | A | Public provider capacity, waiting, configuration, and activity series support aggregate tests where definitions harmonise. |
| AS03 | A | Public codebooks, metadata, and series permit level/slope tests at prespecified coding changes. |
| AS04 | B | Repeated surveys/cohorts are needed because service counts conflate disclosure, help-seeking, access, coding, and need. |
| AS05 | A | Public news, pageview/search, policy, and service series permit attention/ascertainment timing tests; awareness remains a proxy. |
| AS06 | A | Public age, sex, geography, and service-composition strata permit standardisation/decomposition where required cross-tabs exist. |
| AS07 | A | Public provider locations, population denominators, geography, and aggregate use support access-gradient analysis with area-level need controls. |
| AS08 | A | Provider-month coverage metadata support fixed-cohort and coverage-adjusted sensitivity analyses now. |
| AS09 | A | Public category-specific series and coding histories support diagnostic substitution tests. |
| AS10 | A | Public instruments, response distributions, and regulator findings support direct measurement-sensitivity studies. |
| AS11 | A | Public population estimates and activity counts support rate and raw-count decomposition. |
| AS12 | B | Existing longitudinal microdata and attrition records permit inverse-probability weighting and bounds; summaries alone do not. |

### Mixed/alternative family

| ID | Class | Executable scope or reason |
|---|---|---|
| MX01 | B | A joint contribution model requires harmonised individual and aggregate secondary data; public components yield only partial decompositions. |
| MX02 | B | Longitudinal microdata support cohort heterogeneity, though age-period-cohort separation remains assumption-dependent. |
| MX03 | B | Existing microdata can test heterogeneity if sex recorded at birth is measured rather than inferred from a current response. |
| MX04 | A | Public policy, service, survey, and population series permit multijurisdiction comparisons with construct differences documented. |
| MX05 | A | Versioned classifications, codebooks, guidance, and aggregate series support diagnostic-regime comparability tests. |
| MX06 | B | Linked/longitudinal microdata are needed to distinguish identity, distress, referral, treatment request, and intervention outcomes and their predictors. |
| MX07 | D | A residual is conditional on model scope, error, and omitted variables; current data do not define a stable mechanism-independent residual. |
| MX08 | D | Prediction does not identify a causal null, and current data lack a credible instrument, natural experiment, or person-specific exposure design. |
| MX09 | A | Public policy timing, institutional networks, and aggregate outcomes permit bounded equivalence/minimum-effect tests, not a universal institutional null. |
| MX10 | A | Public instrument changes, category definitions, language patterns, and negative-control questions support artefact sensitivity tests. |
| MX11 | D | Current sources do not identify the relevant common causes or a valid instrument; competing model fit cannot distinguish confounding from causation. |
| MX12 | B | Repeated secondary microdata permit lagged bidirectional prediction; cross-lagged estimates alone do not prove reciprocal causation. |
| MX13 | B | Large secondary microdata permit prespecified heterogeneous-effect analysis with shrinkage and multiplicity control. |
| MX14 | A | Open registration/publication/citation/funding/guideline data support competing selection models; a null cannot prove no gatekeeping. |
| MX15 | A | Public cross-jurisdiction series permit event/equivalence tests with broader cultural controls; individual inference is prohibited. |
| MX16 | A | Competing preregistered models can be compared for observational/predictive equivalence and specification sensitivity on the same public data. |

### Thesis-mechanism family

| ID | Class | Executable scope or reason |
|---|---|---|
| TH01 | B | Published experiments and existing datasets permit systematic review/reanalysis of salience, defaults, social proof, and framing; OSLT transfer is indirect. |
| TH02 | C | Private perception and suppressed expression are not jointly observed in a confirmed existing source; a direct test needs new participant research. |
| TH03 | C | Private agreement and public expression are not jointly observed in a confirmed topic-specific secondary source. |
| TH04 | A | Versioned policy, guidance, and institutional documents support adoption-lag and event-history analysis. |
| TH05 | A | Formal public ties and dated institutional adoption support network diffusion analysis with homophily/common-shock controls. |
| TH06 | C | Public sanction records observe selected cases but not counterfactual behaviour or perceived sanction; no adequate protected personnel dataset is confirmed. |
| TH07 | E | Substantively duplicates MD15. Preserve the row and map evidence/execution to MD15. |
| TH08 | A | Public institutional-religion, policy, and discourse series support contextual multivariable tests with negative controls. |

## “Impact of memes on human consciousness”: useful mapping and hard boundary

The phrase is not a scientifically usable OSLT question as stated. Its useful content is a family of **observable diffusion questions**:

| Observable construct | Operational measure | OSLT mapping |
|---|---|---|
| Semantic/narrative diffusion | First appearance, normalised term frequency, source-to-source lag, cascade size, text similarity | MD10, MD12, MD13, MD15, TH04, TH05 |
| Terminology uptake | First use and sustained use by a named institution or document series | MD10, MD15, TH04, TH05 |
| Public attention/information seeking | Wikipedia pageviews, lawful search-interest series, news-volume-normalised attention | AS05, MD12 |
| Framing | Preregistered frame categories or embedding/text-classification scores with a human-audited validation set | MD12, MD13 |
| Guideline/policy language | Citation ancestry, textual reuse, recommendation adoption and lag | MD10, TH04, TH05 |
| Institutional adoption | Dated adoption event by organisation linked to formal network ties | MD10, MD15, TH04, TH05 |
| Service/referral patterns | Aggregate rates around externally dated events, with coverage/denominator controls | AS01, AS02, AS05, AS08, MX09 |

Two registry propositions concern individual exposure and must not be smuggled into this work:

- MD04 asks whether peer networks affect individuals beyond homophily.
- MD05 asks whether passive/algorithmic exposure affects individuals beyond active search.

News frequency, pageviews, aggregate service use, or institutional language can establish neither proposition. They measure the availability and movement of information, not a person-specific exposure or psychological effect.

## Five strongest executable studies

### Study 1 — Census gender-identity instrument sensitivity and validity

**Precise research question**  
How sensitive are the England and Wales Census 2021 gender-identity estimates and subgroup contrasts to response-category construction, nonresponse, proxy response, language comprehension, and denominator choice?

**OSLT propositions**  
AS10 (primary), MX10 (primary), IR07 (bounded instrument component).

**Estimand**

1. Prevalence ratios and risk differences for a “gender identity different from sex registered at birth” response across prespecified comprehension/nonresponse strata.
2. The ratio created by incompatible category definitions carrying the same label (the current harvest shows 48,331 versus 18,074 for two meanings of “all other gender identities,” ratio 2.674).
3. A prespecified sensitivity interval for the national response proportion under alternative denominator and suspect-response recodes—not an estimate of latent true prevalence.

**Competing hypotheses**

- H1: observed subgroup variation is materially influenced by question comprehension, proxy response, nonresponse, or category construction.
- H2: subgroup variation is predominantly substantive and persists across high-comprehension and harmonised-definition strata.
- H0: the tested instrument features make no material difference beyond a frozen equivalence margin.

**Required data**  
NOMIS TS070/TS078 and relevant RM tables; ONS question wording, quality analyses, nonresponse/proxy documentation; OSR review; optional Scotland comparison using explicitly harmonised categories.

**Already available**  
The OSLT harvest has 517 cells from 13 tables, complete codelists, denominator roles, and provenance. It already reproduces the language/ethnicity response-quality signature and the 7-versus-8-category label collision.

**Missing data**  
No respondent-level joint age × language proficiency × identity table is held. Scotland has not been ingested into the same frozen schema. Those gaps limit subgroup adjustment but do not prevent the primary instrument-sensitivity result.

**Study design**  
Preregistered measurement-validity and sensitivity analysis of public aggregate data, with a cross-instrument comparison where harmonisation is defensible.

**Falsifier and negative controls**

- The language/comprehension gradient disappears in correctly interpreted, prespecified strata.
- Harmonising response categories removes the apparent category discrepancy.
- Sexual-orientation items on the same form provide a negative-control instrument because their accreditation was retained; a generic “sensitive census question” explanation predicts similar failure there.
- Perturbed small cells and structural zeros are excluded from any precision claim.

**Likely claim ceiling**  
The published estimate is materially sensitive—or not sensitive within a stated margin—to specified instrument features. No claim about true prevalence, temporal change, identity origin, or subgroup causation.

**Cost/access**  
£0 data cost; public/keyless NOMIS and regulator documents. Main cost is analysis and independent line audit.

**Executable implementation steps**

1. Freeze table IDs, codelists, denominators, recodes, equivalence margins, and subgroup contrasts.
2. Re-harvest from a clean environment and write a URL/timestamp/hash manifest.
3. Produce the category crosswalk before computing any estimate.
4. Run primary estimates, denominator sensitivity, comprehension-related contrasts, and negative control.
5. Have an independent reviewer audit table semantics and every reported numerator/denominator.
6. Release the frozen data extract, code, machine-readable result tables, and manuscript regardless of sign.

**Definition of DONE**  
A clean checkout reproduces every table and figure from the source manifest with one documented command; all estimates carry numerator, denominator, definition, uncertainty/perturbation note, and claim ceiling; an immutable release contains code, data extract, protocol, results, and checksums.

### Study 2 — Public-service time-series measurement decomposition

**Precise research question**  
For the public England MHSDS MHS01 series from April 2016 to June 2026, what proportion of observed log count growth is associated with provider coverage, population denominator change, age composition, coding/scope changes, and a remaining within-definition component?

**OSLT propositions**  
AS03, AS06, AS08, AS11, MX05, MX10, MX16.

**Estimand**

- Coverage component: difference in log growth between the unrestricted series and a prespecified continuous-provider cohort, expressed as a share of unrestricted log growth.
- Denominator component: difference between log count growth and log per-capita rate growth over the common window.
- Composition component: difference between crude and direct age-standardised log rate growth over the common age-stratified window.
- Coding/scope discontinuities: prespecified level and slope changes at documented collection-version boundaries.

Components will be reported on their valid common windows and will **not** be added when windows or measures differ.

**Competing hypotheses**

- H1: coverage, denominator, composition, or coding changes explain a material share of the observed rise.
- H2: most growth persists in stable providers and standardised rates.
- H0: each component is smaller than a prespecified materiality margin.

**Required data**  
MHSDS monthly MHS01 provider and England series, provider coverage, version/coding metadata, ONS population estimates, and published age bands.

**Already available**  
The local archive contains 123 complete months; 71 of 539 providers form the existing continuous cohort for the earlier comparison window. Current unreleased calculations indicate that most headline growth survives the fixed-provider restriction and denominator adjustment, but these must be rerun after a clean freeze.

**Missing data**  
There is no gender-service, gender-clinic referral, provider-by-age historical series, or age-by-sex cross-tab in this archive. That absence is decisive for the claim ceiling.

**Study design**  
Component decomposition, fixed-cohort sensitivity analysis, direct standardisation, and interrupted time series at externally dated coding/scope changes.

**Falsifier and negative controls**

- Stable-provider growth is equivalent to zero within the frozen margin.
- Age-standardised and crude growth diverge materially.
- Placebo change dates show discontinuities as large as actual coding dates.
- Stock and flow measures are never spliced; unrelated stable measures act as negative-control series.

**Likely claim ceiling**  
Measurement-system conclusions about public general mental-health activity. This study cannot be presented as evidence about gender-service referrals or any individual pathway.

**Cost/access**  
£0 data cost; public NHS and ONS data. Compute/storage already available.

**Executable implementation steps**

1. Freeze one primary measure, window, cohort rule, coding dates, population version, and materiality margins.
2. Rebuild the analytic series from raw public files; reject mixed monthly/rolling windows and suppressed-as-zero cells.
3. Estimate each component only on its valid common window.
4. Run placebo dates, cohort-definition, population-revision, and measure-name/ID sensitivity analyses.
5. Separate the result paper from all gender-service interpretation.
6. Release raw-file hashes, analytic table, code, diagnostics, and result narrative.

**Definition of DONE**  
One clean command recreates the source manifest, analytic panel, component table, figures, and robustness appendix; every component states its window and denominator; the release explicitly records the absent target measure and forbids topic-specific extrapolation.

### Study 3 — Longitudinal minority-stress-to-distress systematic review

**Precise research question**  
Among longitudinal studies of gender-diverse populations, what is the association between baseline stigma/discrimination and later validated distress after adjustment for baseline distress?

**OSLT propositions**  
MD18 (primary); MX08 and MX11 as competing explanations; MD02 for temporal ordering of recorded symptoms.

**Estimand**  
The primary meta-analytic effect is the pooled standardised longitudinal coefficient for baseline stigma/discrimination predicting follow-up depression/anxiety/distress after baseline-outcome adjustment, stratified by follow-up window. Incompatible effect measures will be analysed in separate prespecified strata rather than forced into one pooled number.

**Competing hypotheses**

- H1: greater baseline stigma/discrimination predicts worse later distress after baseline adjustment.
- H0: the pooled effect is within a prespecified equivalence interval around zero.
- Hcommon: apparent effects attenuate with stronger confounder control, prospective measurement, and lower risk of bias.
- Hpublication: small or imprecise null studies are underrepresented.

**Required data**  
Published longitudinal studies, protocols/registrations where available, extractable adjusted estimates, instrument definitions, follow-up time, attrition, and risk-of-bias information.

**Already available**  
OSLT has OpenAlex, Crossref, PubMed, Europe PMC, ClinicalTrials.gov, ISRCTN, PROSPERO, and retraction/integrity routes. These support discovery and lineage; they are not a completed systematic search.

**Missing data**  
A frozen search, duplicate screening, full texts, author-supplied estimates where papers do not report the required coefficient, and an audited extraction. Paywalled full text may require existing library access.

**Study design**  
PRISMA-style systematic review and random-effects meta-analysis with robust variance where multiple effects share a cohort, study-family collapse, attrition analysis, and risk-of-bias stratification.

**Falsifier and negative controls**

- Prospective baseline-adjusted estimates are null within the equivalence margin.
- Effects exist only in cross-sectional or retrospective studies, which are excluded from the primary estimate.
- Stronger confounder adjustment or low-risk-of-bias studies materially attenuate the association.
- Negative-control outcomes, where reported, show a similar association.
- Funnel and selection-model analyses indicate that a non-null pooled estimate is not robust to plausible missing studies.

**Likely claim ceiling**  
Evidence for or against a longitudinal association consistent with a minority-stress contribution to distress. No inference about identity origin and no definitive individual causal claim without stronger natural-experiment evidence.

**Cost/access**  
Public metadata are free; full text is £0 with suitable existing library access, otherwise low interlibrary/document-delivery cost. No participant contact.

**Executable implementation steps**

1. Freeze population, exposure, outcome, follow-up, effect hierarchy, exclusion criteria, equivalence margin, and analysis code shell.
2. Run reproducible searches across independent indexes and registries; save exact queries and result hashes.
3. Deduplicate and collapse shared cohorts before analysis.
4. Screen and extract with blinded duplicate review or an independent audit; no automated direction coding enters the primary result unreviewed.
5. Run primary, risk-of-bias, attrition, study-family, and publication-bias analyses.
6. Publish the extraction table, exclusion reasons, code, and null/non-null result.

**Definition of DONE**  
The release contains the frozen protocol, full search strings and dates, PRISMA flow, included/excluded study ledger, cohort-dependency map, audited extraction, reproducible meta-analysis, risk-of-bias table, and a claim bounded to distress rather than identity origin.

### Study 4 — Guideline ancestry and institutional document diffusion

**Precise research question**  
How do prespecified terms, evidence citations, and recommendation fragments move through UK clinical, NHS, education, government, parliamentary, and professional documents, and is earlier adoption associated with documented formal ties to prior adopters after controlling for common national shocks and document type?

**OSLT propositions**  
MD10, MD15, TH04, TH05; MX09 as the bounded null; TH07 retained as the duplicate of MD15.

**Estimand**

- Median and distribution of source-to-adopter lag for exact citations and validated text ancestry.
- Adoption hazard ratio for an institution with a prespecified formal tie to a prior adopter versus a matched institution without that tie, conditional on calendar time, institution/document type, and common policy events.
- Share of later documents with traceable evidence/citation ancestry versus unsupported textual similarity.

**Competing hypotheses**

- Hnetwork: formal ties predict earlier adoption after common-shock controls.
- Hcommon: institutions adopt independently in response to the same evidence or national event.
- Hconvergence: textual similarity reflects shared technical vocabulary rather than transmission.
- Harchive: apparent lag is produced by missing or misdated document versions.

**Required data**  
Versioned NICE, NHS England, GOV.UK, DfE, Hansard, legislation, professional-body, and archived documents; citations; publication and effective dates; organisations; formal ties from authoritative registers.

**Already available**  
OSLT has public guidance/policy connectors, a local guidance corpus, government and institutional registers, and a general graph. The public sources are sufficient to start, and archived government pages are accessible without participant research.

**Missing data**  
The existing graph is not topic-scoped. Version history is incomplete for some professional/local documents, and publication date is not implementation date. Local-school or local-provider policy coverage should not be made a dependency for the first result.

**Study design**  
Historical corpus analysis, citation/dataset lineage, event-history analysis, and network diffusion with matched risk sets. Exact citations and text similarity are reported separately.

**Falsifier and negative controls**

- Terms appear in alleged adopters before the alleged source.
- Shuffled adoption dates or degree-preserving random networks produce equal or stronger tie effects.
- Negative-control technical terms diffuse at the same rate.
- Tie effects vanish after national event and institution-type controls.
- Results depend on one archive snapshot or one ambiguous entity merge.

**Likely claim ceiling**  
Document-level ancestry, institutional adoption timing, and structural coupling. No claim that actors coordinated, believed the text, changed clinical practice, or affected patients.

**Cost/access**  
£0 for the core public corpus. Optional licensed professional/news archives are sensitivity analyses only and cannot block completion.

**Executable implementation steps**

1. Freeze a small term/recommendation ontology, institution set, document types, date rules, and formal-edge types.
2. Build a study-specific versioned corpus directly from public sources; do not extend the general platform.
3. Validate entity resolution and document dates before computing any network statistic.
4. Separate exact citation ancestry, validated text reuse, and mere co-occurrence.
5. Estimate adoption lags/hazards and run shuffled-time, random-network, and negative-term controls.
6. Release the corpus manifest, permitted text-derived features, edge evidence, code, and bounded result.

**Definition of DONE**  
Every adoption event points to a versioned source document and date; every network edge points to an authoritative record; a clean run reproduces lineage tables, event-history estimates, and negative controls; the release uses “diffusion/ancestry/association,” never “coordination” or individual influence.

### Study 5 — Media semantic diffusion and public-attention event study

**Precise research question**  
Do prespecified policy, guideline, and high-salience media events produce detectable changes in normalised gender-related terminology/framing in UK online news and in public information seeking, and how persistent are those changes?

**OSLT propositions**  
MD12 and AS05 (primary), MD13 (cross-jurisdiction extension), MX09 (common-event/null alternative).

**Estimand**

- Event-time change in daily/weekly topic mentions per total UK news volume.
- Event-time change in Wikipedia article pageviews per baseline, with automated traffic excluded where supported.
- Difference-in-differences or synthetic-control contrast against prespecified control terms, control events, and comparator jurisdictions where pre-trends pass.
- Persistence half-life or cumulative excess attention over a frozen post-event window.

**Competing hypotheses**

- Hevent: the dated event is followed by a discrete, persistent shift in terminology/framing or attention.
- Hvolume: the apparent shift is general news-volume/source-coverage growth.
- Hcommon: an unrelated concurrent event explains both treatment and control movement.
- Hnull: the change is within a prespecified equivalence margin.

**Required data**  
GDELT 2.0 article/mention metadata, total-volume denominators, Wikimedia pageviews, frozen event dates from primary documents, source and jurisdiction metadata, and a preregistered term/frame dictionary.

**Already available**  
GDELT is public and an OSLT connector exists, but the topic series has not been harvested. Wikimedia pageviews are public from July 2015. Official policy/guideline dates are available from the document study.

**Missing data**  
The event list, ontology, source-coverage diagnostics, and page-title/redirect map must be frozen. Google Trends API access remains limited to alpha applicants and is therefore an optional B sensitivity source, not a dependency. [Google Trends API alpha](https://developers.google.com/search/apis/trends)

**Study design**  
Interrupted time series and event study, followed by difference-in-differences or synthetic control only where treatment timing, controls, and pre-trends are defensible.

**Falsifier and negative controls**

- Placebo dates generate changes as large as the true event.
- Unrelated terms or comparator jurisdictions move similarly.
- Effects disappear after normalising by total news volume or restricting to a stable source panel.
- Pageview changes lead rather than follow the alleged event, indicating event timing is not the initiator.
- Results depend on one ambiguous term or one news source.

**Likely claim ceiling**  
A dated event is associated with a change in public information availability, framing, or attention. No inference about individual exposure, belief, distress, identity, decision-making, or “consciousness.”

**Cost/access**  
£0 using raw GDELT/Wikimedia downloads; modest optional BigQuery compute. Google Trends is optional and cannot delay the result.

**Executable implementation steps**

1. Freeze events, term/frame ontology, source panel, control terms, jurisdictions, windows, and effect margins before the confirmatory fetch.
2. Fetch only the needed GDELT and Wikimedia aggregates with source manifests and raw-response hashes.
3. Validate stable-source and total-volume denominators; audit classifier precision/recall on a blinded sample of documents.
4. Run event study, placebo dates, control terms, stable-panel, and pre-trend checks.
5. Report attention and semantic diffusion as separate outcomes.
6. Release queries, derived series, code, diagnostics, and bounded result.

**Definition of DONE**  
A clean run recreates the dated event ledger, source-normalised media series, pageview series, primary estimate, placebo distribution, and robustness tables; the abstract explicitly states that the outcomes are aggregate diffusion/attention and cannot support individual causation.

## Revised result-producing roadmap

### Result cycle 0 — apply the constraint immediately

- Keep `registries/hypotheses.csv` unchanged.
- Adopt the companion CSV from this review as the programme feasibility view.
- Remove all C-class implementation work from the active backlog. Do not build consent, recruitment, survey, interview, experiment, exposure-log, or participant-follow-up machinery.
- Prevent D-class propositions from receiving “inconclusive” pseudo-results. Their status is “not identified by the current data/design.”
- Map TH07 evidence and execution to MD15 while retaining TH07 in the registry.
- Freeze broad connector/graph expansion until Result 1 and Result 2 release.

### Result cycle 1 — first public result

**Target:** Study 1, Census instrument sensitivity.  
**Why first:** topic-specific, entirely public, data already harvested, direct falsifiers, and a defensible measurement claim even if every substantive mechanism remains unresolved.  
**Timebox:** 10 working days from protocol freeze.  
**Exit:** immutable result package meeting the DONE definition; no “draft finding” status.

### Result cycle 2 — independent public replication of the measurement lesson

**Target:** Study 2, MHSDS measurement decomposition.  
**Why second:** most analysis assets already exist and the result directly demonstrates how coverage, denominators, composition, and coding alter apparent trends.  
**Timebox:** 15 working days after Result 1.  
**Exit:** signed public release with the non-gender-service claim boundary in its title, abstract, and machine-readable metadata.

### Result cycle 3 — one individual-level question without new participants

**Target:** Study 3, longitudinal systematic review/meta-analysis.  
**Why third:** it answers a person-level temporal question using existing research while obeying the human-subject constraint and explicitly separates distress from identity origin.  
**Timebox:** six to eight weeks; publish an empty/insufficient-evidence result if the eligible evidence base is too small.  
**Exit:** PRISMA package, audited extraction, reproducible meta-analysis or a reproducible conclusion that no poolable evidence exists.

### Result cycle 4 — diffusion at the correct unit of analysis

**Targets:** Study 4, then Study 5.  
**Why:** both operationalise the useful part of the “memes” question at document, institution, media, and attention levels. Study 4 supplies the frozen event/document ledger used by Study 5.  
**Timebox:** six weeks for the core public corpus per study.  
**Exit:** two separate releases; no combined narrative that turns document diffusion into personal influence.

### Secondary-data lane

Run this lane without blocking the public-result queue:

1. For each B proposition, name one primary dataset and one fallback.
2. Perform a field-level catalogue audit before writing any application.
3. Record whether the required exposure, outcome, timing, identifier/linkage, confounders, and attrition variables coexist.
4. Apply only for studies that survive the audit and have a frozen estimand and analysis plan.
5. Do not apply to UK Biobank while its Research Analysis Platform is closed and phased reopening is only planned from September 2026; do not assume NHS/ONS/UKDS approval. [UK Biobank RAP status](https://www.ukbiobank.ac.uk/use-our-data/research-analysis-platform/)
6. Treat access refusal or missing joint fields as evidence for reclassification, not as a reason to start primary collection.

## Release standard: what “completed, reproducible result” means

Every OSLT result must have all of the following. Anything less remains analysis work, not a result.

1. A protocol and analysis plan frozen before the confirmatory fetch or before outcome inspection.
2. A source manifest containing canonical URL, query, retrieval time, version, licence/access basis, and cryptographic hash.
3. A documented clean-environment command that rebuilds the analytic data and all reported outputs.
4. Machine-readable effect estimates, uncertainty, denominators, exclusions, and negative controls.
5. Dependency-family handling so duplicate records, shared cohorts, and aggregator sources are not counted as independent evidence.
6. Explicit falsifier/equivalence margin and publication regardless of direction.
7. A claim-ceiling statement in the abstract, results table, and release metadata.
8. An independent semantic/numerical audit for category definitions, dates, and source lineage.
9. A complete limitations section naming missing variables and prohibited inferences.
10. An immutable release with checksums. “Candidate,” “supports,” or “inconclusive” rows in the internal store do not satisfy DONE.

## Immediate founder-level choices resolved by this reconciliation

- The 64-proposition registry survives intact.
- No new human-subject research is needed for the first five result packages.
- C-class propositions are scientifically preserved but operationally dormant.
- “Consciousness” is rejected as an outcome; semantic diffusion, institutional adoption, attention, framing, and service patterns are accepted observable constructs.
- MD04/MD05 individual peer/algorithmic causation is not inferred from aggregate media or attention data.
- The fastest valid OSLT result is a measurement-validity result, not a grand causal account.
- The next programme milestone is **Release 1**, not another architecture document.
