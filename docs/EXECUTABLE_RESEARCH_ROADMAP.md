# OSLT executable research roadmap

**Canonical from:** 2026-08-26  
**Scientific registry:** all 64 proposition IDs remain in `registries/hypotheses.csv`  
**Operational feasibility:** `registries/proposition_feasibility.csv`

## Programme objective

OSLT's immediate objective is to publish completed, reproducible, falsifiable,
bounded results using public evidence or lawfully accessed existing secondary data.
It is **not** to answer all 64 propositions at once.

The scientific registry and the executable queue are separate controls:

- the registry preserves the full long-term hypothesis space;
- the feasibility companion classifies all 64 without changing their statements;
- A propositions may enter the public-data result queue now;
- B propositions enter a field-audit/access lane and do not block public results;
- C propositions are preserved but parked under the founder's permanent operational
  constraint against new human-participant research;
- D propositions remain visible as not identifiable with current data;
- E propositions remain visible and map to their non-duplicative parent.

No active work item may recruit, survey, interview, experiment on, expose, or begin
longitudinal follow-up of new participant groups. No participant-research machinery is
part of this roadmap.

## Result package 1 — Census instrument sensitivity and validity

**Propositions:** AS10, MX10, and the bounded instrument component of IR07.  
**Precise question:** How sensitive are the England and Wales Census 2021
gender-identity estimates and subgroup contrasts to response-category construction,
nonresponse, proxy response, language comprehension, and denominator choice?  
**Estimands:** prespecified prevalence ratios/risk differences across comprehension and
nonresponse strata; the effect of incompatible category definitions; and a sensitivity
interval under frozen denominator and suspect-response recodes.  
**Competing explanations:** substantive subgroup variation; instrument
comprehension/category artefact; or no material instrument effect within the equivalence
margin.  
**Required sources:** NOMIS TS070/TS078 and relevant RM tables; ONS instruments and
quality reports; OSR review; an optional harmonised Scotland comparison.  
**Already held:** 517 cells from 13 tables with codelists, denominator roles, and
provenance. These pre-freeze data are exploratory inputs only.  
**Missing:** respondent-level joint age/language/identity data and a harmonised Scotland
extract. Neither blocks the primary aggregate instrument result.  
**Methods:** preregistered public-data measurement-validity and sensitivity analysis.  
**Falsifiers/negative controls:** no comprehension gradient in prespecified strata;
category discrepancy disappears under harmonisation; sexual-orientation items on the same
form as a negative-control instrument; no precision claim from perturbed small cells.  
**Claim ceiling:** sensitivity of the published measurement to specified instrument
features—not true prevalence, temporal change, identity origin, or subgroup causation.  
**Access/cost:** public, keyless, £0 data cost.  
**DONE:** a clean checkout recreates the source manifest, analytic tables, estimates,
negative controls, figures, and checksums with one documented command; every output states
its numerator, denominator, definition, limitation, and claim ceiling.  
**Can run now:** **YES — selected first package.** The frozen specification is under
`studies/census_instrument_sensitivity/`.

## Result package 2 — Public-service time-series measurement decomposition

**Propositions:** AS03, AS06, AS08, AS11, MX05, MX10, MX16.  
**Precise question:** For England MHSDS MHS01 from April 2016 to June 2026, what
share of observed log count growth is associated with provider coverage, population
denominator change, age composition, coding/scope changes, and a remaining
within-definition component?  
**Estimands:** differences in log growth between unrestricted and continuous-provider
series; counts and per-capita rates; crude and direct age-standardised rates; and
prespecified level/slope changes at documented collection boundaries. Components are not
added across incompatible measures or windows.  
**Competing explanations:** material measurement-system contribution; persistence in
stable providers/standardised rates; or components smaller than frozen materiality
margins.  
**Required sources:** MHSDS MHS01 provider/England series, provider coverage, coding
metadata, ONS populations, and published age bands.  
**Already held:** 123 complete months and an existing 71-of-539 continuous-provider
cohort for the earlier window.  
**Missing:** a gender-service referral measure, historic provider-by-age series, and
age-by-sex cross-tab. These absences determine the claim ceiling.  
**Methods:** component decomposition, fixed-cohort sensitivity, direct standardisation,
and interrupted time series at external coding dates.  
**Falsifiers/negative controls:** stable-provider equivalence to zero; material
crude/standardised divergence; placebo dates; unrelated stable measures; no stock/flow
splicing.  
**Claim ceiling:** the public general-mental-health measurement system only. No inference
about gender-service referrals or individuals.  
**Access/cost:** public, £0 data cost.  
**DONE:** a clean command recreates source hashes, analytic panel, component estimates,
figures, and robustness appendix; every component states its valid window and the release
prominently records the absent target measure.  
**Can run now:** **YES**, after its own protocol freeze and clean data rebuild.

