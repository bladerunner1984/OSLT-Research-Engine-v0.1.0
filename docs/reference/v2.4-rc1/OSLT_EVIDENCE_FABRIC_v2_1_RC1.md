# OSLT v2.1 Evidence Fabric Specification

## Purpose

The **Evidence Fabric** controls which information reaches the research kernel and how its provenance, chronology, independence and adversarial balance are preserved.

## Retrieval topology

1. Keyword/BM25-style lexical retrieval for exact terminology, names, dates, diagnostic codes and historical phrases.
2. Vector/semantic retrieval for conceptual similarity.
3. Hybrid retrieval to fuse lexical and semantic candidate sets.
4. Structured retrieval for administrative, cohort, survey and statistical data.
5. Graph retrieval for citation, dataset, author, institution, guideline and causal relationships.
6. Multimodal retrieval for tables, figures, images, audio and video with source-location retention.

No single retrieval mode is epistemically privileged.

## Counter-RAG

Each major proposition is routed through separate retrieval lanes: SUPPORT, CONTRADICT, RIVAL, NULL, BIAS_CRITIQUE, REPLICATION and CORRECTION_RETRACTION.

The purpose is not artificial balance by document count; it is to prevent the search process from becoming a confirmation mechanism.

## Evidence object requirements

Every chunk records document/chunk hashes, source URI/class, query ID, retrieval mode/rank, evidence lane, dates, jurisdiction, page/location, source family, dataset family, bias signatures and supersession state.

## Dependency controls

Repeated publications from the same cohort/source family are collapsed for evidence-packing purposes and represented in the evidence dependency graph. Effective independent evidential families are reported separately from raw publication counts.

## Temporal discipline

Evidence can be filtered by as-of date, effective period, jurisdiction, diagnostic regime and policy regime. Historical analyses should be reconstructable using only information available in the relevant period when the estimand requires that restriction.

## Context budget

Evidence packing is lane-aware. Required contradiction/rival lanes may not be discarded merely because supporting material is more numerous. If a context budget removes a mandatory lane, the evidence pack is marked incomplete.
