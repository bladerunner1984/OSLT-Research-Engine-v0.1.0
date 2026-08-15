# Public data harvest runbook

1. Select a proposition and freeze the search concepts, dates, inclusion rules and maximum records.
2. Verify API terms, rate limits and redistribution rights.
3. Run the connector through the OSLT harvest pipeline; do not use ad-hoc scripts for confirmatory
   acquisition.
4. Preserve request parameters, response timestamp, source version, stable identifiers and content
   hash.
5. Admit records only after required provenance and access metadata pass.
6. Deduplicate DOI/PMID/registry identifiers before title/author/year heuristics.
7. Create dataset and study-family dependency edges.
8. Record missing lanes rather than filling them with assumptions.
9. Seal a corpus manifest before confirmatory analysis.
10. Refresh only under a versioned amendment or scheduled surveillance protocol.
