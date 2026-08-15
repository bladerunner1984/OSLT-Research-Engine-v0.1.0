# OSLT Data Discovery Roadmap v2.0 RC1

**Status date:** 25 July 2026  
**Purpose:** identify, acquire and validate the data needed to run the OSLT multidisciplinary research programme.  
**Priority convention:** P0 = foundational/early; P1 = high-value expansion/replication; P2 = specialist/conditional.

## 1. Discovery principle

OSLT should not begin by collecting every available datum. It should begin with explicit estimands and a source-to-variable plan, prioritising data that can discriminate rival explanations.

Every acquisition passes:

```text
research question
→ estimand
→ required variables
→ measurement definition
→ candidate sources
→ field-level availability check
→ access/ethics/governance
→ provenance snapshot
→ linkage/measurement validation
→ analysis-ready dataset
```

The 640-row `OSLT_SOURCE_VARIABLE_LINKAGE_v2_0_RC1.csv` is the operational **variable**-level discovery map. It links every ontology variable to candidate primary/secondary source IDs. Candidate mapping is not evidence that a field exists: field-level availability and construct validity must be confirmed with the custodian before application.

## 2. Data-resource layers

### Layer A — Population denominators and what actually changed — Priority P0

**Data types required**
- age/sex/geography denominators;
- repeated population survey measures;
- identity/incongruence measures where available;
- migration/composition variables;
- practice/region survey weights;
- measurement-question wording and mode over time.

**Primary resources**
- DS014 ONS Census 2021 gender-identity datasets;
- DS015 GP Patient Survey;
- DS013 ONS Secure Research Service / cross-government products;
- DS018 Millennium Cohort Study;
- DS019 Understanding Society.

**Purpose**
Establish separate trends for population measures, disclosure, service presentation and referral. Run age-period-cohort, standardisation/decomposition, weighting and measurement-change analyses before causal attribution.

**Critical limitation**
Observed identity, referral and treatment series are not interchangeable outcomes. Measurement wording and ascertainment must be versioned.

### Layer B — NHS referral, clinical and service pathways — Priority P0

**Data types required**
- referral date/source;
- appointment/assessment dates;
- diagnoses/formulations;
- mental-health and neurodevelopmental history;
- medications/interventions;
- primary-care events;
- admissions/outpatients;
- waiting-list/capacity variables;
- provider/site/region;
- outcomes and follow-up.

**Primary resources**
- DS001 NHS England National Secure Data Environment / Research SDE Network;
- DS002 Hospital Episode Statistics;
- DS003 Mental Health Services Data Set;
- DS004 OpenSAFELY;
- DS061 NHS CYP Gender Service core national dataset, subject to availability/governance;
- DS062 historical GIDS / linked follow-up research, subject to governance.

**Replication resources**
- DS005 CPRD;
- DS010 Public Health Scotland eDRIS/National Safe Haven;
- DS011 SAIL Databank;
- DS012 Northern Ireland Honest Broker Service.

**Purpose**
Referral/ascertainment decomposition, temporality, comorbidity, treatment pathways, service-regime changes, cross-jurisdiction replication and target-trial-compatible research where data permit.

**Access architecture**
Individual-level records should remain inside the approved **Secure Data Environment** or Trusted Research Environment. The acquisition design assumes data minimisation and disclosure-controlled aggregate outputs.

### Layer C — Neurodevelopmental, psychiatric and developmental trajectories — Priority P0

**Data types required**
- autism/ADHD diagnosis and traits;
- psychiatric diagnosis/symptom onset;
- validated scales;
- trauma/safeguarding history where legitimately available;
- puberty/development variables;
- body-image and psychosocial constructs;
- timing relative to first gender-related distress/questioning;
- repeated follow-up.

**Primary resources**
- DS003 MHSDS;
- DS004 OpenSAFELY;
- DS018 Millennium Cohort Study;
- DS020 ALSPAC;
- DS021 Born in Bradford;
- DS019 Understanding Society where constructs overlap.

**Purpose**
Sequence analysis, event-history analysis, latent trajectories, measurement invariance, heterogeneous treatment/effect analysis and rival temporal models.

### Layer D — Family, peer and interpersonal context — Priority P0/P1

**Data types required**
- household structure;
- parent/child reports;
- relationship measures;
- peer networks;
- friendship changes;
- family mental-health context;
- socioeconomic context;
- repeated informants.

**Primary resources**
- DS018 Millennium Cohort Study;
- DS020 ALSPAC;
- DS021 Born in Bradford;
- DS019 Understanding Society;
- DS064 purpose-built qualitative/narrative corpus for constructs unavailable in routine data.

**Purpose**
Multilevel models, network/configurational analysis, informant disagreement and temporal pathway analysis.

### Layer E — Education policy and actual school exposure — Priority P0

