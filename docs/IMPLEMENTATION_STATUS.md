# OSLT executable implementation status

**Release:** GitHub bootstrap v0.1.0 plus the 2026-08-15 build
**Lineage:** OSLT Research Engine v2.4 RC1
**Purpose:** establish a governed public-evidence execution platform and the first runnable vertical slice.

## Implemented now

From the v0.1.0 bootstrap:

- immutable import and hash manifest for the v2.4 RC1 documentation/register package;
- scientific constitution and five competing model families;
- exact-count validation for 64 hypotheses, 640 variables, 65 sources, 100 methods and 13 workstreams;
- seven evidence lanes, provenance admission and dependency-family collapse;
- authority lattice and protected-decision commit gate;
- continuity preflight for open issues, contradictions, rejected paths and artifact hashes;
- 16-dimensional certainty vector and fail-closed claim ceiling;
- attainable sample-size/inference envelope;
- hash-chained research computation journal;
- SQLite persistence for evidence, run manifests, kernel results and synthesis outcomes;
- public-source adapters for OpenAlex, Crossref, PubMed and ClinicalTrials.gov;
- Pilot 1 Academic Knowledge Production vertical slice;
- structured master synthesis over `KernelResult` objects;
- disabled-by-default single AI gateway;
- FastAPI control surface and Typer CLI;
- film claim-to-scene evidence register.

Added 2026-08-15:

- **institutional ontology layer** — role-typed entities, typed dated relations with
  per-edge provenance, admission mirroring evidence admission, and tiered entity
  resolution (`STRONG_IDENTIFIER` / `CORROBORATED_NAME` / `NAME_ONLY`);
- **MD15-versus-MX09 coupling test** requiring a connected component of more than two
  entities, spanning more than one system domain, built from more than one relation type,
  drawn from two or more independent dependency families, with no single central node;
- **four primary-register connectors** — Contracts Finder, Find a Tender, UKRI Gateway to
  Research, UK Parliament written evidence — all keyless;
- **real study-family resolution** replacing DOI equality, clustering on shared trial
  registration, dataset accession, preregistered cohort name and author-network overlap;
- **simulation layer** pinned to `SIMULATION_ONLY` — Monte Carlo power, minimum detectable
  effect, VanderWeele–Ding E-values, coder-drift simulation;
- **lane-coding classifier** with Cohen's kappa and an adjudication flag on every
  assignment;
- **abstract enrichment** from Europe PMC and OpenAlex;
- **counterevidence harvester** running lane-targeted searches and recording which lanes
  were searched as distinct from which returned results;
- **registration-to-publication linkage** supplying the MD11 denominator, with a
  follow-up cutoff;
- **preregistration freeze** and a confirmatory-analysis gate;
- **claim release gate** implementing the nine-point standard with tier-bound wording
  checks;
- **reproducibility manifest** now actually written by the pilot pipeline.

## Deliberately not claimed

This is not a completed scientific study, validated causal model, clinical system or
production research cloud. It does not yet include:

- **any answered proposition** — zero of the 64 have been tested to a releasable
  conclusion;
- blind dual coding, disagreement adjudication or inter-rater reliability against human
  coders (the machinery exists; a second human coder does not);
- validated orientation coding or a labelled training/evaluation corpus;
- complete registration-to-publication linkage at scale;
- live qualified frontier-model calls;
- all 15 specialist domain kernels as empirical implementations;
- TRE/SDE deployment or approved NHS/DfE/ONS analysis packages;
- a production Postgres/object-store/job-queue estate;
- participant recruitment, consent or private digital-history collection;
- independent statistical, clinical, ethical or publication peer review;
- evidence supporting any substantive conclusion about gender-related population change.

## Known limits of the current sources

Two of the four register connectors were found to accept a search term their API
silently discards. Contracts Finder ignores `keyword`, `keywords`,
`searchCriteria.keyword` and `q` alike; UKRI GtR ignores `q`, `term` and `searchTerm`, and
`/api/search/project` returns nothing. Both now refuse the parameter rather than pretend,
and offer client-side `title_contains` which filters only the page retrieved.

**Consequence: no Strand B graph built so far is topic-scoped.** Every one is an arbitrary
sample of recent UK public records. Genuine scoping on those sources requires date paging
plus local filtering, which is not yet implemented.

Any new source should be assumed to behave the same way until proven otherwise: send two
different queries and confirm the results actually differ.

## Current executable claim ceiling

The repository can acquire and provenance-seal public metadata and public-register
relations, collapse real study families, run the Pilot 1 descriptive checks, contest MD15
against the MX09 null, produce structured results, and refuse release when the standard is
unmet. It has done all of these against live data.

What it has not done is answer anything. Outputs remain **descriptive or exploratory
research objects**, and the corpus retrieved on 2026-08-15 is permanently exploratory
because it predates the preregistration freeze — enforced mechanically by
`FREEZE_POSTDATES_DATA_RETRIEVAL`, not by convention.

The MD15 coupling result observed on 2026-08-15 was retired the same day: it held only
when merges made on a naming coincidence were admitted, and reversed to MX09 under any
corroboration requirement.

## Next implementation increment

1. Identifier-level entity resolution (needs Companies House and Charity Commission keys).
2. Date-paged retrieval so the registers can be scoped to a period and topic.
3. A source of `ISSUES_GUIDANCE_TO` edges to complete the bridging tie types.
4. Blind dual coding against a human-coded validation sample.
5. Registration-to-publication linkage at study scale under the frozen specification.
6. Human review of the frozen Pilot 1 specification by a methodologist.
7. Activate master synthesis only after three independently tested kernel result families
   exist.
