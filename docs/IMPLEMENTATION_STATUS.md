# OSLT executable implementation status

**Release:** GitHub bootstrap v0.1.0 plus the 2026-08-15 and 2026-08-16 builds
**Lineage:** OSLT Research Engine v2.4 RC1
**Revised:** 2026-08-16
**Purpose:** establish a governed public-evidence execution platform and the first runnable
vertical slices.

## Verified state

| Measure | Value | How to check |
|---|---|---|
| Tests collected | **756** | `pytest --collect-only -q` |
| Source connector modules | **26** (+ a shared OCDS resolution module, a base and a fixture) | `ls src/oslt_research/connectors/` |
| Admitted evidence records | **6,428** (6 refused: retracted) | `runtime/oslt.db`, `evidence_objects` |
| Institutional entities | **824** | `institutional_entities` |
| Institutional relations | **1,286** — FUNDS 926, ADVISES 227, CONTRACTS_WITH 103, ISSUES_GUIDANCE_TO 30 | `institutional_relations` |
| Propositions | 64; 16 `OPEN_TESTABLE`, 25 `NEEDS_PRIMARY_COLLECTION`, 16 `NEEDS_RESTRICTED_ACCESS`, 7 `NEEDS_INDIVIDUAL_LEVEL` | `assess_feasibility('registries')` |
| Propositions answered | **0 of 64** | — |
| W02 usable calibration series | **218** (56 + 162) | `data/fingertips_w02.json`, `data/fingertips_w02_recovery.json` |
| Census 2021 gender identity cells | **517** across 13 of 24 tables | `data/census_2021_gender_identity.json` |

Test-suite coverage was last measured at 92% on the 442-test build and has **not** been
re-measured since. Do not quote it.

## Connector inventory

All keyless or free-registration. Grouped by what they supply.

**Literature and registries (corpus):** `openalex`, `crossref`, `pubmed`, `europepmc`,
`clinicaltrials`, `isrctn`, `openaire`, `retractions` (Crossref DOI join, admission gate),
`ror` (research-organisation resolver).

**UK public registers (Strand B institutional graph):** `contracts_finder`, `find_a_tender`,
`ukri_gtr`, `parliament_evidence`, `hansard`, `legislation`, `govuk_guidance`,
`threesixty_giving` (10,707 admitted FUNDS edges), `companies_house`, `charity_commission`,
plus `ocds.py` — a shared OCDS party-identifier resolution module, not itself a connector.

**Statistics and denominators (W01, W02, W05, W11):** `fingertips` (OHID public health
indicators — the W02 workhorse), `nomis` (Census 2021 query API), `ons_datasets`,
`ons_population` (streamed local CSV denominators; a 4× counting error was caught here),
`nhs_statistics` (NHS ODS plus a statistics index that returns file *references* and executably
refuses declined hosts), `education_data` (DfE Explore Education Statistics),
`media_discourse` (GDELT).

`fixture.py` and `base.py` are test/support infrastructure.

## Workstream coverage

- **W01 population denominators** — covered (`ons_population`, `nomis`).
- **W02 NHS referrals, diagnoses and service pathways** — required by 40 of 64 propositions;
  was empty, now holds **218 usable series**. Still a proxy: service-contact and admission
  rates, not gender-service referrals. The direct series is FOI/MHSDS-gated.
- **W05 education** — covered (`education_data`, plus Fingertips 91871 school SEMH).
- **W11 media/discourse** — covered (`media_discourse`).
- **Strand B institutional registers** — covered across four register families, but **no
  Strand B graph is topic-scoped** (see limits below).
- Remaining workstreams are access-gated; see the feasibility census.

## What runs

From the v0.1.0 bootstrap:

- immutable import and hash manifest for the v2.4 RC1 documentation/register package;
- scientific constitution and five competing model families;
- exact-count validation for 64 hypotheses, 640 variables, 65 sources, 100 methods and 13
  workstreams;
- seven evidence lanes, provenance admission and dependency-family collapse;
- authority lattice and protected-decision commit gate;
- continuity preflight for open issues, contradictions, rejected paths and artifact hashes;
- 16-dimensional certainty vector and fail-closed claim ceiling;
- attainable sample-size/inference envelope;
- hash-chained research computation journal;
- SQLite persistence for evidence, run manifests, kernel results, synthesis outcomes and the
  institutional graph;
- Pilot 1 Academic Knowledge Production vertical slice;
- structured master synthesis over `KernelResult` objects;
- disabled-by-default single AI gateway;
- FastAPI control surface and Typer CLI;
- film claim-to-scene evidence register.

