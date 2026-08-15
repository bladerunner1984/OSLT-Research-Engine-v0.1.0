# Contributing

1. Work on a branch named `agent/<description>` or `research/<study-id>-<description>`.
2. Freeze the proposition, estimand, scope and analysis plan before confirmatory outcome analysis.
3. Do not add a new model-provider call outside `src/oslt_research/ai/gateway.py`.
4. Do not place raw or restricted data in the repository.
5. Add or update tests, manifests and provenance contracts with every behaviour change.
6. Run `python scripts/preflight.py` and `pytest` before opening a pull request.
7. Use a draft pull request until evidence, tests and human-review requirements are satisfied.

A model-generated change is an A5 proposal. It cannot overwrite an A2 human governance decision,
A1 authorised specification, or A0 constitution.
