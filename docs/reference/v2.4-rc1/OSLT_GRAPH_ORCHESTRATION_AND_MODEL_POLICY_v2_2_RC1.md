# OSLT Graph Orchestration and Model Policy v2.2 RC1

## Architectural decision

OSLT is **multi-agent by design but not multi-model by requirement**. Scientific independence comes from independent evidence, prespecified roles, blinding, rival hypotheses, falsification, replication and distinct bias structures—not from vendor diversity.

The default deployment mode is `SINGLE_PRIMARY`: one approved frontier model may perform the judgment-bearing analyst roles. A cheaper model from the same family may optionally be used for bounded extraction/classification under `TIERED_SAME_FAMILY`. Cross-vendor execution is reserved for evaluation, fallback or robustness testing and contributes **zero evidential weight** merely because models agree.

Hard rule: `MODEL_AGREEMENT_IS_NOT_EVIDENTIAL_REPLICATION`.

## Graph-first execution

The workflow is represented as explicit node and edge contracts. Nodes have one bounded job, typed inputs/outputs and a schema. Edges carry named artifacts; deterministic transformations remain code rather than model calls.

Independent work fans out. The default graph fans retrieval into separate support, contradiction, rival, null, bias, replication and correction lanes, then reduces these deterministically into an evidence pack. Analyst roles fan out after dependency review and converge only at a verifier barrier.

Barriers are used only when the downstream step genuinely requires the complete upstream set. Unbounded cycles are prohibited. Discovery loops use a convergence policy with maximum rounds, dry-round stopping and deduplication against **all previously seen** findings.

## Model assignment

Judgment, synthesis and verification default to the primary model. Extraction and classification may be routed to an economy tier only when the output is schema-validated and the release gates remain unchanged. Deterministic nodes never call an LLM.

Model configuration is external to the scientific kernel because frontier rankings, prices, safety routing and data-retention terms can change. OSLT records model ID/provider in the execution manifest but does not hard-code a vendor as scientific truth.

## Sensitive data

A deployment must separately establish that the selected endpoint is approved for the relevant data class. The model policy can fail closed when the primary endpoint is not approved for sensitive data or requires incompatible retention. Raw protected health/education microdata must never be sent to a general endpoint merely because it is the highest-scoring model.

## Fail-closed conditions

- invalid node/edge schema contract;
- edge carries an artifact the source does not produce or target does not consume;
- uncontrolled graph cycle;
- missing verifier or Global-100 audit node;
- tiered same-family configuration uses different providers;
- attempt to count model-vendor agreement as evidential weight;
- sensitive-data deployment without an approved endpoint.
