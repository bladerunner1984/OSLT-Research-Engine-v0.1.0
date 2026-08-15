# OSLT v2.1 Harness and Wrapper Specification

## Objective-lock wrapper

The research objective, population, outcomes and prohibited default conclusions are frozen before retrieval/model selection. Question decomposition must include at least one subquestion capable of changing the conclusion.

## Multi-Analyst Harness

For important propositions the default harness requires four distinct functions:

- **Primary analyst** — strongest defensible analysis of the target proposition.
- **Rival analyst** — strongest competing explanation and its predictions.
- **Methods critic** — attacks identification, measurement, specification and missingness assumptions.
- **Source verifier** — checks atomic claims against cited evidence.

Additional statistical and historical reviewers can be required by the method router.

Analyst agreement is not counted as replication when analysts share the same evidence or data-generating process.

## Analytical firewall

Domain analyses may be sealed until prespecified work is complete. This reduces contamination from an earlier kernel's conclusion. Unblinding occurs only at the synthesis stage specified by protocol.

## Analysis-code harness

Quantitative execution requires an estimand ID, dataset snapshot hash, code hash, environment hash and prespecified diagnostics. Independent code review can be made mandatory. Results are evidence objects, not free-text claims.

## Release gate

`ScientificWorkflowGate` requires:

1. balanced evidence pack;
2. complete Multi-Analyst Harness;
3. valid execution manifest;
4. temporal/concept review;
5. evidence-dependency review;
6. claim-to-source verification;
7. Global-100 score of 100/100.

The gate fails closed.
