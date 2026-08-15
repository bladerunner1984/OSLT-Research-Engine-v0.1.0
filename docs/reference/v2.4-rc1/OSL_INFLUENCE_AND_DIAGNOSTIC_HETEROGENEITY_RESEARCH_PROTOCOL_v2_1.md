# A Multimodal Causal Framework for Evaluating Diagnostic Heterogeneity, Neurodiversity, Academic and Communication Influence, and Clinical Outcomes in Gender Dysphoria/Gender Incongruence

**Draft protocol paper — OSL Research Kernel v1.1 / protocol v2.1**  
**Date:** 25 July 2026  
**Status:** Research protocol and methods paper. Not a diagnostic instrument. Not a treatment recommendation. No causal findings are claimed in this draft.

## Abstract

### Background
Gender dysphoria (DSM-5-TR) and gender incongruence (ICD-11) are descriptive clinical constructs rather than complete aetiological models. Current NHS England service design for children and young people explicitly requires holistic assessment, formulation of all important factors, consideration of mental-health and neurodevelopmental conditions including autism and ADHD, family/social context, differential diagnosis, and individualised care planning. At the same time, the historical literature, diagnostic frameworks, clinical guidelines, social context and referral populations have changed substantially over time. These features create a plausible methodological problem: similar descriptive presentations may arise through heterogeneous combinations of developmental, neurodevelopmental, psychiatric, biological, social, interpersonal, digital, institutional and healthcare mechanisms.

### Objective
To determine whether current descriptive case definitions sufficiently discriminate clinically relevant causal and prognostic subgroups, or whether a richer multimodal formulation materially improves prediction of distress, functional outcomes, persistence/change in reported gender-related experience, treatment selection, treatment response, adverse outcomes, satisfaction and longer-term health. Secondary objectives are to quantify the influence—without presuming causation—of neurodiversity, academic knowledge diffusion, clinician-patient communication, peer/digital exposure, persuasive communication and marketing, policy and diagnostic-framework change, and institutional decision dynamics.

### Methods
OSL will construct provenance-preserving longitudinal timelines from consented clinical, psychiatric, developmental, neurodevelopmental, family, educational, digital, social-network, communication-transcript, policy, research-corpus and, where separately authorised, genomic data. A 640-variable candidate ontology across 28 domains has been defined, including 36 dedicated selection/disclosure/ascertainment/reverse-causation falsifier variables for H6. Each analysis must specify an estimand, time zero, exposure, outcome, causal DAG, adjustment set, selection mechanism, measurement model and claim ceiling. High-dimensional discovery is separated from preregistered confirmation. Planned methods include multilevel longitudinal models, target-trial emulation where appropriate, interrupted time-series and difference-in-differences designs, social-network models separating selection from influence, psychometric measurement-invariance analysis, citation/guideline dependency graphs, NLP of consultation transcripts, dynamic corpus analysis, Bayesian sensitivity analysis, negative controls, specification curves and external replication.

### Statistical assurance
No single sample size can make a causal conclusion “95% certain.” Confirmatory analyses will generally target two-sided alpha 0.05, 90% statistical power for prespecified minimal effects, 95% confidence intervals, explicit multiplicity control, and independent external replication. Preliminary planning suggests a prospective index cohort of approximately 10,000 participants, enriched to at least 2,000 autistic/neurodivergent participants, plus an external replication cohort of at least 5,000, with nested digital, conversation and clinician-experiment substudies. Final sample sizes will be determined by simulation using observed event rates, clustering, attrition, repeated measures and interaction effects.

### Interpretation
OSL will not classify an identity as “true” or “false.” It will estimate which causal hypotheses are identified, contradicted, unsupported or unresolved; quantify uncertainty; test whether diagnostic criteria behave equivalently across subgroups; and determine whether additional variables improve prediction or treatment-effect stratification. Publication volume, citation count, professional consensus, social exposure, linguistic alignment, model agreement and statistical significance are explicitly prohibited from being promoted into causal truth without independent identification and validation.

---

# 1. Research rationale

