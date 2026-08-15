# OSL Research Kernel v1.1 — Hardened causal-research governance branch

**Purpose:** govern empirical claims in the gender dysphoria / gender incongruence research programme.  
**Boundary:** this is **not** the NHS clinical operating kernel, a diagnostic instrument, an identity classifier, a treatment recommender, or an ethics approval.

## Release status

```text
83 tests passed / 0 failed
94% product-code line coverage
8/8 targeted release mutations detected
16 registered research controls / 16 reachable from ClaimPipeline
640 candidate variables / 28 domains
36 dedicated H6 selection-disclosure-reverse-causation falsifier variables
```

The numbers above are engineering evidence only. They do not establish research validity, causal truth, clinical validity, ethics approval, lawful access to participant data, or deployment authority.

## Why v1.1 exists

Claude's v1.0 materially improved the earlier paper architecture by implementing the `CausalEvidenceObject`, typed claim/output states, prohibited shortcuts, an adjudication vector, a hash-chained journal, a rival/falsifier rule, and instrumentation auditing. It supplied a useful executable base.

A second adversarial review found several remaining ways a caller could overstate a claim or make methodologically weak comparisons. v1.1 therefore hardens the kernel around **evidence provenance, research governance, causal identification, neurodiversity measurement validity, statistical assurance, reproducibility, influence attribution, and academic-evidence dependency**.

## Highest-value changes from v1.0

### 1. Verified evidence is now operational
`UNVERIFIED` evidence can no longer establish a gate condition merely because it has a source ID.

### 2. Missing controls no longer disappear
Every registered control has an explicit applicability rule. Required authorisation controls block release when absent; missing structural/evidential controls cap the permitted claim.

### 3. Rival explanations are evidence-bearing
A caller cannot self-authorise a causal claim by setting a falsifier enum. Rival analyses require an analysis ID and verified evidence reference.

A rival that fully attenuates a target association produces `CAUSAL_EFFECT_NOT_IDENTIFIED`; it does **not** automatically prove the target mechanism false because mechanisms may coexist.

### 4. Raw publication/variable counts are not truth metrics
Raw instrumentation count remains an audit warning only. Confirmatory cross-hypothesis comparison requires a quality-parity profile covering construct coverage, measurement validity, temporal coverage and selection-control coverage.

### 5. H6 is now instrumented
The v2.1 ontology adds 36 variables specifically for selection, disclosure, ascertainment and reverse-causation explanations. The full ontology now contains 640 candidate variables across 28 domains.

### 6. Neurodiversity is a measurement layer, not a binary confounder
The kernel can require subgroup psychometrics and measurement-invariance evidence before causal interpretation of autistic/neurodivergent subgroup comparisons. Autism cannot be used as a proxy for incapacity or unreliable testimony.

### 7. Participant-data research has a governance gate
Where applicable, the kernel requires recorded evidence for sponsor, protocol, research/ethics routes, Article 6/Article 9 basis, confidentiality, DPIA, secure environment, purpose-specific authority for private digital/recording/genomic data, cross-person authority, PPI/justification, participant information/waiver, and withdrawal/objection arrangements.

The gate verifies that governance evidence exists; it **does not decide the correct lawful basis itself**.

### 8. Influence claims have identification requirements
- Digital/marketing/peer claims require baseline state, exposure timing, self-selection control, user-initiated vs algorithmic exposure, reverse-causation analysis, peer selection vs influence and a comparator/counterfactual.
- Conversation influence requires recording/research authority, baseline and post-interaction position, validated/blinded coding, inter-rater reliability and comparator/randomisation. Lexical alignment cannot itself establish persuasion.
- Academic influence requires dataset lineage, guideline ancestry, retraction/correction checks, validated stance coding and dual-human coding. Paper/citation count cannot establish truth.

### 9. Statistical assurance is explicit
Confirmatory work has power and multiplicity gates. A nominal 95% confidence interval or 90% power is never translated into “95% certainty that the conclusion is true.”

### 10. Reproducibility is cross-bound to the actual run
Dataset, code and environment SHA-256 values, protocol/data-dictionary versions and software/seed or deterministic-execution state are checked. The dataset hash in the reproducibility object must match the dataset hash supplied to the pipeline.

### 11. The research journal now records the control state
Journal records include typed replication state, the control-decision snapshot and reproducibility bindings. The JSONL hash chain is tamper-evident but is **not** claimed to be immutable production infrastructure.

## Claim boundaries

The kernel can express descriptive, associational and bounded causal evidence states. It cannot express an identity verdict.

Examples of structurally prohibited shortcuts include:

- identity true / identity false;
- genetics proves identity;
- private content proves identity or diagnosis;
- individual causal attribution from a group association;
- clinician bias inferred from affiliation alone;
- policy change proves negligence/harm;
- treatment response proves diagnostic validity;
- autism implies incapacity;
- neurodivergent communication implies unreliable testimony;
- paper count proves truth;
- citation count proves validity;
- linguistic alignment proves persuasion.

## Architecture

```text
osl_research/
  vocabulary.py              typed research outputs, claims and prohibitions
  evidence.py                verified provenance and findings
  decision.py                4-state decisions + guard registry
  estimand.py                CausalEvidenceObject + controls/null handling
  hypotheses.py              competing hypotheses, evidence-bearing rivals, parity
  guards.py                  structural claim and shortcut prohibitions
  research_governance.py     participant/special-category governance evidence
  measurement.py             validity + neurodiversity measurement invariance
  identification.py          temporality/reverse causation + selection/missingness
  statistical_assurance.py   multiplicity + power
  reproducibility.py         dataset/code/environment/version bindings
  dependency.py              academic evidence-dependency control
  influence_validity.py      consultation + digital/marketing influence validity
  adjudication.py            evidence-bound adjudication + persistent hash journal
  pipeline.py                single governed claim-release entry point
```

## Run the release checks

```bash
python -m pytest -q
python -m pytest -q --cov=osl_research --cov-report=term
python run_mutation_campaign.py
python demo_research_claim.py
python preflight_check.py
```

## Current limits

The kernel has not been:

- approved by an NHS/HRA research sponsor;
- reviewed/approved by a Research Ethics Committee;
- authorised for identifiable or special-category participant data;
- independently validated on a research cohort;
- demonstrated to recover known causal effects prospectively;
- validated for automated NLP coding of consultations or publications;
- clinically validated or authorised for patient-facing use.

Use the protocol, data-governance documentation, statistical analysis plan and independent methodological/ethical review before any participant-data study.
