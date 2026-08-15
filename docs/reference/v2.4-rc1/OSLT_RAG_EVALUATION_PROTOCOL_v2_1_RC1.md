# OSLT v2.1 RAG / Evidence-Retrieval Evaluation Protocol

## Principle

A reasoning kernel cannot recover decisive evidence that its retrieval layer never supplies. Retrieval therefore receives its own prespecified benchmark suite.

## Gold-set metrics

For each benchmark research question OSLT measures:

- **Recall@K** — proportion of known relevant evidence retrieved;
- **Precision@K** — relevant evidence among the first K results;
- reciprocal rank / MRR where aggregated;
- **nDCG@K** — ranking quality with position discount;
- evidence-lane recall — coverage of required support/counter/rival lanes;
- temporal correctness;
- jurisdiction correctness;
- source-family diversity;
- counterevidence recall;
- dependency-detection accuracy;
- citation-location correctness.

## Retrieval A/B testing

Candidate configurations are benchmarked on the same frozen gold questions, for example:

- lexical only;
- vector only;
- hybrid;
- hybrid + semantic reranking;
- hybrid + graph retrieval;
- hybrid + graph + query decomposition + Counter-RAG.

The `RetrievalABComparator` uses a prespecified metric blend prioritising relevant-evidence recall and evidence-lane coverage. This is an engineering optimisation and cannot support a substantive research hypothesis.

## Drift monitoring

Gold questions, relevance judgements, retrieval configuration and index snapshot are versioned. A configuration change that improves average relevance but materially reduces counterevidence recall is not accepted without explicit review.