**Data types required**
- school attended and dates;
- demographic/attainment/absence/exclusion variables;
- school policy versions;
- curriculum/lesson materials;
- external-provider materials;
- staff training;
- implementation dates/fidelity;
- local-authority/trust policy;
- safeguarding/referral practices.

**Primary resources**
- DS016 National Pupil Database;
- DS054 DfE RSHE statutory guidance corpus;
- DS055 DfE KCSIE corpus;
- DS056 school-level policies/curricula;
- DS057 FOI acquisition programme;
- DS063 local authority / ICB / provider archives.

**Purpose**
Create actual exposure variables rather than equating national publication with pupil exposure; enable multilevel and policy-counterfactual analyses.

**Natural-policy opportunity**
England's revised RSHE guidance is scheduled for introduction on 1 September 2026, and KCSIE 2026 also comes into force on 1 September 2026. Any future evaluation must distinguish anticipation, actual implementation and school-level fidelity.

### Layer F — Digital, platform, search and media exposure — Priority P0/P1

**Data types required**
- platform use;
- passive exposure where available;
- active search behaviour;
- recommendation timing;
- content metadata/text;
- peer/following network structure;
- longitudinal exposure intensity;
- geography/time;
- media habits and parental controls.

**Primary resources**
- DS022 Ofcom Children and Parents: Media Use and Attitudes;
- DS023 Ofcom Children Online Experiences programme;
- DS024 Google Trends API Alpha;
- DS025 YouTube Data API;
- DS026 TikTok Research API;
- DS027 Reddit Data API, conditional on current terms/access;
- DS028 GDELT 2.0.

**Purpose**
Separate active search from passive exposure, selection/homophily from influence, and platform diffusion from broader secular trends.

**Known constraints**
Public APIs rarely reproduce the full historical recommendation environment experienced by an individual. OSLT must mark platform-derived measures as exposure proxies unless direct logged exposure is available.

### Layer G — Academic knowledge production and epistemic selection — Priority P0

**Data types required**
- publication metadata;
- DOI and citation graph;
- author/institution/funder;
- dataset/cohort ancestry;
- preprints/registrations;
- trial registrations and results;
- funding awards;
- retractions/corrections;
- result direction and study quality;
- guideline citation uptake.

**Primary resources**
- DS033 OpenAlex;
- DS034 Crossref;
- DS035 Europe PMC;
- DS036 PubMed;
- DS037 ClinicalTrials.gov;
- DS038 ISRCTN;
- DS039 WHO ICTRP;
- DS040 PROSPERO;
- DS041 OSF Registries;
- DS042 UKRI Gateway to Research;
- DS043 Crossref Retraction Watch;
- DS059 ORCID/ROR.

**Supplementary licensed resources**
- DS044 Web of Science / Scopus / Dimensions.

**Purpose**
Reconstruct the study-production pipeline, publication/non-publication, time lag, citation dependency, institutional networks, funding pathways and effective independent evidence count.

### Layer H — Historical psychiatry, diagnosis and treatment doctrine — Priority P0

**Data types required**
- diagnostic-manual editions;
- diagnostic criteria;
- psychiatric textbooks and training materials;
- service protocols;
- clinical guidance;
- archived professional materials;
- terminology and recommendation changes;
- publication dates/effective dates.

**Primary resources**
- DS049 DSM editions / APA manuals (licensed where required);
- DS050 WHO ICD historical/current classifications;
- DS045 NICE guidance/evidence reviews;
- DS046 NHS England gender-services publication corpus;
- DS058 professional-body guideline corpus;
- DS029 UK Government Web Archive;
- DS051 Wellcome Collection;
- DS052 British Library / UK Web Archive.

**Purpose**
Historical regime-change coding, process tracing, content analysis, diachronic semantics and evidence-ancestry reconstruction.

### Layer I — Government, legal and policy mechanisms — Priority P0/P1

**Data types required**
- consultations;
- policy documents;
- statutory guidance;
- legislation;
- parliamentary debate/questions;
- commissioning changes;
- implementation dates;
- archived versions.

**Primary resources**
- DS030 GOV.UK publications/consultations;
- DS031 Hansard;
- DS032 legislation.gov.uk;
- DS029 UK Government Web Archive;
- DS063 local/provider commissioning archives.

**Purpose**
Process tracing, critical junctures, layering/drift/conversion, effective-date analysis and jurisdictional comparison.

### Layer J — Professional guidance and evidence ancestry — Priority P0

**Data types required**
- NICE/NHS/professional guidance versions;
- cited evidence;
- committee membership where public;
- consultation responses;
- service specifications;
- implementation evidence.

**Primary resources**
- DS045 NICE;
- DS046 NHS England;
- DS048 Cass/NHS implementation programme;
- DS058 professional-body corpus;
- DS033/DS034/DS035/DS036 for citation ancestry.

