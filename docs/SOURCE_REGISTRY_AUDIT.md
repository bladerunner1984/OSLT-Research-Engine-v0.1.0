# Connector-to-source-registry audit

**Date:** 2026-08-16
**Scope:** all 28 connector modules under `src/oslt_research/connectors/`
(`base.py` and `fixture.py` are excluded by `connector_source_ids()` and are not connectors).

## Why this exists

`docs/FEASIBILITY_AND_RELEASE.md` recorded, from the `workstream_source_coverage` overlay,
that only **12 of 28** connector modules declared a registry `SOURCE_ID`, and that four
declared `UNREGISTERED:` ids with no row in `registries/sources.csv`. The consequence was a
bookkeeping failure, not a research failure: W02 gained 218 usable Fingertips series and no
mechanical route credited any of it to a registered source, so a reader of the registry would
have concluded the work did not exist.

## What this is NOT

**Registering a source does not make a proposition testable.** The feasibility census reads
only human-written `access_summary` tokens in `registries/workstreams.csv`, deliberately, so
that an engineering gap can never masquerade as an access gap. Nothing here touched
`registries/hypotheses.csv` or any `access_summary`. The reachability split is unchanged:

| | OPEN_TESTABLE | NEEDS_PRIMARY_COLLECTION | NEEDS_RESTRICTED_ACCESS | NEEDS_INDIVIDUAL_LEVEL |
|---|---|---|---|---|
| Before | 16 | 25 | 16 | 7 |
| After | 16 | 25 | 16 | 7 |

## The 28 modules

`SOURCE_ID` column shows the value **after** this audit; "was" records a change.

| # | Module | `SOURCE_ID` | What it actually serves | Workstream |
|---|---|---|---|---|
| 1 | `charity_commission` | *(none — by design)* | Resolver: attaches charity numbers to already-named entities and types them | cross-cutting (entity resolution) |
| 2 | `clinicaltrials` | `DS037` *(new declaration)* | ClinicalTrials.gov registered protocols and summary results | W07 |
| 3 | `companies_house` | *(none — by design)* | Resolver: attaches company numbers to already-named entities | cross-cutting (entity resolution) |
| 4 | `companies_house_officers` | `DS074` *(new row)* | Officer appointments and persons with significant control, with dates | W07 / institutional graph |
| 5 | `contracts_finder` | `DS070` *(new row)* | Buyer-to-supplier contract awards, UK Contracts Finder OCDS | institutional graph |
| 6 | `crossref` | `DS034` *(new declaration)* | Crossref works metadata | W07 |
| 7 | `education_data` | `DS069` *(new row)* — was `UNREGISTERED:DFE-EES` | Dated aggregate education series, DfE Explore Education Statistics API | W05 |
| 8 | `europepmc` | `DS035` *(new declaration)* | Europe PMC biomedical search with inline abstracts | W07 |
| 9 | `find_a_tender` | `DS071` *(new row)* | Above-threshold buyer-to-supplier awards, Find a Tender OCDS | institutional graph |
| 10 | `fingertips` | `DS066` *(new row)* — was `UNREGISTERED:OHID-FINGERTIPS` | Aggregate area-level public health indicators | W02 (aggregate route) |
| 11 | `govuk_guidance` | `DS030` *(new declaration)* | GOV.UK publications; the only `ISSUES_GUIDANCE_TO` source | W10 (also serves DS054/DS055 documents for W05) |
| 12 | `hansard` | `DS031` | Counts of parliamentary contributions, as a dated series | W10 |
| 13 | `isrctn` | `DS038` | ISRCTN trial registrations | W07 |
| 14 | `legislation` | `DS032` | legislation.gov.uk Atom feed of statutes and SIs | W10 |
| 15 | `media_discourse` | `DS028` | GDELT 2.0 news attention volume, daily | W11 |
| 16 | `nhs_statistics` | `DS068` *(new row)* — was `UNREGISTERED:NHS-ENGLAND-OPEN` | ODS organisation reference data **plus a file index only** (see limits) | W02 (aggregate route) |
| 17 | `nomis` | `DS067` *(new row)* — was `UNREGISTERED:NOMIS` | ONS population, labour market and Census 2021 tables via query API | W01 |
| 18 | `ocds` | *(none — by design)* | Pure parsing/identifier helper; performs no retrieval | none |
| 19 | `ons_datasets` | `DS014` | ONS dataset/publication access | W01 |
| 20 | `ons_population` | `DS014` | ONS mid-year population estimates, bulk CSV | W01 |
| 21 | `openaire` | `DS075` *(new row)* | OpenAIRE Graph aggregated scholarly metadata | W07 |
| 22 | `openalex` | `DS033` *(new declaration)* | OpenAlex works metadata | W07 |
| 23 | `parliament_evidence` | `DS072` *(new row)* | Organisation-to-committee written-evidence submissions | W10 / institutional graph |
| 24 | `pubmed` | `DS036` *(new declaration)* | PubMed / NCBI E-utilities metadata | W07 |
| 25 | `retractions` | `DS043` | Crossref Retraction Watch data | W07 |
| 26 | `ror` | `DS059` | ROR institution identifiers | W07 |
| 27 | `threesixty_giving` | `DS073` *(new row)* | Philanthropic grant awards, 360Giving registry | institutional graph |
| 28 | `ukri_gtr` | `DS042` *(new declaration)* | UKRI Gateway to Research funded projects | W07 |