The principal research problem is **diagnostic heterogeneity** rather than identity adjudication. A descriptive criterion can reliably identify a presentation without identifying why that presentation occurred or which intervention is optimal. The OSL research programme therefore separates four questions that are often conflated:

1. **Case definition:** Does the individual meet a descriptive diagnostic or service criterion?
2. **Aetiology/formulation:** Which factors plausibly contributed to the presentation and distress?
3. **Treatment indication:** Which intervention, if any, has an evidence-supported expected benefit-harm profile for this individual?
4. **Outcome:** What happened after the clinical decision, and can the effect be causally attributed?

The April 2026 NHS England Children and Young People’s Gender Service specification is directly compatible with this separation. It requires holistic assessment followed by formulation, relevant diagnoses and an individualised care plan; it specifically requires neurodevelopmental expertise and states that other clinical needs and family/social context can materially affect the individual pathway.

The research programme therefore tests whether OSL can make the formulation layer more explicit, measurable, reproducible and auditable.

# 2. Core falsifiable hypothesis

## Primary hypothesis

**H1 — Diagnostic heterogeneity/conflation:** Patients satisfying the same descriptive gender-dysphoria/gender-incongruence criteria comprise multiple clinically meaningful latent and/or causally distinct subgroups, and incorporating validated biological, developmental, neurodevelopmental, psychiatric, interpersonal, social, digital and contextual variables improves prospective prediction of outcomes beyond diagnostic criteria alone.

## Null hypothesis

**H0 — Adequate clinical discrimination:** Standard diagnostic/service criteria plus ordinary clinical assessment already capture the clinically meaningful information; the richer OSL variable set adds little reproducible incremental value after proper validation.

Neither result is presupposed.

# 3. Competing causal hypotheses

The confirmatory programme should preregister competing hypotheses rather than treating one explanatory framework as the default.

### H2 — Biological/developmental contribution
Biological, pubertal, endocrine, developmental and/or heritable factors contribute to onset, persistence or distress in some individuals.

### H3 — Neurodevelopmental interaction
Autism, ADHD and related neurodevelopmental traits modify measurement, interpretation, distress, communication, decision-making context, social exposure or outcome trajectories.

### H4 — Psychiatric/psychological interaction
Anxiety, depression, obsessive phenomena, trauma, dissociation, eating/body-image pathology, self-concept instability or other psychiatric/psychological factors modify presentation and/or outcomes.

### H5 — Social-influence contribution
Peer, digital, educational or cultural exposures causally influence timing, interpretation, expression, help-seeking or persistence in some individuals.

### H6 — Selection/disclosure alternative
Apparent social influence is substantially explained by pre-existing feelings leading individuals to seek related peers/content, increased vocabulary enabling disclosure, ascertainment effects, or combinations of these.

**Dedicated H6 instrumentation in ontology v2.1.** The programme now records 36 variables specifically intended to distinguish selection/disclosure/ascertainment/reverse-causation pathways from an exposure-causes-outcome interpretation. These include baseline questioning/distress, timing of first active search versus first algorithmic recommendation, peer-tie formation relative to onset, user-initiated versus algorithmic exposure, disclosure delay, referral threshold/service availability, clinic inclusion probability, digital-substudy participation, attrition/loss-to-follow-up, documentation/coding changes, negative controls and time-varying recommendation propensity conditional on prior search. These variables are falsifier instrumentation, not evidence that H6 is true.

### H7 — Minority-stress pathway
Stigma, rejection, discrimination and conflict primarily increase distress, self-harm risk and functional impairment rather than explain the origin of gender incongruence itself.

### H8 — Pubertal/body-image pathway
Pubertal development, body image, sexual development or sensory/interoceptive experience modifies the onset or severity of distress.

### H9 — Family/interpersonal pathway
Family dynamics, attachment, autonomy, interpersonal conflict and support modify distress, help-seeking, persistence or outcomes.

### H10 — Communication/influence pathway
Clinician, parent, peer or institutional language, framing, option presentation or lexical convergence influences preferences and clinical decisions in some encounters.