**Purpose**
Test whether clinical doctrine changes because of new evidence, institutional policy, semantic reframing, service redesign or combinations thereof.

### Layer K — News, advocacy and public discourse — Priority P1

**Data types required**
- article text/metadata;
- broadcast/news event metadata;
- source/outlet;
- date;
- framing/stance;
- quoted actors;
- terminology;
- audience proxies where available.

**Primary resources**
- DS028 GDELT;
- DS052 British Library/news archives;
- DS053 LexisNexis/Factiva;
- DS029 UK web archive;
- relevant platform sources DS025-DS027.

**Purpose**
Corpus linguistics, semantic change, frame/stance analysis and temporal diffusion; never linguistic change alone as proof of behavioural causation.

### Layer L — Clinical conversation and narrative data — Priority P0 primary collection / restricted secondary

**Data types required**
- time-stamped consultations/transcripts where lawfully authorised;
- pre/post positions;
- question/response structure;
- clinician language;
- patient language;
- narrative development over time;
- blinded coding;
- inter-rater reliability.

**Primary resources**
- DS064 researcher-authored qualitative corpus;
- future authorised clinical research collections;
- DS065 experimental vignette/framing studies for causal tests of wording.

**Purpose**
Conversation analysis, narrative analysis, pragmatics, linguistic convergence and experimental framing, with strict separation between lexical alignment and causal persuasion.

### Layer M — Biological/genomic hypotheses — Priority P2

**Data types required**
- genotype/genome;
- ancestry/relatedness;
- validated phenotype definitions;
- linked clinical variables;
- family structure;
- replication population.

**Primary resources**
- DS009 Genomics England;
- DS008 UK Biobank when applications reopen;
- DS007 Our Future Health;
- cohort genetic modules where relevant.

**Purpose**
Group-level association/heterogeneity and external replication only; genomic association cannot classify an individual's identity.

### Layer N — Treatment and long-term outcomes — Priority P0/P1

**Data types required**
- indication;
- treatment strategy;
- start/stop/switch dates;
- co-interventions;
- baseline state;
- outcomes;
- adverse events;
- loss to follow-up;
- adult linkage.

**Primary resources**
- DS061 NHS CYP core dataset;
- DS062 linked historical follow-up;
- DS004 OpenSAFELY;
- DS002/DS003 linked administrative datasets;
- DS005 CPRD as independent replication where feasible.

**Purpose**
Target-trial emulation, g-methods, event-history models and long-term outcomes. Treatment response is not diagnostic proof.

### Layer O — Designed experiments and adjudication studies — Priority P0 where ethical

**Data types required**
- preregistered vignettes;
- randomised wording/framing;
- masked reviewer assessments;
- A/B/n or factorial conditions;
- predeclared outcomes;
- reviewer/participant covariates needed for heterogeneity analysis.

**Primary resource**
- DS065 preregistered experimental vignette/framing studies.

**High-value uses**
- academic-review result-direction experiments;
- clinician/professional framing experiments using hypothetical cases;
- measurement/wording experiments;
- coder-blinding and analyst-blinding studies.

Experiments involving vulnerable populations, clinical care or sensitive content require proportionate independent ethical review; OSLT does not create authority to run them.

## 3. Acquisition Phases

### Phase 0 — Freeze the research constitution
- register questions/estimands;
- freeze outcome taxonomy and time-zero definitions;
- define source-independent variable dictionary;
- create data-protection/ethics decision log;
- define rival hypotheses and minimum discriminating evidence.

### Phase 1 — Open/public corpus build
Acquire and version open or openly queryable materials first:
- ONS aggregate data;
- GP Patient Survey aggregate data;
- NHS/NICE/DfE/GOV.UK/Parliament/legislation corpora;
- ICD public materials;
- OpenAlex/Crossref/Europe PMC/PubMed;
- trials/registries/UKRI/retraction data;
- Ofcom reports/data;
- Google Trends where access is granted;
- GDELT;
- public web archives.

**Output:** historical/policy/academic/discourse evidence graph and a refined list of variables genuinely requiring restricted microdata.

### Phase 2 — Restricted UK microdata applications
Run applications in parallel according to estimand, not convenience:
- NHS England SDE routes for HES/MHSDS and relevant linked data;
- OpenSAFELY projects where suitable;
- ONS SRS accreditation/project applications;
- DfE NPD access;
- cohort access applications (MCS/ALSPAC/Born in Bradford/UKHLS);
- NHS specialist service research datasets subject to governance.

**Output:** individual-level longitudinal/administrative analyses with explicit linkage error, missingness and ascertainment models.

### Phase 3 — Cross-jurisdiction and cohort replication
- Scotland eDRIS/National Safe Haven;
- Wales SAIL;
- Northern Ireland HBS;
- CPRD;
- Our Future Health;
- specialist cohorts.

