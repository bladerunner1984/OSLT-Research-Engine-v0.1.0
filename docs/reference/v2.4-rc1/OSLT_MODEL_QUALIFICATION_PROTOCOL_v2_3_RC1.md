# OSLT Model Qualification Protocol v2.3 RC1

OSLT does not hard-code a model vendor. A candidate endpoint must pass a frozen OSLT benchmark
before it may occupy PRIMARY_FRONTIER.

## Benchmark domains

1. Causal reasoning
2. Statistical reasoning
3. Source discrimination and citation entailment
4. Historical/temporal reasoning
5. Linguistic/discourse interpretation
6. Psychometrics and measurement
7. Adversarial refutation
8. Tool use
9. Code generation/execution review
10. Long-context evidence handling
11. Calibration/uncertainty
12. Instruction and safety fidelity

The benchmark must include adversarial and counterevidence-heavy tasks, frozen answer keys or expert
rubrics, contamination review, reproducible settings, tool-use logs and error taxonomy. Generic AI
leaderboards may inform candidate selection but do not qualify a model for OSLT.

Model agreement across vendors is not scientific replication.
