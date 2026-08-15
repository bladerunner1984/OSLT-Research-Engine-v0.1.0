# OSLT model-selection note — 25 July 2026

## Decision

Use a **single-primary-model, multi-agent, graph-orchestrated** architecture by default. Do not require multiple vendors for normal scientific execution. Distinct agent roles, evidence firewalls, rival hypotheses and verifier gates provide procedural challenge; model agreement itself has no evidential weight.

## Current deployment recommendation

For a new general OSLT deployment on 25 July 2026, GPT-5.6 Sol is the preferred default primary model because its current profile is particularly strong for agentic research, browsing/tool use, professional knowledge work and scientific workflows, while its published API price is lower than Claude Fable 5. Programmatic Tool Calling is also advertised as Zero Data Retention compatible.

Claude Fable 5 remains a strong alternative, especially for very long-horizon autonomous knowledge work and deep coding/research tasks. It is not removed from the architecture: use it as an optional benchmark/fallback or select it as the primary model where its deployment environment and data-governance terms fit the study.

The model alias in production should therefore be configuration such as `PRIMARY_FRONTIER`, resolved at deployment time rather than hard-coded into the scientific kernel.

## Important data-governance qualifier

The highest-scoring model must never automatically receive protected NHS, education or cohort microdata. Endpoint approval, retention, region, contractual terms and SDE/TRE rules take precedence over benchmark ranking.

## Sources checked

- OpenAI, GPT-5.6 release, 9 July 2026: https://openai.com/index/gpt-5-6/
- Anthropic, Claude Fable 5 product page, checked 25 July 2026: https://www.anthropic.com/claude/fable
