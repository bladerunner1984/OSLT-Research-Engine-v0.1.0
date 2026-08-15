# OSLT v2.4 Implementation and Data-Harvest Roadmap

## Build order
### Stage 0 — Freeze constitution
Approve competing model families, 64 propositions, prohibited default conclusions, outcome taxonomy and claim-state rules.

### Stage 1 — Verify the 640-variable dictionary
For every variable, identify actual source field/instrument, codebook version, collection period, missingness, linkage and construct validity. The generated field-level dictionary is a planning register; all rows begin as `UNVERIFIED_FIELD_AVAILABILITY`.

### Stage 2 — Stand up evidence stores/connectors
Implement OpenAlex, Crossref, PubMed/Europe PMC, trial/review registries, UKRI, government/archive and policy connectors first. Add restricted-source adapters as code/query manifests rather than raw extractors.

### Stage 3 — Run Pilot 1
Academic knowledge-production is the fastest end-to-end test because most core metadata are public. Use it to validate provenance, dependency collapse, orientation coding, Counter-RAG and certainty.

### Stage 4 — Submit restricted-data applications concurrently
Prepare NHS/OpenSAFELY/ONS/DfE/cohort applications using the provided template. Field requests must be derived from frozen estimands, not the entire 640-variable catalogue.

### Stage 5 — Run Pilot 2
Referral/change-point decomposition validates population, historical and ascertainment kernels.

### Stage 6 — Launch primary deep-cohort protocol
Only after ethics/sponsor/governance approval. Begin with attainable sample, use matched comparators and nested digital-history subcohort.

### Stage 7 — Run Pilot 3
Developmental heterogeneity validates temporal person-level integration and subgroup controls.

### Stage 8 — Cross-kernel synthesis
Only after individual pilots pass release gates. No cross-kernel conclusion may exceed the weakest load-bearing evidence required for that conclusion.

### Stage 9 — Scale to full programme
Prioritise new data by expected information gain: collect what most reduces uncertainty between competing models, not simply what is easiest to obtain.