## Result package 3 — Longitudinal minority-stress-to-distress meta-analysis

**Propositions:** MD18; MX08 and MX11 as competing explanations; MD02 for recorded
temporal order.  
**Precise question:** Among longitudinal studies of gender-diverse populations, what is
the association between baseline stigma/discrimination and later validated distress after
adjustment for baseline distress?  
**Estimand:** pooled standardised baseline-adjusted longitudinal coefficient, stratified
by follow-up window; incompatible effect measures remain in separate frozen strata.  
**Competing explanations:** a positive longitudinal association; equivalence to zero;
common-cause/reverse-causality attenuation under stronger designs; or publication
selection.  
**Required sources:** published longitudinal studies, registrations/protocols,
extractable adjusted effects, follow-up/attrition, and risk-of-bias information.  
**Already held:** discovery and lineage routes for OpenAlex, Crossref, PubMed, Europe PMC,
ClinicalTrials.gov, ISRCTN, PROSPERO metadata where lawfully accessible, and retractions.  
**Missing:** frozen search, duplicate screening, full texts, author-supplied estimates
where necessary, and audited extraction.  
**Methods:** systematic review, study-family collapse, random-effects meta-analysis,
robust variance where effects share a cohort, attrition analysis, and risk-of-bias
stratification.  
**Falsifiers/negative controls:** prospective adjusted estimates within the null margin;
effects restricted to excluded cross-sectional/retrospective work; attenuation in
low-risk studies; negative-control outcomes; selection-model fragility.  
**Claim ceiling:** longitudinal association consistent with a contribution to distress.
No claim about identity origin or definitive individual causation.  
**Access/cost:** public metadata; existing library or low document-delivery cost for full
text. No participant contact.  
**DONE:** frozen protocol, full search strings/dates, PRISMA flow, inclusion/exclusion
ledger, cohort-dependency map, audited extraction, reproducible meta-analysis or a
reproducible insufficient-evidence result.  
**Can run now:** **YES WITH EXISTING EVIDENCE ACCESS**, after protocol freeze.

## Result package 4 — Guideline ancestry and institutional diffusion

**Propositions:** MD10, MD15, TH04, TH05; MX09 as the bounded null; TH07 mapped to MD15.  
**Precise question:** How do prespecified terms, citations, and recommendation fragments
move through UK clinical, NHS, education, government, parliamentary, and professional
documents, and is earlier adoption associated with documented formal ties after common
national shocks and document type are controlled?  
**Estimands:** citation/text-ancestry lag; adoption hazard ratio for tied versus matched
untied institutions; and the share of later documents with traceable ancestry.  
**Competing explanations:** network diffusion; independent response to a common event;
shared technical vocabulary; or missing/misdated archive versions.  
**Required sources:** versioned NICE, NHS England, GOV.UK, DfE, Hansard, legislation,
professional-body and archived documents plus authoritative formal ties.  
**Already held:** public guidance/policy connectors, a guidance corpus, government and
institutional registers, and a general graph.  
**Missing:** a topic-scoped graph, complete version history for some local/professional
documents, and implementation dates distinct from publication dates. Local coverage is
not a dependency for the first release.  
**Methods:** historical corpus analysis, citation lineage, validated text ancestry,
matched-risk-set event history, and network diffusion.  
**Falsifiers/negative controls:** adopter text predates its alleged source; shuffled dates
or degree-preserving random networks match the effect; negative-control terms diffuse
similarly; tie effect vanishes under national-event controls.  
**Claim ceiling:** document ancestry, adoption timing, and structural coupling—not
coordination, belief, clinical practice, or patient effects.  
**Access/cost:** core public corpus, £0. Licensed archives are optional sensitivity
sources and cannot block completion.  
**DONE:** every adoption and edge resolves to a versioned authoritative source; a clean
run reproduces lineage, event-history estimates, and negative controls; the release uses
document-level language only.  
**Can run now:** **YES**, after a small ontology and corpus freeze.

