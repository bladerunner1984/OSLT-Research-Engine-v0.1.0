# OSLT Research Engine v2.0 RC1

OSLT is the separately versioned **research** branch derived from the hardened OSL kernel. It is intended for governed multidisciplinary study planning, causal/adversarial reasoning, evidence integration and claim calibration. It is not a clinical decision system.

## What RC1 contains

- inherited hardened OSL claim-governance controls;
- 15 executable domain-kernel specifications;
- 100 analytical method families with assumptions, safeguards and claim ceilings;
- method router and study-plan orchestrator;
- A/B, A/B/n, factorial and counterfactual contrast primitives;
- pairwise rival-hypothesis distillation;
- 16-dimensional certainty vector;
- dependency-aware triangulation;
- historical change/process-tracing primitives;
- interpretive/psychodynamic claim sandboxing;
- 640-variable method crosswalk;
- 640-variable source/acquisition linkage;
- 65-source discovery register;
- Global-100 anti-drift architecture audit;
- inherited and new test suites.

## Research boundary

OSLT must not diagnose a person, determine identity truth/falsity, infer individual causation from group associations, treat publication/citation volume as truth, or treat language alignment as proof of persuasion. Study-specific ethical, legal, information-governance and custodian approvals remain external requirements.

## Core files

- `OSLT_ARCHITECTURE_v2_0_RC1.md`
- `OSLT_ANALYTICAL_METHOD_REGISTER_v2_0_RC1.csv`
- `OSLT_DOMAIN_METHOD_MATRIX_v2_0_RC1.csv`
- `OSLT_VARIABLE_METHOD_CROSSWALK_v2_0_RC1.csv`
- `OSLT_DATA_SOURCE_REGISTER_v2_0_RC1.csv`
- `OSLT_SOURCE_VARIABLE_LINKAGE_v2_0_RC1.csv`
- `OSLT_DATA_DISCOVERY_ROADMAP_v2_0_RC1.md`
- `OSLT_GLOBAL100_AUDIT_FINAL.md`
- `tests/test_research_kernel.py`
- `tests/test_oslt_v2.py`

## Executable package

`oslt_research/` contains the claim pipeline, governance controls and new OSLT modules. The entry-point planning class is `OSLTResearchEngine` in `oslt_research/engine.py`.

## PACKAGE_MANIFEST

`PACKAGE_MANIFEST.json` is regenerated at release finalisation and binds the versioned artefacts by cryptographic hash.
