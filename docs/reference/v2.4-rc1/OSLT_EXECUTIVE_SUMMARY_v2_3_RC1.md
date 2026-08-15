# OSLT Research Engine v2.3 RC1 - Executive Summary

## Objective

OSLT is a governed multidisciplinary research engine designed to investigate complex multicausal phenomena without allowing any one discipline, dataset, model or preferred explanation to dominate the result. It separates retrieval, measurement, causal identification, historical/linguistic interpretation, adversarial review, certainty calibration and final claim release.

## Current architecture

- 640-variable causal/research ontology.
- 100 analytical method families.
- 15 domain kernels.
- 65 registered source families.
- 13 data-acquisition workstreams.
- 7 Counter-RAG evidence lanes.
- 4 default adversarial analyst roles.
- 16 certainty dimensions.
- 24 default workflow nodes and 33 explicit data edges.
- Single-primary model policy, but model-agnostic and benchmark-qualified.

![OSLT engine flow](visuals/OSLT_ENGINE_FLOW_v2_3_RC1.png)

## Core reasoning principle

For each important proposition, OSLT asks not merely whether evidence supports it, but whether the evidence discriminates it from the strongest competing explanation. Supporting, contradictory, null, rival, methodological-critique, replication and correction evidence are deliberately retrieved separately. Evidence sharing the same cohort, dataset or institutional lineage is collapsed before triangulation.

The system then resolves apparent contradictions across kernels, calibrates certainty dimension-by-dimension, verifies atomic claims against source evidence, escalates high-impact outputs to human review, and fails closed if reproducibility or release gates are incomplete.

## Evidence and data that must be accumulated

![OSLT data estate](visuals/OSLT_DATA_ESTATE_v2_3_RC1.png)

The 13 acquisition workstreams are: population denominators/trends; NHS referrals and pathways; primary-care/psychiatric/neurodevelopmental history; longitudinal developmental cohorts; education and school implementation; digital/social/peer exposure; academic publication and knowledge production; historical psychiatry and nosology; clinical/professional guidance; government/legal policy; media/public discourse; qualitative/narrative evidence; and designed experiments/independent replications.

The current register maps 640 ontology variables to candidate source families. That mapping is a discovery plan, not proof of availability: field-level definitions, timing, missingness, construct validity, linkage quality and governance must be verified before each study.

## Anti-drift and release assurance

- 171/171 tests passing.
- 95.20% exact product-code coverage.
- 12/12 targeted mutations detected.
- Global-100 architecture audit: 100/100.
- Executable fail-closed assurance overlay: 20/20.

These metrics validate the internal engineering controls of this release. They do not establish the truth of any substantive hypothesis and do not substitute for real-data validation, preregistration, independent replication, ethics/governance approval or expert peer review.

## Discovery sequence

1. Freeze constructs, outcomes, populations, estimands, rival hypotheses and causal assumptions.
2. Acquire open population, literature, policy, guideline and historical corpora.
3. Build temporal, semantic, citation/dependency and causal graphs.
4. Secure restricted NHS, ONS, DfE and longitudinal cohort microdata.
5. Decompose observed population change into prevalence, ascertainment, service/referral and compositional components before mechanism attribution.
6. Run domain-specific analyses under analytical blinding and cross-method falsification.
7. Replicate using independent cohorts, jurisdictions and bias structures.
8. Commission new A/B/n, factorial, measurement or qualitative studies only where observational evidence cannot discriminate rival mechanisms.
9. Synthesize only after contradiction resolution, certainty calibration and atomic claim verification.

## Bottom line

OSLT v2.3 is best understood as a scientific operating architecture rather than an LLM prompt. The AI model is one replaceable reasoning component inside a larger evidence, computation, adversarial-testing and governance system. The next phase is empirical: obtain the priority data, build benchmark/gold-standard tasks, validate retrieval and model qualification against expert adjudication, then run preregistered studies through the engine.
