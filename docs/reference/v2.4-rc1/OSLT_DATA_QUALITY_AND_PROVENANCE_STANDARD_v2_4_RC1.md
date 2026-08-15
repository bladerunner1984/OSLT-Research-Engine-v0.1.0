# OSLT Data Quality and Provenance Standard v2.4 RC1

Every field and evidence object must retain enough metadata to reproduce what was analysed.

## Required lineage
`source -> release/version -> exact field/document -> retrieval/query -> raw value/text -> transformation -> harmonised value -> analysis object -> claim`

## Admission gates
A source/field is not analysis-ready until: exact definition is verified; time coverage is verified; missingness and coverage are characterised; diagnostic/terminology version is known; transformations are code-reviewed; duplicate/dependency relationships are recorded; privacy/access requirements are satisfied; and the field is mapped to an estimand/DAG role rather than a generic 'important variable'.

## Missingness
`UNKNOWN`, `NOT_RECORDED`, `NOT_APPLICABLE`, `NOT_ASKED` and true negative values must remain distinct. Absence of a code is not automatically absence of a condition/exposure.

## Temporal harmonisation
Preserve event date, collection date, publication/effective date and observation window separately. Never compare concepts across diagnostic/policy eras until the concept resolver records equivalence/partial-equivalence/non-equivalence.

## Dependency
Publications sharing cohort/data/code/research lineage are linked before meta-analysis. Replication requires materially independent evidence.

## Transformations
Every recode, NLP label, imputation, derived measure and exclusion is versioned and reproducible. Original values are never overwritten.
