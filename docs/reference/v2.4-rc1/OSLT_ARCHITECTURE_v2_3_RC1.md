# OSLT Research Engine v2.3 RC1 - Architecture

## Purpose

OSLT is a multidisciplinary computational research architecture for investigating complex,
multicausal phenomena. It is not a diagnostic system, clinical decision-maker, or mechanism
for deciding the truth of an identity claim. Its job is to organise evidence, expose rival
explanations, select defensible methods, execute or specify reproducible analyses, and limit
claims to what the evidence and design can support.

The government-facing OSL lineage remains separate. OSLT is the research-engine branch.

## Core constitutional rules

1. A research objective and estimand are locked before confirmatory analysis.
2. VARIABLE IMPORTANCE != CAUSAL IMPORTANCE != EVIDENCE CERTAINTY.
3. Prediction is not causation.
4. Paper count, citation count, model agreement, or source prestige are never truth scores.
5. Interpretive methods may generate/test hypotheses but cannot independently establish a
   population causal effect.
6. Every important proposition must retrieve support, contradiction, rival explanations,
   methodological criticism, null findings, replication, and corrections/retractions where
   available.
7. Evidence dependence is collapsed before triangulation.
8. Historical terms are resolved within their time, jurisdiction and diagnostic regime.
9. Cross-kernel disagreement is not called a contradiction until construct, population,
   period, jurisdiction and estimand are aligned.
10. High-impact outputs fail closed into human review when risk criteria are met.
11. A model endpoint must qualify on an OSLT-specific benchmark; generic model rankings are
    insufficient.
12. Observations, measurements, associations, causal inferences, interpretations, simulations
    and recommendations retain explicit epistemic labels.

## System layers

### L0 - Scientific constitution
Research boundaries, neutrality, prohibited shortcuts, ethics, governance and claim ceilings.

### L1 - Objective and causal specification
ObjectiveLock, population/outcome definition, estimand, DAG/causal assumptions, preregistration,
versioned CausalSpecification and frozen confirmatory specification.

### L2 - Data/evidence acquisition
Structured administrative data, cohorts, surveys, research literature, historical archives,
policy/guideline corpora, school data, digital exposure data, narrative/qualitative material,
multimodal sources and new primary studies.

### L3 - Evidence fabric
Keyword, vector, hybrid, structured, graph and multimodal retrieval. Counter-RAG lanes retrieve
support, contradiction, rival, null, bias/critique, replication and correction/retraction evidence.

### L4 - Provenance and dependency
Every evidence object preserves source URI, version/time, location, retrieval query, hashes,
dataset/source family and dependency relations. Shared cohorts and citation/guideline ancestry
are detected before evidence is counted as independent.

### L5 - Method routing
The domain kernel and data-generating structure route the question to the applicable analytical
families. The current method register contains 100 analytical families spanning causal inference,
epidemiology, psychometrics, historical analysis, process tracing, corpus/diachronic linguistics,
content/discourse/narrative analysis, bibliometrics, network science and multimodal methods.

### L6 - Graph orchestration
Bounded nodes have explicit input/output schemas. Independent retrieval and analyst work fans out;
deterministic code performs deduplication, joins, filtering and routing; barriers are used only when
cross-set information is required. Controlled cycles use maximum rounds and loop-until-dry
convergence rules with deduplication against all previously seen findings.

### L7 - Multi-analyst adversarial harness
Primary analyst, rival analyst, methods critic and source verifier operate as distinct procedural
roles. Additional statistical/historical reviewers may be invoked. Model-vendor diversity is
optional and never contributes evidential weight.

### L8 - Cross-kernel contradiction and triangulation
ContradictionResolver distinguishes scope/construct/period/jurisdiction/estimand mismatch from
substantive contradiction. Triangulation then weights independent methodological/data families,
not raw analysis counts.

### L9 - Certainty and epistemic calibration
The CertaintyVector maintains 16 dimensions including statistical precision, measurement validity,
temporal/causal identification, confounding, selection, missing data, specification stability,
independence, convergence, replication, transportability, publication selection, provenance,
theory dependence and explanatory contribution.

### L10 - Claim verification and human review
Atomic claims are bound to evidence and classified by entailment. High-impact, clinically/policy
consequential, contradictory, novel, low-certainty or sensitive-population claims are escalated to
risk-based expert review.

### L11 - Reproducibility and release
Prompt/model/RAG/tool versions, code/environment/data hashes and evidence IDs are bound into run
manifests and the computation journal. ReleaseReadiness fails closed if a mandatory gate is absent.

## v2.3 additions

- OSLT-specific model qualification benchmark across 12 benchmark domains.
- Versioned and frozen causal specifications with hashes and parent lineage.
- Evidence completeness and discovery saturation diagnostics.
- Context-aware cross-kernel contradiction resolution.
- Explicit epistemic-status labelling of generated propositions.
- Risk-based human expert escalation.
- Execution budgets and circuit breakers for model calls, tokens, concurrency and wall-clock.
- Final release-readiness aggregation.
- Global-100 executable assurance overlay in addition to the 100-item architecture audit.

## Default scientific workflow

Objective lock -> discriminating question decomposition -> 7-lane Counter-RAG fan-out ->
deterministic evidence reduction -> dependency review -> parallel analyst roles -> verifier ->
contextual contradiction resolution -> certainty calibration -> synthesis -> atomic claim verification
-> human review (when required) -> reproducibility gate -> Global-100 -> release gate.

## Model policy

OSLT is model-agnostic. A deployment has a PRIMARY_FRONTIER alias selected only after an
OSLT-specific qualification benchmark. The default operating pattern is one qualified primary model
used across multiple procedurally independent agent roles. Economy models may be used only for
bounded schema-validated extraction/classification tasks. Model agreement is never evidential
replication.

## Data architecture invariant

The 640-variable ontology is retained. Each variable has a method crosswalk and candidate source
mapping. Candidate data availability never authorises a causal claim; field-level construct validity,
measurement timing, missingness, linkage quality and governance approval must be assessed per study.

## Audit markers

OSLT is an **experimental research architecture**. It is **not a clinical** decision authority.
Theory-dependent methods are explicitly bounded: interpretive conclusions remain **theory-dependent**
unless independently supported by empirical causal evidence.
