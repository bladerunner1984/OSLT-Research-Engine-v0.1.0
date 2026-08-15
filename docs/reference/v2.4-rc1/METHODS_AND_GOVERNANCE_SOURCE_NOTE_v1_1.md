# Methods and Governance Source Note — OSL Research Kernel v1.1

**Date checked:** 25 July 2026  
**Purpose:** current authoritative/source-method context for the research-kernel controls.  
**Important:** this note does not constitute HRA, REC, ICO, NHS England or legal approval.

## 1. NHS England clinical context

**NHS England — Service specification: NHS Children and Young People's Gender Service**  
Published 1 April 2026.  
https://www.england.nhs.uk/publication/service-specification-nhs-children-and-young-peoples-gender-service/

The current specification describes care for children and young people expressing gender incongruence and recognises that a significant proportion may have co-existing mental-health, neurodevelopmental, personal, family or social complexities whose relationship to gender incongruence may require careful exploration. The research programme therefore treats these factors as competing/modifying variables rather than presuming a single aetiology.

**Applicability:** direct contextual relevance to NHS CYP gender services in England; it is not itself a research-method standard and does not validate the OSL hypotheses.

## 2. UK health and social care research governance

**Health Research Authority — UK Policy Framework for Health and Social Care Research, version 3.4**  
Updated 28 April 2026.  
https://www.hra.nhs.uk/planning-and-improving-research/policies-standards-legislation/uk-policy-framework-health-social-care-research/uk-policy-framework-health-and-social-care-research/

The framework sets principles and responsibilities for health and social care research, including scientific/ethical conduct, participant choice, safety, competence, protocol compliance, transparency and accessible findings.

**HRA — Informing participants and seeking consent**  
Updated 24 April 2026.  
https://www.hra.nhs.uk/planning-and-improving-research/best-practice/informing-participants-and-seeking-consent/

The kernel's governance gate records evidence that the appropriate route, participant information/waiver and consent/choice arrangements have been resolved. It does not determine those arrangements itself.

## 3. UK data protection and sensitive inference

**Information Commissioner's Office — What is special category data?**  
https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/special-category-data/what-is-special-category-data/

ICO guidance states that intentional profiling/inference about special-category characteristics can itself constitute special-category processing regardless of confidence. This is particularly relevant to health, genetic data, sexual orientation and sex-life inference from private digital, clinical, conversation or genomic material.

**ICO — Research provisions**  
https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/the-research-provisions/what-are-the-research-provisions/

UK GDPR/DPA 2018 contain research provisions, but researchers still require the appropriate lawful basis/condition and safeguards. The OSL kernel therefore requires recorded governance evidence and fails closed on missing authority; it does not calculate or declare the lawful basis.

## 4. Reporting and methodological standards

### Observational studies
**STROBE — Strengthening the Reporting of Observational Studies in Epidemiology**  
https://www.strobe-statement.org/

STROBE provides reporting recommendations for cohort, case-control and cross-sectional studies. It is a reporting standard, not a causal-identification or risk-of-bias tool.

### Routinely collected health data
**RECORD — REporting of studies Conducted using Observational Routinely-collected Data**  
https://www.record-statement.org/

RECORD extends STROBE for research using routinely collected health data such as EHR/administrative/registry data. It is particularly relevant if OSL studies NHS records or linked datasets.

### Randomised trials
**CONSORT 2025**  
BMJ 2025;389:e081123.  
https://www.bmj.com/content/389/bmj-2024-081123

CONSORT 2025 supersedes CONSORT 2010 and provides a 30-item minimum reporting checklist plus participant-flow diagram for randomised trials. It becomes relevant to randomised clinician/vignette/communication experiments or future interventional studies.

### Non-randomised intervention studies
**ROBINS-I**  
https://www.riskofbias.info/welcome/home

ROBINS-I is used for risk-of-bias assessment in non-randomised intervention studies. A revised v2 draft was announced in November 2025. Study teams should verify the version appropriate to the final protocol/publication rather than silently treating a draft as mandatory.

## 5. Kernel-to-source mapping

| Kernel area | External methodological/governance rationale |
|---|---|
| `RCTRL-RESEARCH-GOVERNANCE` | HRA UK Policy Framework; HRA consent/participant information; ICO UK GDPR research/special-category requirements |
| `RCTRL-MEASUREMENT-VALIDITY` | General psychometric requirement; current NHS service context explicitly requires attention to neurodevelopmental complexity |
| `RCTRL-TEMPORAL-IDENTIFICATION` | Causal inference requirement to establish time order and address reverse causation |
| `RCTRL-SELECTION-BIAS` | STROBE/RECORD transparency plus causal selection/missingness identification |
| `RCTRL-MULTIPLICITY` / `RCTRL-POWER` | Statistical-analysis-plan discipline; CONSORT for randomised components |
| `RCTRL-REPRODUCIBILITY` | Protocol/version/data/code/environment traceability and open-science reproducibility principles |
| `RCTRL-ACADEMIC-DEPENDENCY` | Prevents bibliometric popularity from substituting for independent evidence quality |
| `RCTRL-CONVERSATION-INFLUENCE` | Requires authority plus an identification design before linguistic association can be called influence |
| `RCTRL-EXPOSURE-INFLUENCE` | Requires separation of exposure, self-selection, peer selection and reverse causation |

## 6. Reporting plan by study component

- Prospective observational cohort: **STROBE**.
- Routinely collected linked record study: **RECORD + STROBE**.
- Randomised clinician/vignette/communication experiment: **CONSORT 2025**.
- Non-randomised intervention/effect analysis: appropriate design-specific reporting plus **ROBINS-I** risk-of-bias assessment where applicable.
- Genomic analyses: use the relevant current genetic-association/reporting standard and statistical genetics guidance at protocol finalisation; no individual identity classification is permitted by OSL.
- Qualitative/linguistic components: use appropriate qualitative/NLP validation and reporting standards selected prospectively rather than retrofitted after results.

## 7. Evidence boundary

These sources justify the **methodological controls and governance questions**. They do not establish any empirical result about causation, diagnostic validity, treatment effect, social influence, academic bias, neurodevelopment, or individual identity.