Added 2026-08-15:

- **institutional ontology layer** — role-typed entities, typed dated relations with per-edge
  provenance, admission mirroring evidence admission, tiered entity resolution
  (`STRONG_IDENTIFIER` / `CORROBORATED_NAME` / `NAME_ONLY`);
- **MD15-versus-MX09 coupling test** requiring a connected component of more than two
  entities, spanning more than one system domain, built from more than one relation type,
  drawn from two or more independent dependency families, with no single central node;
- **real study-family resolution** replacing DOI equality (shared trial registration, dataset
  accession, preregistered cohort name, author-network overlap);
- **simulation layer** pinned to `SIMULATION_ONLY` — Monte Carlo power, minimum detectable
  effect, VanderWeele–Ding E-values, coder-drift simulation;
- **lane-coding classifier** with Cohen's kappa and an adjudication flag on every assignment;
- **abstract enrichment** from Europe PMC and OpenAlex;
- **counterevidence harvester** recording which lanes were searched as distinct from which
  returned results;
- **registration-to-publication linkage** supplying the MD11 denominator;
- **preregistration freeze** and a confirmatory-analysis gate;
- **claim release gate** implementing the nine-point standard with tier-bound wording checks
  and a typed human-review record that a model review cannot satisfy;
- **reproducibility manifest** written by the pilot pipeline;
- **retraction screening** — a retracted work is refused admission, not merely findable.

Added 2026-08-16:

- **Fingertips (OHID) connector** and two harvests — 135 indicators discovered, 56 usable
  series first pass, then a recovery run over the 39 refusals plus the 15 never reached (429
  series retrieved, 162 usable). W02 now holds 218. The recovery loosened no check: each
  refusal was the connector reporting an ambiguous question, and the recovery asked a specific
  one per (area, sex, age) stratum;
- **NOMIS connector** and the **Census 2021 gender identity harvest** — 13 whole-table queries,
  517 cells, zero missing, zero refusals, every dimension explicitly pinned so that no
  codelist's own total was mixed with its parts;
- **NHS ODS and NHS England statistics index**, with `guard_route()` making the
  `files.digital.nhs.uk` refusal executable — links to declined hosts are stripped from index
  results;
- **ONS population denominators**, **DfE Explore Education Statistics**, **GDELT media
  discourse**, **360Giving** (10,707 admitted FUNDS edges), **legislation.gov.uk**, **ONS open
  datasets API**, **ROR**, **OpenAIRE**, **ISRCTN**, **Hansard**, **GOV.UK guidance**,
  **Charity Commission** and **Companies House** connectors;
- **one Strand B pipeline run across every register**;
- **three descriptive analyses** — `scripts/referral_baseline.py` (background referral growth),
  the second comparator (secondary mental health referrals by age and sex), and
  `scripts/negative_controls.py` (objectively ascertained paediatric admissions plus school
  SEMH). Outputs in `data/`; findings and caveats in `docs/REFERRAL_BASELINE.md`;
- **FOI request drafted** (`studies/foi_requests/nhs_gender_service_referrals.md`) and the
  WhatDoTheyKnow automation route declined on published-policy grounds.

## What is wired into the CLI, and what is not

The Typer CLI (`src/oslt_research/cli.py`) exposes: `preflight`, `registry-summary`,
`init-db`, `harvest`, `pilot1`, `synthesise`, `sample-envelope`.

**`harvest --source` accepts only four connectors** — `openalex`, `crossref`, `pubmed`,
`clinicaltrials`. The other 22 are reachable only through `src/oslt_research/pipelines/` or
through the scripts in `scripts/`. That is a real gap: the register, statistics and harvest
connectors have no CLI surface, and the three descriptive analyses are standalone scripts
rather than CLI commands. A successor wanting a single reproducible entry point should expect
to add one.

Repeatable scripts: `harvest_fingertips_w02.py`, `harvest_fingertips_recovery.py`,
`harvest_census_gender_identity.py`, `referral_baseline.py`, `negative_controls.py`,
`preflight.py`, `validate_registries.py`, `export_schemas.py`,
`generate_reference_manifest.py`, `check_ai_boundary.py`, `check_sensitive_files.py`.

## Deliberately not claimed

This is not a completed scientific study, validated causal model, clinical system or
production research cloud. It does not yet include:

- **any answered proposition** — zero of 64 tested to a releasable conclusion;
- **any mechanism calibrated against a target series** — `compare_mechanisms` has never been
  run against real gender-service data, because no such series is held;
