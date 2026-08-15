# Claude v1.0 Review and OSL Research Kernel v1.1 Optimisation Report

**Date:** 25 July 2026  
**Reviewed input:** `OSL_Research_Kernel_v1_0.zip` and accompanying README  
**Resulting branch:** OSL Research Kernel v1.1 HARDENED

## Executive assessment

Claude's v1.0 added substantial value. It turned several previously documented research-governance concepts into executable software: a 21-binding causal evidence object, typed research-output/claim states, a seven-dimension adjudication vector, prohibited-shortcut guards, a hash-chained research journal, a competing-hypothesis registry, a falsifier rule and an instrumentation audit.

The original package was executable and reproducible: its supplied test suite ran **30/30 passing tests**. The central direction was sound: research claims should be governed by an auditable kernel rather than produced directly from model prose.

However, independent review identified several methodological and anti-self-authorisation gaps. v1.1 fixes the material software issues that can be addressed without real study data, research approvals or external validation.

## Findings and disposition

| Finding in v1.0 | Risk | v1.1 disposition |
|---|---|---|
| UNVERIFIED evidence could establish a condition | Caller could present unverified provenance as operative evidence | **Fixed.** Only VERIFIED establishing derivations can establish a gate |
| Missing guard input did not reliably degrade claims | Missing evidence could disappear into the pipeline | **Fixed.** applicability + missing ceilings; authorisation absence blocks |
| Falsifier state was caller-supplied | Caller could self-authorise causal promotion | **Fixed.** evidence-bearing `RivalExplanationResult` required |
| Rival explanation automatically implied target contradiction | Competing/coexisting mechanisms could be falsely treated as mutually exclusive | **Fixed.** full attenuation yields `CAUSAL_EFFECT_NOT_IDENTIFIED`, not automatic falsity |
| Raw variable count acted as parity gate | Quantity could substitute for validity | **Fixed.** raw count = warning only; confirmatory comparison requires quality profiles |
| `max_claim_permitted` not enforced in release pipeline | Evidence object's own ceiling could be bypassed | **Fixed** |
| Adjustment-set guard not cross-bound to evidence object | Clean adjustment list could authorise a different fitted model | **Fixed** |
| Negative/positive controls lacked adequate provenance semantics | Caller booleans could overstate control performance | **Hardened.** evidence refs required; positive-control failure makes analysis not assessable |
| Interval logic implicitly treated null as zero | Incorrect for ratios | **Fixed.** explicit `null_value` supports RR/OR null=1 |
| Adjudication scores were unaudited caller numbers | Subjective scoring could lift a claim | **Fixed.** all seven dimensions can require evidence refs; unverified dimensions cap at association |
| Journal was in-memory only | Weak audit/reproducibility | **Hardened.** optional JSONL persistence, duplicate IDs refused, load-time chain verification |
| Prohibited text sweep relied on exact tokens | Paraphrase could bypass | **Fixed structurally.** typed `ClaimScope` is primary; text sweep is defence-in-depth |
| No participant/special-category governance gate | Sensitive-data study could be technically processed without research governance evidence | **Fixed at reference level.** governance evidence gate added; kernel does not decide lawful basis |
| No neurodiversity measurement-invariance gate | General-population scales could be assumed valid in autistic/neurodivergent subgroups | **Fixed** |
| No explicit temporal/reverse-causation gate | Exposure association could be called influence without ordering/sensitivity evidence | **Fixed** |
| No selection/missingness/referral ascertainment gate | Referral/attrition mechanisms could be mistaken for population effects | **Fixed** |
| No multiplicity/power gate | Discovery multiplicity/underpowering could be hidden | **Fixed** |
| No reproducibility gate | Dataset/code/environment drift not bound to claim | **Fixed and cross-bound to pipeline dataset hash** |
| No academic evidence-dependency control | Paper/citation counts could be mistaken for independent evidence | **Fixed** |
| No conversation-influence identification control | Lexical alignment could be mistaken for persuasion | **Fixed** |
| No digital/marketing influence validity control | Exposure could be confused with self-selection/reverse causation | **Fixed** |
| H6 falsifier had inadequate dedicated instrumentation | Social-influence hypothesis lacked its strongest competing explanation | **Fixed in ontology v2.1:** 36 dedicated H6 variables |
| Reachability report was registry-level only | Risk of confusing registration with runtime reachability | **Hardened.** import-graph regression test confirms all product modules reachable from pipeline; all 16 controls register through single entry point |
| Mutation sensitivity too narrow | Constant-refusal test alone did not test key bypasses | **Hardened.** 8 targeted release mutations, all detected |
| Demo contained Claude-local absolute path and was stale | Shipped package demo could not run elsewhere | **Fixed.** relative ontology path, v1.1 governed scenarios, test asserts no developer-local paths |

## Further v1.1 refinement beyond the defect list

### Reproducibility object is now bound to the actual pipeline invocation
A valid SHA-256 in a reproducibility record is insufficient if it describes a different dataset. The pipeline checks that the recorded dataset snapshot hash equals the actual `dataset_snapshot_hash` submitted for the analysis. A mismatch makes the claim `NOT_ASSESSABLE`.

### Journal records the governance snapshot
Each released journal record now stores:

- typed replication state;
- the control ID/outcome/ceiling snapshot;
- dataset/code/environment hashes;
- protocol and data-dictionary versions;
- the prior hash and current record hash.

This improves auditability while retaining the explicit limitation that a local JSONL chain is tamper-evident rather than production-immutable.

### Instrumentation parity is no longer allowed to fall back to raw counts
For a confirmatory cross-hypothesis comparison, raw indicator numbers cannot substitute for construct/validity/temporal/selection-control profiles. If no quality profile is supplied, the comparison is capped.

## Release engineering result

The v1.1 release candidate currently records:

- **83 tests passed / 0 failed**;
- **94% product-only line coverage**;
- **8/8 targeted release mutations detected**;
- **16 registered controls / 16 reachable**;
- **640 candidate variables across 28 domains**;
- **36 variables dedicated to H6 selection/disclosure/ascertainment/reverse-causation falsification**.

These are software-engineering results. They are not evidence that any causal hypothesis is true and are not clinical/research validation.

## Remaining non-software gates

Before participant-level research, the programme still needs, as applicable:

1. sponsor and chief investigator arrangements;
2. a final version-controlled protocol and statistical analysis plan;
3. HRA/REC and other applicable approvals/assessments;
4. a documented UK GDPR/DPA 2018 lawful basis and special-category condition determined by the accountable organisation;
5. DPIA and secure research environment controls;
6. participant information/consent or an approved alternative route where applicable;
7. independent psychometric validation and measurement-invariance work;
8. validated NLP/stance/conversation coding against blinded human standards;
9. cohort recruitment, power simulations and prospective data collection;
10. independent replication and publication under appropriate reporting standards.

## Bottom line

Claude v1.0 was a useful architectural advance, not a finished research engine. v1.1 preserves its strongest concepts while closing the principal self-authorisation, confounding, measurement, selection, governance and reproducibility gaps found in adversarial review. The next scientifically valuable step is no longer to add conclusions to the kernel; it is to formalise the protocol/SAP and obtain independent methodological, ethical and data-governance review before any real participant-data study.
