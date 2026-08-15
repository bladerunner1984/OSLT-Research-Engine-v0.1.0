# OSLT Research Engine v2.0 RC1 — Architecture

**Release:** 2.0.0rc1  
**Branch:** OSLT (research-engine branch; separate from the government-facing OSL artefact)  
**Status:** release candidate for research architecture and study planning; not empirical validation.

## 1. Purpose and boundary

**OSLT is an experimental research architecture** for multidisciplinary investigation of complex, multicausal changes in observed populations, clinical presentations, policy, knowledge production, language, services and social environments.

OSLT is **not a clinical** decision system, diagnostic device, patient-level causal classifier, or authority for treatment decisions. It does not determine whether an identity is true or false, and it prohibits individual causal attribution from group-level associations.

The governing objective is not to find evidence for a preferred explanation. It is to construct, compare, falsify and calibrate **rival** explanations using methods suited to the estimand, data-generating process and evidential limitations.

## 2. Constitutional rules

1. Define the estimand before selecting a model.
2. Define time zero/index date and temporal ordering.
3. Express causal assumptions through a DAG or equivalent explicit causal model where a causal claim is attempted.
4. Assign each variable a causal role for the specific estimand; there is no universal variable coefficient.
5. Separate measurement quality from effect magnitude and from certainty.
6. Separate predictive importance from causal importance.
7. Test reverse causation, selection, ascertainment and measurement alternatives.
8. Use falsifiers, negative controls, placebos and rival models where feasible.
9. Preserve evidence dependency: repeated analyses of the same source are not independent replications.
10. Theory-dependent methods can generate and test interpretations but cannot self-authorise population-level causal claims.
11. Use multidimensional certainty rather than a single opaque confidence score.
12. Apply the weakest defensible claim ceiling when controls conflict.

> **VARIABLE IMPORTANCE ≠ CAUSAL IMPORTANCE ≠ EVIDENCE CERTAINTY.**

## 3. Federated architecture

OSLT separates the common scientific constitution from specialised domain kernels.

```text
QUESTION / PROPOSITION
        │
        ▼
SCIENTIFIC CONSTITUTION
estimand • provenance • DAG • time • measurement • governance
        │
        ▼
DOMAIN KERNEL
        │
        ▼
ANALYTICAL METHOD ROUTER
        │
        ├── descriptive / temporal
        ├── causal / quasi-experimental
        ├── measurement / psychometric
        ├── network / diffusion
        ├── historical / process tracing
        ├── linguistic / content / discourse
        ├── interpretive / narrative / psychodynamic
        ├── meta-research / publication selection
        └── robustness / bias / adversarial replication
        │
        ▼
EXPERIMENTAL OR COUNTERFACTUAL CONTRAST
        │
        ▼
RIVAL-EXPLANATION DISTILLATION
        │
        ▼
INDEPENDENCE-AWARE TRIANGULATION
        │
        ▼
MULTIDIMENSIONAL CERTAINTY
        │
        ▼
CLAIM ADJUDICATION / BOUNDED OUTPUT
```

## 4. Fifteen domain kernels