- blind dual coding, disagreement adjudication or inter-rater reliability against human coders
  (the machinery exists; a second human coder does not — every AI review record is
  `A5_MODEL_PROPOSAL` and is barred from becoming `A2_HUMAN_GOVERNANCE_DECISION`);
- persisted lane coding — all 6,428 admitted records currently read `UNCLASSIFIED`;
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

**Silently discarded query parameters.** Contracts Finder ignores `keyword`, `keywords`,
`searchCriteria.keyword` and `q` alike; UKRI GtR ignores `q`, `term` and `searchTerm`, and
`/api/search/project` returns nothing. Both now refuse the parameter rather than pretend, and
offer client-side `title_contains` which filters only the page retrieved. **Consequence: no
Strand B graph built so far is topic-scoped.** Every one is an arbitrary sample of recent UK
public records. Genuine scoping needs date paging plus local filtering, not yet implemented.
Assume any new source behaves the same until proven otherwise: send two different queries and
confirm the results differ.

**Six confirmed cases of a date field measuring something else** — legislation.gov.uk Atom
`<updated>`, OpenAIRE `dri:dateOfCollection`, OpenAIRE `relevantdate[created]`, ISRCTN element
dates, WHO ICTRP `Date_enrollement`, and Fingertips period labels (Financial, Calendar and
Academic bases coexist; `YearType` is authoritative).

**One index-not-trend trap caught.** Fingertips 91344 is an England-indexed standardisation
ratio — 100.0 in every period, `count == denominator` throughout — whose naive first-to-last
ratio of 1.00 would have **inverted** the referral-baseline conclusion. Excluded by id;
every stratum in the negative-control run is now tested for the same failure mode.

**Rate limits are a data-loss event.** OpenAlex enforces a daily *budget*, not a rolling
window. One unthrottled enrichment run drew 1,379 requests and cost roughly a day of access to
a P0 source. Throttle from the first request.

**811 thin-abstract records are non-recoverable** — conference front-matter and session
headers with no abstract at source. Closed; do not retry.

**Pooled windows and short strata are refused, not padded.** 34 Fingertips series are flagged
pooled and `observed()` refuses them unless `allow_pooled=True` is passed deliberately; strata
with fewer than three points are excluded and recorded, never interpolated. A failed request
marks a series incomplete rather than producing a zero.

**Declined on published-policy grounds, not to be reopened:** PROSPERO (anti-automation
header), WhatDoTheyKnow (robots.txt plus House Rules), `files.digital.nhs.uk` (blanket
`Disallow: /`), data.gov.uk CKAN, WHO ICTRP bulk export (account plus licensing decision). See
`SOURCE_ACCESS_NOTES.md`; each has a legitimate route recorded.

## Current executable claim ceiling

The repository can acquire and provenance-seal public metadata, public-register relations and
public statistical series; collapse real study families; run the Pilot 1 descriptive checks;
contest MD15 against the MX09 null; produce descriptive comparator analyses with their
exclusions recorded; and refuse release when the standard is unmet. It has done all of these
against live data.

What it has not done is answer anything. Outputs remain **descriptive or exploratory research
objects**. The corpus retrieved on 2026-08-15 is permanently exploratory because it predates
the preregistration freeze — enforced mechanically by `FREEZE_POSTDATES_DATA_RETRIEVAL`, not by
convention. The three 2026-08-16 analyses are descriptive by construction: per
`compare_mechanisms`, compatibility is never support, and no mechanism has been run.

The MD15 coupling result observed on 2026-08-15 was retired the same day: it held only when
merges made on a naming coincidence were admitted, and reversed to MX09 under any corroboration
requirement. The surviving MX09-over-MD15 disposition rests on a 337-relation graph; the store
now holds 1,286 relations and has not been re-adjudicated.

## Next implementation increment

1. Send the drafted FOI request — free, statutory, and the gate on the whole comparison.
2. Manual MHSDS download plus a local-file reader on the `ons_population.py` precedent.
3. Re-run the MD15/MX09 coupling test against the current 1,286-relation graph.
4. Date-paged retrieval so the registers can be scoped to a period and topic.
5. Persist lane-classifier output, then blind dual coding against a human-coded validation
   sample.
6. Wire the register, statistics and harvest connectors into the CLI, and promote the three
   analysis scripts to commands.
7. Registration-to-publication linkage at study scale under the frozen specification.
8. Human review of the frozen Pilot 1 specification by a methodologist.
9. Activate master synthesis only after three independently tested kernel result families
   exist.