## Result package 5 — Media semantic diffusion and public-attention event study

**Propositions:** MD12, AS05, the macro component of MD13, and MX09 as a common-event/null
alternative.  
**Precise question:** Do prespecified policy, guideline, and high-salience media events
produce detectable changes in normalised UK online-news terminology/framing and public
information seeking, and how persistent are those changes?  
**Estimands:** event-time change in mentions per total news volume; event-time change in
Wikipedia pageviews; a difference-in-differences or synthetic-control contrast only where
pre-trends pass; and cumulative excess attention/persistence.  
**Competing explanations:** event-associated shift; general news/source-volume growth;
concurrent common event; or equivalence to zero.  
**Required sources:** GDELT 2.0, total-volume denominators, Wikimedia pageviews, frozen
primary-document event dates, and a preregistered term/frame dictionary.  
**Already held:** an OSLT GDELT connector and official event-date sources; Wikimedia data
are lawfully public but not yet harvested for this study.  
**Missing:** frozen event list/ontology/source panel, coverage diagnostics, and redirect
map. Google Trends alpha access is optional and cannot block the study.  
**Methods:** interrupted time series/event study; difference-in-differences or synthetic
control only after design checks.  
**Falsifiers/negative controls:** placebo dates; unrelated terms/jurisdictions; stable
source panel; normalisation by total news volume; leading rather than lagging pageview
change; single-term/source dependence.  
**Claim ceiling:** aggregate semantic availability, framing, and attention—not individual
exposure, belief, distress, identity, behaviour, or “consciousness.”  
**Access/cost:** public GDELT/Wikimedia, £0 data cost with modest optional query compute.  
**DONE:** a clean run recreates the event ledger, normalised media/pageview series,
primary estimate, placebo distribution, robustness tables, and aggregate-only claim
boundary.  
**Can run now:** **YES**, after Result package 4 supplies the frozen event ledger.

## Result sequence

1. **Freeze and release package 1.** Existing pre-freeze data remain exploratory; perform
   a clean confirmatory retrieval only after the committed freeze.
2. **Release package 2.** Treat it as an independent measurement-system result and keep
   the missing gender-service measure in the title/abstract claim boundary.
3. **Run package 3.** Publish a well-specified null or insufficient-evidence result if that
   is what the evidence yields.
4. **Run package 4, then package 5.** Share a frozen document/event ledger but publish
   document diffusion and media attention as separate outcomes.

No new general connector, ontology, graph, or model-routing architecture is a milestone.
Study-local code is added only when it directly produces a frozen result package.

## Definition of a completed OSLT result

A result is DONE only when it has:

1. a protocol/analysis plan frozen before confirmatory retrieval or outcome inspection;
2. a source manifest with URL, query, retrieval time, version, access basis, and hash;
3. one documented clean-environment command that rebuilds data and outputs;
4. machine-readable estimates, uncertainty, denominators, exclusions, and controls;
5. dependency-family collapse where sources or cohorts overlap;
6. a falsifier or equivalence margin and publication regardless of direction;
7. a claim ceiling in the abstract, results table, and release metadata;
8. independent semantic/numerical audit of definitions, dates, and lineage;
9. explicit missing-variable and prohibited-inference statements; and
10. an immutable checksummed release.

Internal candidate findings, compatibility labels, and unreleased claim-store rows are not
completed results.

## Informal “memes” concept

“Impact on consciousness” is not an OSLT outcome. The only executable mappings are
semantic diffusion, terminology uptake, public attention, framing, document ancestry,
institutional adoption, information seeking, and aggregate service patterns.

These are exposure/diffusion outcomes. They do not establish person-specific exposure or
individual psychological, identity, or behavioural causation. MD04 and MD05 remain parked
rather than being inferred from aggregate news, policy, network, pageview, or service data.