### H11 — Academic/institutional diffusion pathway
The structure of the academic literature and its transmission into guidelines, training, policy and clinical discourse affects diagnostic framing and management patterns independently of patient characteristics.

### H12 — Marketing/persuasion/exposure pathway
Repeated or strategically framed media, advocacy, commercial, educational or influencer messaging affects beliefs, vocabulary, help-seeking or intervention preferences in some individuals.

### H13 — Policy/diagnostic drift pathway
Changes in DSM/ICD terminology, service criteria, policy, referral thresholds, professional guidance or commissioning rules change recorded incidence and clinical management independent of changes in the underlying population phenotype.

### H14 — Heterogeneous pathways
No single explanation is sufficient; distinct subgroups show materially different combinations of mechanisms and outcomes.

# 3A. Executable claim-governance kernel

Protocol v2.1 is paired with **OSL Research Kernel v1.1**. The kernel does not estimate the scientific results by itself; it governs whether an analysis may be promoted into a descriptive, associational or bounded causal claim.

A released analysis is required, where applicable, to bind: verified provenance; a complete causal evidence object; research/data-governance evidence; measurement validity; temporal ordering/reverse-causation analysis; selection/missingness/ascertainment analysis; multiplicity and power; reproducibility hashes and versions; evidence-bearing rival explanations; negative/positive controls; and an evidence-bound seven-dimension adjudication vector.

For the specific influence hypotheses:

- **H5/H12 digital, peer and persuasive exposure:** the kernel requires exposure timing, baseline interest/belief, user-initiated versus algorithmic exposure separation, dose/intensity, self-selection modelling, reverse-causation sensitivity, peer selection versus influence, and a comparator/counterfactual.
- **H10 communication influence:** recording and research-use authority, pre/post position, validated/blinded coding, inter-rater reliability and comparator/randomisation are required before linguistic patterns can be promoted as influence.
- **H11 academic/guideline influence:** publication count is explicitly separated from evidence strength; dataset lineage, guideline ancestry, retractions/corrections, funding/conflicts and stance-classifier validation are required.
- **Neurodivergent subgroup claims:** subgroup psychometrics and measurement-invariance evidence are required before causal interpretation.

A rival analysis that materially attenuates an association does not automatically prove the target hypothesis false. It limits causal identification. Likewise, raw variable counts are an audit signal rather than a substitute for construct validity or equal measurement quality.

The kernel prohibits identity-validity verdicts, genomic individual identity classification, diagnosis from private content alone, individual causal attribution from group associations, treatment response as diagnostic proof, and inference of incapacity/unreliable testimony from autism or neurodivergent communication.

# 4. Neurodiversity and autism as a major analysis layer

Autism and broader neurodiversity must not be represented as a binary confounder only. The v2.1 OSL variable ontology therefore expands the neurodevelopmental domain to include:

- formal autism diagnosis, age at diagnosis and diagnostic pathway;
- ADHD diagnosis, age at diagnosis, attention regulation and impulsivity;
- social-communication differences;
- restricted/repetitive behaviour profile;
- sensory hyper- and hypo-reactivity;
- interoceptive differences;
- alexithymia;
- cognitive flexibility/set shifting;
- intolerance of uncertainty;
- executive function;
- hyperfocus/special-interest intensity;
- pragmatic/literal-language profile;
- masking/camouflaging and masking-related exhaustion;
- rejection sensitivity and social-threat processing;
- need for predictability/routine;
- learning disorders/dyslexia and intellectual disability;
- late recognition and possible sex-related ascertainment delay;
- diagnostic overshadowing;
- neurodivergence-specific communication and sensory accommodations;
- neurodivergent peer/community exposure;
- neurodevelopmental clinician expertise.

The research must test **measurement invariance**: a scale validated in the general population cannot be assumed to measure the same latent construct, with the same thresholds, in autistic and non-autistic participants. Autism also cannot be used as a proxy for incapacity or unreliability.

# 5. Academic influence and bibliometric analysis

The research can quantify academic influence, but **the number of papers supporting a proposition is not evidence that the proposition is true or false**. Publication volume is an exposure/diffusion variable.

