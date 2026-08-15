# OSLT Research Engine v2.2 RC1 — Governed Evidence & Reasoning Architecture

**Release:** 2.1.0rc1  
**Branch:** OSLT research-engine branch; separate from the government-facing OSL artefact.  
**Status:** research architecture and study-planning/execution-governance release candidate; not empirical validation.

## 1. Objective and scientific boundary

OSLT is an **experimental research architecture** for multidisciplinary investigation of complex, multicausal changes. It is **not a clinical** decision system, diagnostic device or patient-level causal classifier. It does not determine whether an identity is true or false and it prohibits individual causal attribution from group-level associations.

The system is objective-locked before analysis. It must compare **rival** explanations and deliberately search for evidence capable of defeating the target explanation.

The constitutional distinction remains:

> **VARIABLE IMPORTANCE ≠ CAUSAL IMPORTANCE ≠ EVIDENCE CERTAINTY.**

Theory-dependent methods are bounded: psychodynamic, critical-discourse, narrative and other interpretive methods may generate or test interpretations, but no **theory-dependent** output can independently establish population-level causation.

## 2. v2.1 architectural change

v2.0 hardened the scientific kernel. v2.1 adds the governed outer execution fabric:

```text
OBJECTIVE LOCK
    ↓
QUESTION DECOMPOSITION
    ↓
TEMPORAL / JURISDICTION / CONCEPT RESOLUTION
    ↓
BALANCED EVIDENCE FABRIC
 keyword + vector + structured + graph + multimodal
    ↓
COUNTER-RAG
 support / contradict / rival / null / bias / replication / correction
    ↓
DEPENDENCY + PROVENANCE GRAPH
    ↓
CONTEXT-BUDGETED EVIDENCE PACK
    ↓
DOMAIN KERNEL + METHOD ROUTER
    ↓
MULTI-ANALYST / BLINDED HARNESS
 primary / rival / methods critic / source verifier
    ↓
STATISTICAL / HISTORICAL / INTERPRETIVE TOOLS
    ↓
RIVAL-EXPLANATION DISTILLATION
    ↓
INDEPENDENCE-AWARE TRIANGULATION
    ↓
16-DIMENSION CERTAINTY
    ↓
ATOMIC CLAIM ↔ EVIDENCE VERIFICATION
    ↓
RELEASE-READINESS GATE
    ↓
GLOBAL-100 ANTI-DRIFT AUDIT
```

## 3. Evidence fabric

OSLT does not treat generic vector retrieval as sufficient. `RetrievalMode` distinguishes KEYWORD, VECTOR, HYBRID, STRUCTURED, GRAPH and MULTIMODAL retrieval. Structured quantitative datasets are queried as structured data rather than being reduced to text chunks.

Every retrieved evidence object binds source URI, document and chunk hashes, retrieval query, retrieval mode, rank, lane, date, jurisdiction, source/dataset family and bias signatures.

## 4. Counter-RAG and evidence balance

Major propositions are searched through separate evidence lanes:

- SUPPORT
- CONTRADICT
- RIVAL
- NULL
- BIAS_CRITIQUE
- REPLICATION
- CORRECTION_RETRACTION

A missing required lane is a formal warning/blocking condition rather than an invisible retrieval failure.

## 5. Temporal and conceptual discipline

Historical evidence is filtered by publication/effective dates, jurisdiction, policy regime and diagnostic regime. `ConceptResolver` prevents terminology from different historical periods being silently treated as equivalent. Ambiguous resolution is surfaced explicitly.

## 6. Evidence dependency

`EvidenceDependencyGraph` represents shared datasets/cohorts, derivation, research groups, funding, citation and guideline ancestry. Multiple papers from one evidential family are not counted as independent replication.

## 7. Context management

`ContextBudget` prevents a large evidence class from crowding out rivals. Budgeting is lane-aware and deterministic. If the context budget removes a required counterevidence lane, the pack becomes unbalanced rather than silently proceeding.

## 8. Analytical blinding and multi-analyst harness

Independent analytical roles are specified for important propositions:

- primary analyst;
- rival-hypothesis analyst;
- methods critic;
- source verifier;
- optional statistical/historical specialist reviewers.

Cross-domain results can be sealed until prespecified analyses are complete. Model agreement is not treated as independent empirical evidence.

## 9. Security boundary

Retrieved text, webpages, tool outputs and documents are **UNTRUSTED_EXTERNAL_DATA**. They are structurally isolated from system/control instructions. Instruction-like content is quarantined and logged; retrieval content cannot change the OSLT constitution or authorise tools.

Tools are role-scoped under least privilege. Irreversible/high-impact actions are disabled by default.

## 10. Reproducibility

The execution manifest binds the scientific run to kernel version, wrapper version, RAG version, model identifier, system/method prompt hashes, evidence-pack hash, tool versions and exact retrieved evidence IDs. Quantitative analyses additionally bind dataset, code and environment hashes and required diagnostics.

## 11. Claim verification and release

Each substantive output is decomposed into atomic claims linked to evidence IDs. A source verifier classifies support as directly supported, partially supported, inferential, contradicted, not supported, source too weak or not verified. Citation support can only cap claims; it cannot promote an otherwise weak causal design.

`ScientificWorkflowGate` fails closed if evidence balance, multi-analyst review, temporal concept review, dependency review, claim verification, execution manifest or Global-100 completion is missing.

## v2.2 graph orchestration and model policy

OSLT is multi-agent but not multi-model by requirement. The default execution policy is `SINGLE_PRIMARY`: one approved frontier model can occupy distinct procedural analyst roles without model-vendor diversity being interpreted as evidence. `MODEL_AGREEMENT_IS_NOT_EVIDENTIAL_REPLICATION` is a hard rule.

The execution topology is an explicit graph. `NodeContract` objects declare bounded inputs, outputs, schema and work class. `EdgeContract` objects carry named artifacts. Independent retrieval lanes and analyst roles use `parallel_group` fan-out; deterministic reduction remains code. Verifier and Global-100 audit nodes are mandatory. Uncontrolled cycles are prohibited; unknown-size discovery uses `LoopPolicy` with bounded rounds, dry-round stopping and deduplication against all seen findings.

Sensitive-data deployment is governed separately from intelligence ranking. A primary endpoint must be approved for the relevant data class, and incompatible mandatory retention blocks raw sensitive-data processing. Vendor/model configuration remains external to the scientific kernel so that capability rankings, pricing, retention and safeguards can change without altering scientific rules.

## v2.3 hardening note

The v2.3 branch adds six fail-closed capabilities that were not explicit in v2.2:
model qualification on an OSLT-specific benchmark; versioned/frozen causal specifications;
evidence-lane completeness and discovery saturation; contextual cross-kernel contradiction
resolution; risk-based human expert escalation; and execution resource/circuit-breaker policy.
Every emitted proposition is also assigned an explicit epistemic status so observations,
associations, causal inferences, interpretations, simulations and recommendations cannot be
silently conflated.
