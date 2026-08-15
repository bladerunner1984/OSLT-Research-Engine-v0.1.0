# OSL Research Kernel v1.1 — Engineering Validation Report

**Date:** 25 July 2026  
**Branch:** gender dysphoria / gender incongruence causal-research governance kernel  
**Maturity:** executable reference implementation; not ethics-approved, clinically validated or authorised for participant data.

## Release result

| Check | Result |
|---|---:|
| Unit/regression tests | **83 passed / 0 failed** |
| Product-only line coverage | **93.53% (reported as 94% rounded)** |
| Targeted release mutation campaign | **8/8 detected** |
| Registered research controls | **16** |
| Reachable controls from `ClaimPipeline.submit` | **16/16** |
| Product-module import reachability | **all product modules reached from pipeline** |
| Candidate variable ontology | **640 variables / 28 domains** |
| Dedicated H6 falsifier instrumentation | **36 variables** |
| Synthetic governed demo | **PASS** |
| Python compilation | **PASS** |
| Release pre-flight | **PASS** |

## What the tests establish

The suite exercises, among other things:

- evidence verification and caller-assertion boundaries;
- causal evidence object completeness, finite intervals and ratio-null handling;
- time-varying-confounding estimator restrictions;
- evidence-bearing rival/falsifier results;
- raw-count versus quality-based instrumentation parity;
- autism/neurodiversity measurement-invariance requirements;
- participant/special-category research governance evidence;
- digital/marketing exposure self-selection and reverse-causation controls;
- conversation-influence identification requirements;
- academic publication/dataset/guideline dependency controls;
- multiplicity and power controls;
- dataset/code/environment reproducibility hashes;
- typed structural prohibitions on identity/individual-attribution shortcuts;
- hash-chain alteration and duplicate-analysis detection;
- causal-claim caps for missing/weak/unverified controls;
- adjustment-set and dataset-hash cross-binding;
- control-decision/reproducibility snapshots in journal records;
- packaged demo execution using relative paths;
- no developer-local absolute paths in product/demo code;
- fail-closed guard-execution behaviour.

## Mutation sensitivity

Eight targeted faults are deliberately introduced one at a time. The suite detects all eight:

1. permit-to-block mutation in generic decision path;
2. structured prohibited-claim bypass;
3. unverified-evidence self-authorisation;
4. removal of dataset-hash cross-check;
5. quality-parity profile bypass;
6. rival-result verification bypass;
7. research-governance evidence bypass;
8. subgroup measurement-invariance bypass.

This is a targeted release mutation campaign, not a full surviving-mutant score across every expression in the codebase.

## Important v1.1 safety/method boundaries

1. **No identity verdict state exists.** The kernel cannot legitimately output whether an individual's identity is true/false.
2. **Group association cannot establish individual causation.**
3. **Autism/neurodivergence cannot be used as an incapacity or credibility proxy.**
4. **Private digital content cannot, by itself, establish diagnosis/identity.**
5. **Academic publication/citation volume is an influence metric, not evidence strength.**
6. **Lexical alignment is not persuasion without an identification design.**
7. **Policy change is not proof of historical harm/negligence.**
8. **A rival mechanism explaining an association does not automatically prove the target mechanism false.**
9. **Raw variable counts cannot authorise a confirmatory cross-hypothesis comparison.**
10. **90% power / 95% confidence intervals are not converted into probability that a causal conclusion is true.**

## Known limitations that remain intentionally open

### External research governance
The code cannot supply sponsor accountability, HRA/REC review, data-controller decisions, lawful-basis determinations, DPIA approval, participant information/consent arrangements or secure research infrastructure. It checks for recorded evidence of those decisions where applicable.

### Empirical validity
No real participant cohort has yet demonstrated that the ontology, causal DAGs, measurement models, language features, digital exposure features or adjudication thresholds recover valid effects.

### NLP and computational coding
Automated academic-stance, conversation and exposure coding must be validated against independently coded human reference sets before inferential use.

### Measurement invariance
The kernel can require measurement-invariance evidence; it does not itself establish that any specific scale is invariant across autistic/non-autistic or other subgroups.

### Journal immutability
The local JSONL hash chain is tamper-evident only. Production use requires external immutable/auditable infrastructure.

### Statistical thresholds
Reference thresholds such as the 0.80 power floor are governance floors, not universal sufficiency rules. Final studies require estimand-specific simulation and a preregistered statistical analysis plan.

## Honest maturity statement

`TESTED_REFERENCE_KERNEL != VALIDATED_RESEARCH_METHOD != ETHICS_APPROVED != LAWFULLY_AUTHORISED_DATA_USE != EMPIRICALLY_CONFIRMED_CAUSAL_RESULT`

The appropriate next gate is independent protocol/statistical/ethics/data-governance review followed by preregistered pilot validation, not stronger causal language in software.
