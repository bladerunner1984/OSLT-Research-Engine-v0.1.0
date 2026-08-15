# OSL Gender Dysphoria / Gender Incongruence Research Data Requirements v2.1

**Status:** research planning asset; not a diagnostic instrument or clinical recommendation.

Current candidate ontology: **640 variables across 28 domains**. Variable roles are candidate roles only and must be reassigned for each estimand/DAG.

## Domain inventory

| Domain | Candidate variables |
|---|---:|
| Methodological / statistical integrity | 60 |
| Neurodevelopmental | 52 |
| Clinical conversation / linguistic dynamics | 50 |
| Persuasion / marketing / exposure dynamics | 48 |
| Historical psychiatric / policy corpus | 40 |
| Academic influence / bibliometrics | 39 |
| Selection, disclosure and reverse-causation falsifiers | 36 |
| Psychodynamic / identity-process constructs | 35 |
| Outcomes | 27 |
| Healthcare pathway | 22 |
| Digital/social media | 20 |
| Psychiatric | 20 |
| Biological/physical | 18 |
| Clinician | 14 |
| Developmental | 14 |
| Diagnostic measurement | 14 |
| Institutional/service | 14 |
| Treatment | 13 |
| Education | 12 |
| Family/interpersonal | 12 |
| Genomic/family biology | 12 |
| Marketing/media/advocacy | 12 |
| Body image/sexual development | 10 |
| Cultural/religious/socioeconomic | 10 |
| Government/policy | 10 |
| Peer network | 10 |
| Minority stress/discrimination | 8 |
| Trauma/safeguarding | 8 |

## Minimum provenance required for every patient-level variable

- subject/person identifier separated from research pseudonym;
- source and acquisition method;
- event/sample/exposure time and availability time;
- instrument/device/platform version where applicable;
- direct measurement vs patient report vs clinician opinion vs derived feature;
- missingness state and reason where known;
- transformation/normalisation history;
- consent/authority/purpose state for private-context, transcript, family and genomic data;
- data-quality and measurement-validity state.

## High-priority neurodiversity data

Autism/ADHD should be represented both diagnostically and dimensionally where validated and appropriate. Candidate fields include diagnostic status and timing, autistic/ADHD traits, sensory and interoceptive profile, alexithymia, cognitive flexibility, intolerance of uncertainty, masking/camouflaging, executive function, pragmatic communication, learning differences, intellectual disability where relevant, accommodations and instrument/version provenance. General-population scale validity must not be assumed to transport to neurodivergent subgroups.

## Academic influence data

For each atomic proposition: publication identifier, date, stance, study design, population, dataset lineage, methodological quality, effect estimates, citation network, author/institution/funder metadata, retraction/correction state, guideline citations and guideline ancestry. Publication/citation volume is an influence metric, not a truth metric.

## Recorded consultation data

Where explicit recording and research-use authority exist: speaker-labelled transcript/audio provenance, baseline patient preferences, question structure, framing, option order, certainty/uncertainty language, authority markers, interruptions, speaking-time balance, shared-decision features, label introduction timing, lexical convergence, post-consultation preferences and later clinical decisions/outcomes.

## Persuasive / marketing / media exposure data

Time-stamped exposure intensity, source, source credibility, sponsored/commercial status, algorithmic vs search-initiated exposure, influencer/parasocial features, repetition, emotional framing, social proof, authority cues, peer endorsement, school/institutional exposure, counter-messaging, media literacy, baseline beliefs and prior content-seeking. Reverse causation and self-selection must be modelled.

## Historical psychiatry / policy corpus data

Versioned DSM/ICD definitions, NHS specifications, professional guidelines, training materials, policy documents, institutional statements and relevant literature. Each document requires publication/effective dates, authorship, provenance, supersession lineage and semantic-version representation. Patient outcome linkage additionally requires service/patient exposure and a credible counterfactual design.

## Outcome data

Use prospectively defined outcomes including distress, mental health, self-harm/suicidality, functioning, quality of life, body-image distress, persistence/change in gender-related experience, formulation/diagnosis change, treatment uptake/change/discontinuation, satisfaction, adverse physical/psychological outcomes, regret/re-identification/detransition/retransition using neutral definitions, healthcare utilisation, follow-up and patient-defined goal attainment.

## Statistical principle

No count of variables or participants establishes causal certainty. Final models require a defined estimand, time zero, DAG, measurement model, selection/missingness analysis, prespecified primary endpoints, multiplicity control, appropriate uncertainty intervals, falsification/negative controls and external replication.

## v2.1 H6 falsifier instrumentation expansion

Ontology v2.1 adds **36 dedicated variables** for the selection/disclosure/ascertainment/reverse-causation alternative (H6). These are required because an exposure-outcome association cannot distinguish causal influence from prior interest, self-selection, disclosure dynamics, referral/diagnostic ascertainment or loss-to-follow-up.

The added data family covers, where lawfully and ethically collectable: baseline gender-related distress/questioning; timing of active search and algorithmic recommendation; peer-tie formation relative to onset; baseline peer network; self-selection propensity; baseline social-media use; motivation for content access; user-initiated versus algorithmic exposure; first disclosure/help-seeking; referral threshold and service availability; clinic-inclusion probability; digital-substudy consent/participation; attrition and reasons; recall discrepancy; coding/terminology/documentation changes; pre-existing psychiatric/body-image/trauma timing; relevant policy/media shocks; negative controls; baseline treatment/formulation preferences; and time-varying recommendation propensity conditional on prior search.

These variables are **falsifier/identification variables, not proof of H6**. The analysis plan must preregister which are confounders, selection variables, negative controls, mediators or moderators for each estimand.
