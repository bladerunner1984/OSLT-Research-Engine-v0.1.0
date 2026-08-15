# OSLT v2.2 RC1 Re-engineering Changelog

## Added

- governed Evidence Fabric with keyword, vector, hybrid, structured, graph and multimodal retrieval contracts;
- Counter-RAG evidence lanes for support, contradiction, rivals, nulls, criticism, replication and corrections/retractions;
- temporal/jurisdiction scope and historical concept resolution;
- evidence dependency graph and pseudo-replication collapse;
- provenance-preserving evidence chunks and multimodal artifacts;
- context-budgeted, lane-aware evidence packing;
- objective lock and discriminating question decomposition;
- multi-analyst adversarial harness and analytical firewall;
- retrieved-content prompt-isolation and least-privilege tool policy;
- execution manifest binding prompts, model, RAG version and retrieved evidence;
- analysis-code reproducibility contract;
- atomic claim-to-source verification;
- retrieval benchmark metrics and A/B configuration comparator;
- final ScientificWorkflowGate that fails closed on missing outer-layer controls;
- expanded Global-100 audit covering both scientific kernel and evidence/reasoning fabric.

## Preserved

All v2.0 causal, measurement, contrast, historical, interpretive, certainty, triangulation, governance, 640-variable ontology and data-discovery controls remain in the release lineage.

## v2.2 graph/model-policy optimisation

- Reframed OSLT as multi-agent rather than multi-model by requirement.
- Added `model_policy.py` with single-primary, same-family tiering and evaluation-only cross-vendor modes.
- Added hard prohibition on counting model agreement as evidential replication.
- Added sensitive-data endpoint readiness gate.
- Added `workflow_graph.py` with typed node/edge contracts, explicit fan-out groups and deterministic plumbing.
- Added mandatory verifier and Global-100 nodes.
- Added bounded loop-until-dry policy with deduplication against all seen findings.
- Added integrated `ExecutionArchitecturePlan` binding scientific run, workflow graph and model policy.
- Added dated model-selection note; model vendor remains deployment configuration, not a scientific invariant.