## 5.1 Corpus construction

Use a preregistered search over OpenAlex, Crossref, Europe PMC/PubMed and relevant guideline bibliographies. Deduplicate by DOI/PMID/title and record retractions/corrections through Crossref/Retraction Watch metadata.

The unit of analysis is not “supports gender identity theory” as a single binary category. Each paper is stance-coded against specific propositions, for example:

- P1: diagnostic construct validity;
- P2: biological/developmental contribution;
- P3: social/peer/digital influence;
- P4: minority-stress contribution to distress;
- P5: effectiveness/harms of particular interventions;
- P6: persistence/change trajectories;
- P7: neurodevelopmental interaction;
- P8: guideline or diagnostic-framework validity.

For each proposition, classify the paper as:

`SUPPORTS / CHALLENGES / MIXED-CONDITIONAL / METHOD-ONLY / NOT-ASSESSABLE`.

Automated stance classification must be trained against blinded dual-human coding and independently validated before scaling.

## 5.2 Academic Influence Index

OSL should calculate separate dimensions, never one opaque score:

- annual publication volume;
- annual citation volume;
- field-normalised citation impact;
- number of genuinely independent primary datasets;
- systematic-review/meta-analysis count;
- guideline citation centrality;
- policy citation centrality;
- author/institution/funder network centrality;
- replication and independent-replication count;
- shared dataset/reused cohort dependence;
- guideline ancestry/dependency;
- self-citation rate;
- citation-cluster modularity;
- proportion of prospective/comparator/preregistered studies;
- risk-of-bias/evidence-quality distribution;
- retractions/corrections;
- citation asymmetry to contrary evidence;
- time from paper publication to guideline/policy incorporation;
- epistemic certainty and causal-language overstatement;
- funding/conflict disclosures.

The research question then becomes:

> Does academic diffusion predict subsequent guideline language, clinician discourse or treatment patterns after accounting for evidence quality, policy timing, secular trends and patient characteristics?

That is empirically testable. It is not established merely by finding a large number of papers with similar conclusions.

# 6. Recorded clinical conversations and linguistic influence

With explicit recording consent, separate research-use authorisation and revocation controls, consultation audio/video can be transformed into diarised transcripts and analysed using NLP plus blinded human coding.

## 6.1 Candidate linguistic variables

- speaker-specific speaking time;
- interruptions and turn taking;
- open versus closed questions;
- leading questions and presuppositions;
- gain/loss framing;
- percentage versus frequency risk framing;
- order and number of options presented;
- omitted material alternatives;
- clinician/patient certainty language and hedging;
- directive/paternalistic versus shared-decision language;
- empathy, validation and affiliation markers;
- clinician authority/clout markers;
- causal language;
- first introduction of diagnostic/identity terminology and by whom;
- lexical convergence/entrainment;
- repetition and priming of labels;
- challenge/disconfirmation questions;
- exploration of alternative explanations;
- checking understanding and teach-back;
- explicit discussion of evidence uncertainty;
- preference before and after consultation;
- parent/carer preference before and after consultation;
- emotional valence/arousal trajectory;
- silence/non-fluency markers;
- longitudinal language change across sessions.

## 6.2 Identification problem

Linguistic convergence can reflect rapport, common vocabulary or pre-existing agreement rather than persuasion. Therefore OSL cannot label language as causal influence unless it can establish, at minimum:

1. validated linguistic measurement;
2. baseline preference/attitude before the interaction;
3. temporal ordering;
4. comparator or experimental variation;
5. alternative-explanation control;
6. replication.

Randomised vignette/communication experiments should therefore complement observational conversation analysis.

# 7. Propaganda, marketing and persuasion theory

The term “propaganda” should not be used as a deterministic causal label in the statistical model. The measurable construct is **persuasive communication exposure**.

Candidate mechanisms include:

- repeated exposure/mere exposure;
- source credibility and authority cues;
- social proof/normative consensus;
- influencer and parasocial exposure;
- peer endorsement;
- identity-based framing;
- emotional, moral, fear, hope or relief framing;
- urgency/scarcity cues;
- narrative/testimonial persuasion;
- sponsored/commercial-provider content;
- advocacy campaigns;
- institutional branding;
- school/education messaging;
- algorithmic amplification;
- homophilic network concentration;
- exposure to countervailing information;
- viewpoint diversity;
- media literacy/persuasion knowledge;
- baseline need for belonging/social approval;
- conformity orientation and psychological reactance.

The study must separate **search-initiated exposure** from **algorithm-initiated exposure**, because this distinction is central to reverse causation: a person may encounter content because an existing concern caused them to seek it.

# 8. Psychodynamic and identity-process variables

Psychodynamic constructs may be included only as **theory-contingent hypotheses**, not presumed mechanisms. Candidate variables include attachment, identity integration/diffusion, self-concept clarity, mentalisation, affect regulation, experiential avoidance, dissociation, depersonalisation, body-self integration, shame, interpersonal dependency, autonomy, family enmeshment, narrative identity coherence, meaning attributed to puberty/body distress, expectancy of relief from intervention, therapeutic alliance and alliance rupture/repair.

Where constructs lack robust measurement validity, OSL must downgrade them to exploratory status. Expert psychodynamic formulation is a research interpretation, not a diagnostic fact.

# 9. Historical psychiatry, diagnostic criteria and corpus analysis

The historical corpus should include every obtainable version of:

- DSM and ICD diagnostic frameworks;
- NHS service specifications and commissioning policies;
- professional clinical guidelines;
- systematic evidence reviews;
- professional-body statements;
- relevant medical-school/training material where lawfully accessible;
- policy documents and consultation reports;
- research literature and major review papers.

OSL can compute time series for:

- diagnostic terminology;
- inclusion/exclusion criteria;
- distress/impairment requirements;
- duration/age requirements;
- pathologising/depathologising language;
- biological, psychosocial, social-influence and minority-stress explanations;
- differential-diagnosis emphasis;
- autism/neurodevelopment references;
- trauma/psychiatric-comorbidity references;
- family/social-context emphasis;
- treatment recommendations;
- certainty/uncertainty language;
- evidence-grading standards;
- guideline dependency and citation ancestry.

Dynamic topic models, sentence embeddings, supervised claim extraction and change-point detection can identify semantic shifts. These shifts are then linked to separately measured policy, training, referral and patient-level variables.

A corpus shift alone cannot establish that the shift caused a patient outcome.

# 10. Study architecture

## Study A — National retrospective longitudinal linkage

**Purpose:** characterise epidemiology, service exposure, neurodevelopmental/psychiatric comorbidity, treatment pathways and outcomes across time.

Target: use the full eligible national cohort where lawful linkage is possible rather than sampling. Include matched general-population and clinically relevant comparator groups.

## Study B — Prospective inception cohort

Recruit participants near first specialist referral/assessment, before major treatment decisions where possible.

**Planning target:** approximately **10,000 index participants**, intentionally enriched to at least **2,000 autistic/neurodivergent participants**, with repeated follow-up for at least 5 years and preferably 10 years. A 25% attrition allowance leaves approximately 7,500 complete-follow-up equivalents.

An external independently governed replication cohort should target **at least 5,000** additional participants.

## Study C — Digital exposure and peer-network subcohort

Approximately **3,000 consented participants**, with prospective digital-exposure measurement rather than retrospective memory alone. Record search-initiated versus algorithm-initiated exposure and longitudinal peer-network structure. Oversample neurodivergent participants.

## Study D — Consultation/conversation corpus

Approximately **2,000 recorded clinical consultations**, across at least **300 clinicians** and **10+ services/sites**, with baseline and post-consultation patient/parent preferences. Use cross-classified multilevel models because consultations are nested within patients and clinicians/sites.

## Study E — Randomised clinician communication/vignette experiment

Target approximately **2,400 clinicians/qualified assessors** across multiple arms. For orientation, a simple two-group comparison requires roughly 527 participants per group for 90% power to detect a small standardised effect of d=0.20 at alpha 0.05; a multi-arm factorial study therefore needs materially more after clustering, exclusions and interaction tests.