| Domain kernel | Primary analytical purpose |
|---|---|
| Clinical & developmental heterogeneity | Longitudinal pathways, timing, subgroup heterogeneity and measurement invariance |
| Psychiatric & psychological formulation | Competing psychiatric, developmental, cognitive, trauma, family-system, narrative and psychodynamic formulations |
| Academic epistemic production & diffusion | Publication, funding, citation, study dependency, research integrity and guideline uptake |
| Historical psychiatry & nosology | Diagnostic regime change, institutional mechanisms, process tracing and semantic change |
| Education policy & school environment | Actual implementation/exposure, policy discontinuities and school-level counterfactuals |
| Digital, media & peer influence | Selection/homophily versus influence, active search versus passive exposure, diffusion and networks |
| Service, referral & ascertainment | Referral thresholds, capacity, waiting lists, coding, disclosure and ascertainment decomposition |
| Population trend & epidemiology | Establish what changed, in whom, where and when before causal explanation |
| Professional guidance & clinical doctrine | Recommendation change, evidence ancestry and translation into practice |
| Legal & public-policy change | Effective dates, implementation, institutional mechanisms and jurisdictional contrasts |
| Public discourse, language & media | Diachronic semantics, framing, stance, argumentation and corpus change |
| Biological & genomic | Group-level biological associations, phenotype quality and heterogeneity with strict misuse controls |
| Family & interpersonal systems | Household, family and peer configurations, clustering and temporal relationships |
| Treatment & outcomes | Target-trial logic, indication confounding, treatment switching and longitudinal outcomes |
| Methods, bias & meta-research | Model uncertainty, missingness, hidden bias, analyst degrees of freedom and adversarial replication |

Executable specifications are in `oslt_research/kernels.py`; planning orchestration is in `oslt_research/engine.py`.

## 5. Analytical-method ontology

RC1 contains **100 registered analytical method families**. They are metadata-governed by:

- inference roles;
- supported data structures;
- assumptions;
- safeguards;
- theory-dependence flag;
- simulation-only flag;
- maximum claim ceiling.

The method register includes classical and modern causal inference, target-trial emulation, g-methods, survival/event-history analysis, age-period-cohort analysis, standardisation/decomposition, multilevel models, causal forests, latent class/trajectory models, SEM/dynamic SEM, IRT/DIF/measurement invariance, specification curves/multiverse analysis, Bayesian model averaging, probabilistic bias analysis, E-values, Rosenbaum bounds, negative controls, publication-selection models, network/diffusion models, QCA, process tracing, historical institutional analysis, corpus/diachronic semantics, content/discourse/narrative methods, and explicit A/B, A/B/n, factorial, crossover, cluster, stepped-wedge and adaptive designs.

`oslt_research/router.py` recommends candidate methods; it never declares their assumptions satisfied.

## 6. Experimental and counterfactual contrast

`oslt_research/contrast.py` formalises a general contrast principle.

### Experimental contrasts
- RANDOMISED_AB
- RANDOMISED_ABN
- FACTORIAL
- CROSSOVER
- CLUSTER

Confirmatory randomised designs require preregistration. Ethical authorisation is a hard gate where required.

### Observational / historical contrasts
- QUASI_EXPERIMENT
- NATURAL_EXPERIMENT
- MATCHED_COMPARATOR
- HISTORICAL_COMPARATOR
- SYNTHETIC_CONTROL

The architecture also supports DiD, event-study, ITS and RDD method families through the analytical register.

## 7. Contrastive evidence distillation

The engine does not ask merely whether evidence is compatible with H1. It asks whether the evidence discriminates H1 from H2, H3, etc.

Each `HypothesisEvidence` object can hold hypothesis-specific likelihoods. `ContrastiveDistiller` performs pairwise contests and collapses evidence that shares the same dataset/source family to reduce pseudo-replication.

Core distinction:

```text
Evidence predicted by H1, H2 and H3  → low discriminatory value
Evidence likely under H1 but unlikely under H2/H3 → high discriminatory value
```

OSLT permits several mechanisms to survive simultaneously when the phenomenon is genuinely multicausal.

## 8. Historical mechanism reasoning

`oslt_research/historical.py` represents institutional change as explicit candidate mechanisms:

- displacement;
- layering;
- drift;
- conversion;
- exhaustion;
- critical juncture;
- diffusion.

Each proposed causal chain is decomposed into `MechanismLink` objects. A historical mechanism cannot be promoted to causal-ready status from chronology alone: all links must be admissible, at least one stronger process-tracing test must be present, counterfactual evidence must exist, and rival mechanisms must be specified.

## 9. Linguistic, discourse, narrative and psychodynamic analysis

OSLT distinguishes:

1. computational/corpus linguistic measurement;
2. diachronic semantic change;
3. quantitative content coding;
4. frame, stance, modality, pragmatics and conversation analysis;
5. discourse and critical discourse analysis;
6. narrative analysis;
7. psychodynamic and phenomenological interpretation.

These methods may identify patterns, changes, mechanisms to test and hypothesis-generating interpretations. A **theory-dependent** analysis is explicitly bounded. `InterpretiveFinding.claim_ceiling()` prevents interpretive output from independently establishing population-level causation.

## 10. Multidimensional certainty

`oslt_research/certainty.py` requires all sixteen certainty dimensions:

1. statistical precision;
2. measurement validity;
3. temporal identification;
4. causal identification;
5. confounding control;
6. selection-bias control;
7. missing-data robustness;
8. model/specification stability;
9. evidence independence;
10. cross-method convergence;
11. replication;
12. transportability;
13. publication-selection risk;
14. provenance integrity;
15. theory dependence;
16. explanatory contribution.

A claim can therefore be statistically precise but causally weak, or causally credible but poorly transportable. Certainty is not collapsed into a spurious universal percentage.

## 11. Independence-aware triangulation

`oslt_research/triangulation.py` clusters analyses by dataset family and source family. Multiple methods applied to the same data contribute diminishing evidence rather than being counted as independent replications. Shared bias signatures further reduce effective triangulation strength.

## 12. 640-variable ontology integration

The original 640-variable ontology is preserved. `OSLT_VARIABLE_METHOD_CROSSWALK_v2_0_RC1.csv` maps every variable to:

- primary and secondary OSLT research domains;
- default analytical method families;
- timing requirement;
- preferred source;
- measurement requirements;
- inference boundary.

`OSLT_SOURCE_VARIABLE_LINKAGE_v2_0_RC1.csv` then maps every variable to candidate primary and secondary data-source IDs, access classes and acquisition phases.

No crosswalk assignment is a causal weight. Coefficients/effects must be estimated within a prespecified estimand and defensible design.

## 13. Adversarial scientific reasoning

For important propositions OSLT should deliberately seek the strongest routes to defeat them:

```text
TARGET HYPOTHESIS
 ├─ reverse causation
 ├─ selection / ascertainment
 ├─ measurement artefact
 ├─ common cause / unmeasured confounding
 ├─ alternative operationalisation
 ├─ alternative statistical specification
 ├─ alternative disciplinary formulation
 ├─ placebo / negative control
 ├─ counterfactual population or jurisdiction
 └─ independent replication
```

A conclusion is strengthened only by surviving relevant attacks; attacks that are impossible because required data are absent become explicit uncertainty rather than assumed passes.

## 14. Population-change decomposition before explanation

OSLT separates outcomes that are often incorrectly conflated, for example:

- self-reported incongruence;
- identity labels;
- disclosure;
- social transition;
- GP presentation;
- specialist referral;
- diagnostic/formulation state;
- treatment request;
- treatment initiation;
- surgical referral/procedure.

The service/referral and population kernels test whether changes can be decomposed into underlying rate change, population composition, awareness/disclosure, ascertainment, coding, referral thresholds, service capacity and measurement change before attributing the residual to substantive causal mechanisms.

## 15. Research governance and protected outputs

Restricted individual-level data must remain inside the custodian's approved secure environment where required. Only approved, disclosure-controlled aggregate outputs should leave a Trusted Research Environment/Secure Data Environment. Data minimisation, purpose limitation, access logging, provenance, reproducibility and governance authorisation are architectural requirements.

## 16. Release validation

OSLT uses two distinct validation concepts:

- **software/architecture validation:** tests, reachability, preflight, manifest, Global-100 anti-drift audit;
- **scientific validation:** external datasets, real studies, preregistration, replication, sensitivity analysis and independent review.

Passing the former never proves a substantive scientific hypothesis.