Declared: **25 of 28** (was 12). Deliberately undeclared: **3**.

## Ids allocated

Ten new rows, `DS066`–`DS075`, taken from the next free number. No existing id was reused or
renumbered, because other documents cite them.

| Id | Source |
|---|---|
| DS066 | OHID Fingertips public health profiles API |
| DS067 | NOMIS ONS labour market, population and Census 2021 query API |
| DS068 | NHS England open route: ODS reference data and statistics publication file index |
| DS069 | DfE Explore Education Statistics public API |
| DS070 | UK Contracts Finder (OCDS) |
| DS071 | UK Find a Tender Service (OCDS) |
| DS072 | UK Parliament committee written evidence |
| DS073 | 360Giving grants registry |
| DS074 | Companies House public register: officers and persons with significant control |
| DS075 | OpenAIRE Graph |

Seven further modules were pointed at **rows that already existed** (`DS030`, `DS033`–`DS037`,
`DS042`). No new row was invented where the register already described the source.

## Deliberately left unregistered, and why

A padded registry is worse than an honest gap. Three modules get no row:

- **`ocds.py`** — a parsing and identifier-extraction helper. It issues no request and holds
  no data of its own; it normalises OCDS payloads for `contracts_finder` and `find_a_tender`,
  which carry the rows (DS070, DS071). A row here would double-count one register as two.
- **`companies_house.py`** — an entity **resolver**. It turns a name into a company number so
  another connector's edge can be attributed correctly. It emits `ResolutionAttempt` records,
  not provenance-bearing evidence. The register it queries is described by DS074, which is
  declared by the module that does emit evidence (`companies_house_officers`).
- **`charity_commission.py`** — likewise a resolver, over the Register of Charities. Its job
  is identifying bodies Companies House could not match and typing them; it contributes no
  observation to any proposition.

## Limits recorded on the new rows

Each new row states what the connector **actually retrieves**, including where that is much
less than its name suggests:

- **DS066 (Fingertips)** supplies aggregate area-level public-health indicators. It supplies
  **no gender-service referral, diagnosis or pathway measure** and cannot substitute for
  individual NHS records. Missing values are an empty `Value` plus a `Value note` and are
  never zero; rows carry overlapping aggregates, so summing double-counts.
- **DS068 (NHS England open route)** does two narrow things, neither of which is clinical
  activity. ODS supplies **organisation reference data only**. The statistics half **can only
  INDEX files, not fetch them**, because `files.digital.nhs.uk` disallows automated retrieval;
  it returns file references, never numbers. A reader who assumes it fetches would badly
  misjudge what W02 holds.
- **DS067 (NOMIS)** overlaps DS014 on Census 2021 gender identity and carries its validity
  problem explicitly: **OSR removed the accreditation on 12 September 2024** and the
  statistics are now "official statistics in development", with documented
  question-comprehension and elevated-uncertainty problems. The question was voluntary and
  asked only of usual residents aged 16 and over.
