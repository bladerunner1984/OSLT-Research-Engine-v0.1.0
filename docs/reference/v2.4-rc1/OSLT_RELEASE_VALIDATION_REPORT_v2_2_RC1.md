# OSLT Research Engine v2.2 RC1 — Release Validation

**TESTS_PASS: 156/156**  
**GLOBAL100: 100/100**  
**EXACT PRODUCT-LINE COVERAGE: 94.8690%**  
**TARGETED MUTATIONS: 8/8 detected**  
**DEFAULT WORKFLOW GRAPH: 19 nodes / 27 edges**  
**DEFAULT MODEL MODE: SINGLE_PRIMARY**

## Scope of validation

This validates architecture and engineering controls. It does **not** establish the truth of any research hypothesis, clinical effectiveness, causal effect, or external scientific validity.

## v2.2 additions validated

- typed graph node and edge contracts;
- retrieval and analyst fan-out groups;
- deterministic plumbing separated from model judgment;
- verifier and Global-100 audit nodes;
- bounded loop-until-dry convergence policy;
- single-primary model policy;
- same-family cost tiering for bounded extraction/classification;
- prohibition on treating cross-model agreement as evidential replication;
- sensitive-data endpoint readiness gate;
- integrated scientific + graph + model execution plan.