Manipulate one factor at a time where feasible: wording/frame, autism disclosure, psychiatric history, social-media history, family context, or the order in which information is presented. Patient facts otherwise remain identical.

## Study F — Academic/policy corpus

Use the **entire identified corpus**, not a sample, for bibliometric metadata. For stance/risk-of-bias classifier development, manually double-code a stratified validation set of at least **2,000 papers/abstracts**, with full-text adjudication for clinically influential papers and guideline ancestors.

## Study G — Genomic/family sub-study

Only where separately consented and ethically approved. Common polygenic or gene-environment interaction work will generally require far larger cohorts than the core prospective study; **20,000–50,000+** participants or access to suitable controlled datasets may be required for stable small-effect estimates. Genomic associations must not be used as an identity classifier.

# 11. Why 95% confidence is not a sufficient study criterion

A 95% confidence interval does **not** mean there is a 95% probability that the hypothesis is true. OSL Research Kernel v1.1 therefore prohibits `95% CI -> 95% certainty` and `p < 0.05 -> hypothesis true` transformations.

For simple planning:

- estimating a proportion near 50% to ±5 percentage points at 95% confidence requires about **385** independent observations;
- ±3 points requires about **1,068**;
- ±2 points requires about **2,401**.

Those numbers address **precision of one proportion only**. They do not cover confounding, interaction effects, clustering, attrition, rare outcomes or causal inference.

For a simple binary-outcome example with baseline risk 20%:

- detecting 25% versus 20% at 90% power and alpha 0.05 requires roughly **1,450 participants per group**;
- detecting 23% versus 20% requires roughly **3,900 per group**.

Consequently, small subgroup interactions rapidly push the required cohort into the many-thousands. The final OSL protocol should calculate sample size by simulation from the observed event rate, expected minimal effect, number of sites/clinicians, intraclass correlation, repeated measures, attrition and interaction structure.

# 12. Statistical analysis plan

## 12.1 Confirmatory principles

- preregister primary hypotheses and estimands;
- alpha 0.05, two-sided unless scientifically justified otherwise;
- target 90% power for primary prespecified effects;
- report 95% confidence intervals;
- prespecify a minimal clinically meaningful effect;
- control family-wise error for primary confirmatory hypothesis families;
- control false discovery rate for high-dimensional secondary analyses;
- preserve exploratory results as exploratory until independent replication.

## 12.2 Longitudinal models

Depending on outcome type:

- mixed-effects linear/generalised models;
- recurrent-event models;
- survival/time-to-event models;
- joint longitudinal-survival models;
- marginal structural models for time-varying treatment/exposure/confounding;
- target-trial emulation when the clinical question and data permit.

## 12.3 Social-network influence

Use longitudinal network methods capable of jointly modelling **selection/homophily and influence**, rather than correlating a participant's outcome with friends' outcomes.

## 12.4 Policy and historical effects

Use:

- interrupted time series;
- segmented regression;
- event studies;
- difference-in-differences where parallel-trend assumptions are credible;
- synthetic controls where suitable comparator jurisdictions exist;
- negative-control dates/outcomes.

## 12.5 Heterogeneity

Exploratory methods can include latent class analysis, growth-mixture models, causal forests and unsupervised clustering. Any discovered subtype must be stable, externally replicated and clinically validated before being described as a clinical entity.

## 12.6 Bayesian sensitivity

Bayesian models may quantify posterior uncertainty **only where priors are explicit and sensitivity to priors is reported**. Posterior probability must not be confused with frequentist confidence intervals.

## 12.7 Robustness

Required:

- negative-control exposures/outcomes;
- placebo-time tests;
- unmeasured-confounding sensitivity analysis;
- specification curves/multiverse analysis;
- alternative DAGs;
- missing-data sensitivity;
- transportability analysis;
- external replication.

# 13. OSL evidence adjudication kernel

OSL should not emit a single opaque “truth score.” For every substantive hypothesis it should produce an **Evidence Adjudication Vector**:

