# OSLT Adaptive Sample Size and Information-Gain Protocol v2.4 RC1

OSLT does not impose one N across 640 variables. Sample size is set per estimand and data structure.

## Required planning inputs
Available N; number of outcome events; expected baseline risk; smallest effect worth distinguishing; effective model parameters (including splines/interactions, not raw variable count); clustering; repeated measures; missingness; attrition; measurement error; multiplicity; desired precision/power; external validation.

## Rules
- Use closed-form calculations only for simple designs.
- Use simulation for hierarchical, network, longitudinal, rare-event, latent-class and complex causal designs.
- If the attainable sample cannot discriminate plausible effects, lower the claim ceiling rather than lower the statistical standard.
- Optimise information, not participant count: better temporality or measurement can be worth more than additional low-quality observations.
- Deep cohorts and national administrative cohorts may answer different layers of the same question.

## Output
For each proposition OSLT emits an **Attainable Inference Envelope**: available information, feasible analyses, minimum detectable/estimable region, subgroup limits, replication status, and permitted claim tier.