- **DS070/DS071/DS072/DS073/DS074** each record what their tie does *not* mean: a purchase is
  not influence; submitting to an inquiry is not influencing it; a shared director is a
  structural tie, not coordination; a missing 360Giving grant is not evidence no grant was
  made.
- **DS075 (OpenAIRE)** is an aggregator of DS034/DS036 and repository records, so it is not
  independent corroboration of them.

## Coverage effect

`workstream_source_coverage`, `with_connector` per workstream:

| Workstream | Before | After |
|---|---|---|
| W01 | DS014 | DS014 |
| W05 | — | — |
| W07 | DS038, DS043, DS059 | DS033, DS034, DS035, DS036, DS037, DS038, DS042, DS043, DS059 |
| W10 | DS031, DS032 | DS030, DS031, DS032 |
| W11 | DS028 | DS028 |

Distinct credited source ids rise from 7 to 14; workstreams with at least one credited
connector rise from 4 to 5.

## Open items for a human to decide

These are **recommendations, not edits**. Each would change a file this audit was not
permitted to touch.

1. **W02 still reads as having no connector.** `workstream_source_coverage` joins on the
   `source_ids` column of `registries/workstreams.csv`, and W02 declares
   `DS001;DS002;DS003;DS004;DS047;DS061;DS062` — none of which is the aggregate open route.
   Adding `DS066` and `DS068` to W02's `source_ids` (and `DS069` to W05, `DS067` to W01) is
   what would finally credit the Fingertips work mechanically. It was **not** done here
   because `workstreams.csv` was out of scope. **This is the one remaining half of the gap.**
   Note that this is a *source-list* edit, not an `access_summary` edit: it would not, and
   must not, change any proposition's reachability.
2. **`pipelines/harvest.py` mislabels OpenAIRE.** `SOURCE_IDS` maps `"OpenAIRE"` to `DS041`,
   which is **OSF Registries** — a different source entirely. It should be `DS075`. Not
   changed here because the file was out of scope and because the change relabels the
   provenance of already-stored records; that needs a deliberate decision about existing rows.
3. **`ons_datasets` and `ons_population` both declare `DS014`.** DS014 is specifically the
   Census 2021 gender identity publication, whereas `ons_population` streams mid-year
   population estimates. At least one of these is probably mislabelled and may warrant its own
   row. Not changed here: re-pointing an existing declaration is a larger judgement than
   closing an unregistered gap, and both ids are cited elsewhere.

## Mechanical consequences

- `registries/sources.csv` grew from 65 to 75 rows, so
  `pipelines/registries.EXPECTED_COUNTS["sources.csv"]` was updated 65 → 75. The check remains
  exact; it was not loosened.
- `run_manifest` hashes all `registries/*.csv`, so those hashes change. That is expected and
  correct — the registry genuinely changed.
- `registry_digest` in the feasibility census hashes only `workstreams.csv` and
  `hypotheses.csv`, neither of which was touched, so the census digest is **unchanged** — which
  is itself the evidence that reachability was not altered.
- `harvest_state` uses a new token `ACQUIRED_OPEN_AGGREGATE` on DS066 and DS067, the two
  sources actually retrieved. No code consumes `harvest_state`; every other row remains
  `NOT_YET_ACQUIRED`.

## Tests

Two assertions were updated because the id **genuinely changed**, not to accommodate the edit:

- `tests/unit/test_education_data.py::test_series_is_not_labelled_with_a_document_corpus_source_id`
  — was `SOURCE_ID.startswith("UNREGISTERED:")`, now asserts `SOURCE_ID == "DS069"` **and**
  still asserts it is not `DS054`/`DS055` **and** that it is no longer an `UNREGISTERED:`
  placeholder. Strictly stronger than before.
- `tests/unit/test_nomis.py::test_observed_series_carries_the_real_england_population_and_source_id`
  — was `== "UNREGISTERED:NOMIS"`, now `== "DS067"`.

No test was weakened. Full suite: **857 passed, 3 xfailed** (the three xfails are the
pre-existing `WIRING_AUDIT` ones), exit code 0.