1. methodological quality;
2. causal identification;
3. measurement validity;
4. selection-bias control;
5. replication;
6. transportability;
7. provenance integrity.

The claim ceiling is controlled by the weakest material dimension. A geometric summary score may be used for prioritisation but must never be rendered as “probability the hypothesis is true.”

Suggested claim states:

- `NOT_ASSESSABLE`;
- `DESCRIPTIVE_EVIDENCE_ONLY`;
- `ASSOCIATION_OBSERVED`;
- `CAUSAL_EFFECT_NOT_IDENTIFIED`;
- `LIMITED_CAUSAL_EVIDENCE`;
- `MODERATE_TRIANGULATED_CAUSAL_EVIDENCE`;
- `STRONG_REPLICATED_CAUSAL_EVIDENCE`;
- `CONTRADICTED_BY_HIGHER_QUALITY_EVIDENCE`.

# 14. Primary outcomes

The study should not define “identity truth” as an outcome. Clinically meaningful outcomes include:

- gender-related distress severity;
- general psychological distress;
- depression/anxiety;
- self-harm/suicidality;
- functioning at school/work;
- social functioning;
- quality of life;
- body-image distress;
- reported gender-incongruence persistence/change over time;
- diagnostic/formulation change;
- treatment initiation/change/discontinuation;
- treatment satisfaction;
- adverse physical effects;
- adverse psychological effects;
- regret, re-identification, detransition and retransition where defined neutrally and measured prospectively;
- healthcare utilisation;
- adherence/follow-up;
- patient-defined goals and goal attainment.

# 15. Required bias and alternative-explanation controls

Every analysis must explicitly test or discuss:

- referral/clinic selection bias;
- survivorship bias;
- loss-to-follow-up bias;
- diagnostic ascertainment change;
- calendar-time effects;
- age/puberty confounding;
- psychiatric/neurodevelopmental comorbidity;
- minority stress;
- family support/conflict;
- socioeconomic and cultural factors;
- social selection/homophily;
- reverse causation;
- collider bias;
- mediation;
- clinician/site clustering;
- treatment-by-indication bias;
- measurement non-invariance;
- missing-not-at-random data;
- publication and citation bias;
- guideline ancestry/dependence;
- policy and service-availability changes;
- expectancy/placebo/nocebo/context effects;
- researcher degrees of freedom.

# 16. Ethics, consent and data governance

The proposed combined dataset—clinical records, psychiatric history, neurodevelopmental assessments, private messages, digital traces, recorded consultations and genomic data—would be exceptionally sensitive. Each source requires a purpose-specific governance basis and data minimisation.

Conversation recording requires explicit recording consent and separate research-use authority. Social-media or email availability does not itself authorise clinical inference. Family-member data cannot be analysed under another person's consent. Genomic processing requires separate consent/governance. Research should use pseudonymisation, role-based access, secure research environments, data separation and independent ethics/data-governance review.

# 17. Predefined interpretive rules

The research kernel must enforce:

- autism association ≠ aetiology;
- autism ≠ incapacity;
- neurodivergent communication ≠ unreliable testimony;
- publication count ≠ evidence strength;
- citation count ≠ truth;
- citation-network density ≠ independent replication;
- linguistic alignment ≠ persuasion;
- recording availability ≠ research permission;
- leading language ≠ causal influence without identification;
- persuasive exposure ≠ deterministic outcome;
- semantic/policy change ≠ patient-level causal effect;
- model fit ≠ causal identification;
- p-value ≠ probability hypothesis is true;
- 95% confidence interval ≠ 95% certainty;
- latent class ≠ diagnosis;
- discovery dataset ≠ confirmation;
- training/derivation dataset ≠ external validation;
- multi-model agreement ≠ causal certainty;
- guideline descendants ≠ independent evidence.

# 18. Proposed contribution

The project would contribute a reproducible method for asking a question that is frequently addressed through polarised narrative rather than appropriately identified causal designs: whether current gender-dysphoria/gender-incongruence presentations are clinically homogeneous enough for existing diagnostic constructs to serve as adequate prognostic/treatment proxies, or whether clinically important causal heterogeneity is being obscured.

