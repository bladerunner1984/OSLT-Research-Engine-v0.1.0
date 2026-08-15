# OSLT Research Engine v2.3 RC1 - Release Validation

## Engineering validation

- TESTS_PASS: 171/171 unit and regression tests passed; 0 failed.
- Exact product-code line coverage: 95.195672923958% (95.20%).
- Targeted mutation campaign: 12/12 deliberate control breakages detected.
- Global-100 architecture anti-drift audit: 100/100 criteria passed.
- Global-100 executable assurance overlay: 20/20 fail-closed probes passed.
- Final package preflight: PASS (coverage rechecked at 95.20%).
- Inherited research-control reachability: 16/16 controls reachable.
- Domain kernels: 15.
- Analytical method families: 100.
- Ontology variables: 640.
- Variable-method crosswalk: 640/640 rows.
- Variable-source linkage: 640/640 rows.
- Registered source families: 65.
- Data acquisition workstreams: 13.
- Default workflow graph: 24 nodes / 33 explicit edges.
- Counter-RAG lanes: 7.
- Default analyst roles: 4.
- Certainty dimensions: 16.

## v2.3 hardening additions

Model qualification benchmark; frozen/versioned causal specifications; evidence completeness and
discovery saturation; contextual cross-kernel contradiction resolution; explicit epistemic status;
risk-based human expert escalation; execution budgets/circuit breakers; fail-closed release
readiness; and an executable assurance overlay for the Global-100 architecture audit.

## Mutation/preflight note

The 12-mutant campaign is executed independently and recorded in `Mutation_Campaign_Log_v2_3_RC1.txt`.
The final preflight validates the 12-mutant registry and recorded 12/12 result rather than nesting the
full mutation campaign inside the coverage subprocess, avoiding coverage-plugin interaction while
preserving a reproducible standalone campaign.

## Scientific validation status

This release has **not** empirically validated any substantive hypothesis. Architecture/test success
means the engine contains and exercises its intended safeguards. Real research still requires
study-specific data, field-level construct validation, governance/ethics approval, preregistration
where appropriate, independent replication, expert review and external validation.