**Output:** transportability and natural-policy/service contrasts; distinguish England-specific mechanisms from wider temporal change.

### Phase 4 — Digital/platform research access
- Ofcom downloadable/controlled resources;
- TikTok Research Tools application;
- Google Trends alpha access;
- YouTube API;
- other platform data only under current lawful/research terms.

**Output:** temporal exposure and diffusion proxies with provenance/coverage metadata.

### Phase 5 — Purpose-built primary studies
Only after observational gaps are known:
- preregistered masked A/B or factorial experiments;
- multi-analyst coding/replication;
- qualitative/narrative longitudinal research;
- measurement validation/invariance studies.

**Output:** evidence designed specifically to discriminate rival hypotheses that observational data cannot separate.

### Phase 6 — Integrated synthesis and external challenge
- dependency graph;
- cross-method triangulation;
- pairwise rival-model tournament;
- specification/multiverse analysis;
- certainty vector;
- external replication;
- independent quantitative, clinical, historical and methods review.

## 4. Data-access strategy

### Open data
Ingest locally with immutable raw snapshots, retrieval date, licence, URL, content hash and parser version.

### Licensed data
Record licence terms and prohibit redistribution of source material where licence does not permit it.

### Restricted person-level data
Analysis occurs within the custodian's approved TRE/SDE. OSLT code may be deployed into that environment where approved, but raw person-level data are not exported to the general OSLT repository.

### Sensitive qualitative data
Use purpose-specific consent/authority, pseudonymisation, data minimisation and access segmentation. Public availability of a social-media item does not remove the need for an ethical/research-purpose assessment when constructing individual-level profiles.

### Output protection
Only disclosure-controlled, approved **aggregate** findings or other authorised outputs leave secure environments.

## 5. Source-validation checklist

Before any source becomes `ANALYSIS_READY`, record:

- custodian;
- legal/access route;
- coverage dates;
- population/denominator;
- inclusion/exclusion;
- variable definitions;
- coding/version changes;
- missingness;
- linkage process/error;
- collection purpose;
- ascertainment mechanism;
- known quality warnings;
- refresh frequency;
- reproducible extraction query;
- snapshot/content hash;
- transformations;
- source-family and dataset-family IDs for dependency control.

## 6. Key access findings as of 25 July 2026

- ONS SRS is an active TRE for accredited/approved researchers and publishes current project/dataset information.
- NHS England states that nearly all future planning, commissioning and research uses of data are intended to occur inside secure data environments.
- OpenSAFELY exposes primary-care, hospital and mortality datasets within its secure platform, with important topic-specific recording limitations that must be checked.
- DfE's NPD discovery tool can be used to identify required fields before a formal data application; DfE personal-data routes include its data-sharing service and ONS SRS pathways.
- Ofcom's 2026 programme provides both quantitative and qualitative youth media-use evidence and includes passive online measurement/online-experience components.
- OpenAlex provides a large scholarly graph via API and bulk snapshot suitable for publication/citation dependency analysis.
- Google Trends API remains alpha-access and provides a rolling five-year window.
- TikTok Research Tools require qualifying researcher/application status and expose defined categories of public platform data.
- UK Biobank new applications are currently paused, with new applications intended later in 2026; it should therefore be treated as P2 rather than a blocking dependency.
- NHS England published the current CYP gender-service specification on 1 April 2026 and describes a research programme including a core national dataset and longer-term follow-up ambitions.

The authoritative operational detail for each source is in `OSLT_DATA_SOURCE_REGISTER_v2_0_RC1.csv`; access conditions must be rechecked at the time of application.

## 7. Minimum viable discovery sequence

The minimum evidence programme should not wait for all 640 variables. Start with the smallest set capable of falsifying major rival explanations:

1. build outcome/referral/population time series and denominator model;
2. encode diagnostic/service/policy regime changes;
3. build academic/guideline/publication dependency graph;
4. build historical linguistic/content corpus;
5. obtain longitudinal clinical/neurodevelopmental/psychiatric timing data;
6. obtain school implementation/exposure data rather than guidance-only proxies;
7. obtain digital exposure/search data with active-search timing;
8. test rival explanations and identify irreducible data gaps;
9. commission primary experiments/qualitative studies only for those gaps;
10. replicate in independent jurisdictions/cohorts before high causal promotion.

## 8. Discovery completion criterion

A question is ready to enter confirmatory analysis only when:

- all variables required by its estimand/DAG have a source or an explicit unresolved-gap state;
- measurement validity and timing are defensible;
- primary and rival explanations have testable predictions;
- missingness, selection and ascertainment can be addressed or bounded;
- source dependencies are recorded;
- governance/ethics/access are authorised;
- a prespecified analysis and sensitivity plan exists.

Absence of data is not converted into evidence for or against a hypothesis.