The study is deliberately capable of falsifying the motivating concern. If diagnostic criteria plus ordinary assessment outperform or equal the richer OSL formulation, social/academic/communication effects attenuate after proper confounding and selection control, and findings replicate across settings, the diagnostic-conflation hypothesis would be weakened. If distinct reproducible subgroups, exposure effects, measurement non-invariance or institutional decision effects remain after robust causal controls and predict materially different outcomes, that would justify refinement of assessment, research and potentially clinical formulation.

# References and source infrastructure

1. NHS England. *Service specification: NHS Children and Young People’s Gender Service*. 1 April 2026. https://www.england.nhs.uk/publication/service-specification-nhs-children-and-young-peoples-gender-service/
2. WHO. *Gender incongruence and transgender health in the ICD*. https://www.who.int/standards/classifications/frequently-asked-questions/gender-incongruence-and-transgender-health-in-the-icd
3. Mears K, Rai D, Shah P, Cooper K, Ashwin C. *A Systematic Review of Gender Dysphoria Measures in Autistic Samples*. Arch Sex Behav. 2024. PMID 38831234. https://pubmed.ncbi.nlm.nih.gov/38831234/
4. Kallitsounaki A, Williams DM. *Autism Spectrum Disorder and Gender Dysphoria/Incongruence: A systematic Literature Review and Meta-Analysis*. J Autism Dev Disord. 2023. PMID 35596023. https://pubmed.ncbi.nlm.nih.gov/35596023/
5. Rea HM et al. *Gender Diversity, Gender Dysphoria/Incongruence, and the Intersection with Autism Spectrum Disorders: An Updated Scoping Review*. J Autism Dev Disord. 2026. PMID 39630339. https://pubmed.ncbi.nlm.nih.gov/39630339/
6. Avci H, Baams L, Kretschmer T. *A Systematic Review of Social Media Use and Adolescent Identity Development*. Adolesc Res Rev. 2025. PMID 40385471. https://pubmed.ncbi.nlm.nih.gov/40385471/
7. Brechwald WA, Prinstein MJ et al. *Peer influence on gender identity development in adolescence*. 2016. PMID 27584667. https://pubmed.ncbi.nlm.nih.gov/27584667/
8. Riedl D, Schüßler G. *The Influence of Doctor-Patient Communication on Health Outcomes: A Systematic Review*. 2017. PMID 28585507. https://pubmed.ncbi.nlm.nih.gov/28585507/
9. Tan Z, Sun Z, Lin Y. *How Physician Communication Style Shapes Patient Trust: A Systematic Review*. Health Commun. 2026. PMID 42410925. https://pubmed.ncbi.nlm.nih.gov/42410925/
10. Zhou Y et al. *What Does Patient-Centered Communication Look Like? Linguistic Markers...*. Health Commun. 2023. PMID 34657522. https://pubmed.ncbi.nlm.nih.gov/34657522/
11. Taylor J et al. *Clinical guidelines for children and adolescents experiencing gender dysphoria or incongruence: a systematic review of guideline quality (part 1)*. Arch Dis Child. 2024. PMID 38594049. https://pubmed.ncbi.nlm.nih.gov/38594049/
12. Surís A et al. *The Evolution of the Classification of Psychiatric Disorders*. Behav Sci. 2016. PMID 26797641. https://pubmed.ncbi.nlm.nih.gov/26797641/
13. Fabiano F, Haslam N. *Diagnostic inflation in the DSM: A meta-analysis...*. Clin Psychol Rev. 2020. PMID 32736153. https://pubmed.ncbi.nlm.nih.gov/32736153/
14. OpenAlex API documentation. https://developers.openalex.org/api-reference/works
15. Crossref REST API documentation. https://www.crossref.org/documentation/retrieve-metadata/rest-api/
16. Crossref Retraction Watch production data. https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/
17. Europe PMC REST API. https://europepmc.org/RestfulWebService

