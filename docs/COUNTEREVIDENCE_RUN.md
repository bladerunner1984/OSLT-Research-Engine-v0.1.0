# Counterevidence lane sweep — first live run

**Date:** 2026-08-16 · **Run:** `CE-20260816013116` · **Source:** Europe PMC (DS035) only
**Store:** `runtime/oslt.db` (backed up to `runtime/oslt.db.pre-counterevidence` before the write)
**Artefacts:** `data/counterevidence_run.json`, table `lane_search_records` (35 rows)

## What this run changes

`docs/WIRING_AUDIT.md` recorded that `CounterevidenceHarvester` had no production caller,
that no `LaneSearchRecord` was ever persisted, and that the corpus therefore held **0
CONTRADICT records with no way to tell that zero apart from "nobody looked"**.

The zero is now interpretable. 35 lane searches are persisted, each carrying its status,
its queries and its result count. Every mandatory lane (`CONTRADICT`, `RIVAL`, `NULL`)
was searched to completion for every proposition in scope, and the store can now be asked
"did anyone look?" and answer.

## Wiring

| Where | What |
|---|---|
| `pipelines/counterevidence.py` | `LaneSearchRecord.status` vocabulary; `genuine_zero`; `MandatoryLaneGapError`; `save_lane_searches` / `load_lane_searches` and the `lane_search_records` table; request pacing and 429/503 backoff; `SUPPORT` query terms mirroring `CONTRADICT` |
| `pipelines/kernel_harvest.py` | `harvest_counterevidence_for_kernels` — the sweep on the corpus path, one report per proposition, persisted per lane |
| `cli.py` | `oslt counterevidence` (exits **1** if any mandatory lane is unsearched) and `oslt kernel-harvest` — the corpus path had no production entry point at all before this |
| `scripts/run_counterevidence.py` | the live runner; `--dry-run` prints the exact queries without issuing a request |
| `tests/integration/test_governance_field_wiring.py` | standing guard: mandatory lanes present in the store, and no row may claim a zero it did not establish |

### Searched-zero vs unsearched — how the distinction is stored

Four statuses, one per lane per proposition:

| Status | Meaning |
|---|---|
| `NOT_ATTEMPTED` | the lane was never included in the sweep — a **GAP** |
| `UNSEARCHED_ERROR` | every query failed (HTTP, timeout, exhausted 429 backoff) — a **GAP**, never a zero |
| `SEARCHED_PARTIAL` | some queries completed, some failed — searched, but not citable as an absence |
| `SEARCHED_COMPLETE` | every query completed against every source |

`genuine_zero` is true only for `SEARCHED_COMPLETE` **and** `records_returned == 0`. A
partial sweep that returned nothing is deliberately *not* a zero: the part that failed is
exactly where the missing records would have been. `MANDATORY_LANES` is enforced —
`CounterevidenceReport.enforce_mandatory_lanes()` raises, and the CLI exits non-zero.

## Scope

Five propositions: **MD11** and **MX14** (the two with persisted kernel results) plus
**MX08**, **MX09**, **MX11** — the null/rival model families those results are implicitly
compared against. 7 lanes × 3 terms (RIVAL: 4) = 22 queries per proposition, 110 requests,
paced at 1.2 s from the first request. Europe PMC only, deliberately: OpenAlex was
rate-limited and a 429-shaped lane is `UNSEARCHED`, which would have suppressed the sweep
rather than improved it. That exclusion is a scope limit, not a failed search.

## Query construction

Base concepts come from `build_proposition_queries`, which derives them from the
registry's `domain` and `primary_outcome_construct` and **never** from `statement` —
searching the statement retrieves papers phrased like the claim. Lane terms are appended
to that one unmodified stem, identically for every lane.

| Proposition | Base concept (from domain + outcome) |
|---|---|
| MD11 | `academic selection onset identity referral pathway outcome` |
| MX14 | `academic direction bias model-specific outcome` |
| MX08 | `null social effect model-specific outcome` |
| MX09 | `null institutional effect model-specific outcome` |
| MX11 | `common-cause alternative model-specific outcome` |

### The symmetry pair

`SUPPORT` exists in `LANE_QUERY_TERMS` **only** so the CONTRADICT search can be judged
rather than trusted. Same count, same grammatical form, same position:

| # | SUPPORT | CONTRADICT |
|---|---|---|
| 1 | `<stem> consistent findings` | `<stem> contradictory findings` |
| 2 | `<stem> confirming evidence` | `<stem> conflicting evidence` |
| 3 | `<stem> consistent with previous` | `<stem> inconsistent with previous` |

Both returned **75 records per proposition** — identical retrieval volume, which is what
a symmetric pair should produce when the index is not the binding constraint.

Other lanes: NULL `no significant association` / `null findings` / `no difference between
groups`; RIVAL `alternative explanation` / `competing hypothesis` / `ascertainment
artefact` / `reverse causation`; REPLICATION `replication study` / `failure to replicate`
/ `independent replication`; BIAS_CRITIQUE `risk of bias` / `methodological critique` /
`systematic review limitations`; CORRECTION_RETRACTION `retracted` / `expression of
concern` / `correction to`. The full expansion is in `data/counterevidence_run.json`
under `planned_queries`.

## Results

Gross records returned (before cross-lane dedup) and records the classifier confirmed
into that lane, summed over the five propositions:

| Lane | Mandatory | Returned | Lane-confirmed | Status | Genuine zeros |
|---|---|---|---|---|---|
| SUPPORT | | 375 | **0** | 5/5 SEARCHED_COMPLETE | 0 |
| CONTRADICT | ✓ | 375 | **0** | 5/5 SEARCHED_COMPLETE | 0 |
| RIVAL | ✓ | 500 | 3 | 5/5 SEARCHED_COMPLETE | 0 |
| NULL | ✓ | 375 | 60 | 5/5 SEARCHED_COMPLETE | 0 |
| REPLICATION | | 375 | 106 | 5/5 SEARCHED_COMPLETE | 0 |
| BIAS_CRITIQUE | | 375 | 87 | 5/5 SEARCHED_COMPLETE | 0 |
| CORRECTION_RETRACTION | | 375 | 5 | 5/5 SEARCHED_COMPLETE | 0 |

Corpus: 6,434 → **7,071** evidence records (+637 unique). 6 records remain refused
admission with `SOURCE_WORK_RETRACTED`; the admission gate ran on every new record.

**No lane in this run returned a genuine zero.** Every mandatory lane returned records.
The `genuine_zero` column exists and is exercised by tests, but the live answer is that
the literature is not empty — the previous emptiness was ours.

## The finding that matters

**CONTRADICT is still 0, and the reason is now known and is not the literature.**

`LaneClassifier` structurally never assigns `SUPPORT` or `CONTRADICT`. Both lanes are
*proposition-relative* — the same result contradicts one model family and supports
another — so the classifier routes anything directional to human adjudication instead of
guessing (see its docstring). The corpus's 0 CONTRADICT was therefore **overdetermined**:
before this run nobody had searched, and even had they searched, the automated coder
could not have produced the lane.

The state has changed from one uninterpretable zero to a different, interpretable one:

- **before:** 0 CONTRADICT records, 0 searches. Indistinguishable from confirmation bias.
- **after:** 0 CONTRADICT records, 5 recorded complete CONTRADICT searches, **375 retrieved
  records (171 unique) sitting in the adjudication queue** as `UNCLASSIFIED` with
  `requires_human_adjudication=True`.

That is a queue, not a refutation. Under rule 4 every classifier lane is `A5`
`requires_human_adjudication=True`; nothing in this run is a verified counterexample to
anything.

## Limits a successor must not gloss over

1. **Every query saturated its `max_records=25` cap.** Retrieval was never the binding
   constraint, so these counts are ceiling-limited, not literature-limited. Raising the
   cap will change every number in the table above.
2. **Precision is untested.** Europe PMC ANDs a long free-text stem; a 10-word stem plus a
   lane term returning 25 hits every time means the match is loose. Whether those 375
   CONTRADICT-lane records are *about* the proposition is exactly the human adjudication
   that has not happened.
3. **One source.** Europe PMC is biomedical. MD11/MX14 are partly about publication
   sociology, which Europe PMC indexes thinly. OpenAlex, once un-rate-limited, is the gap.
4. **Five of 64 propositions.** The other 59 remain `NOT_ATTEMPTED` — a GAP, and recorded
   as one. `oslt counterevidence` with no `--proposition` sweeps all 64.
5. **CONTRADICT and SUPPORT counts can only ever be 0 until a human codes them.** Do not
   read a future 0 in those two columns as a search result; read the `records_returned`
   column instead, which is the honest measure of whether anyone looked.

## Not fixed by this work

The three `xfail(strict=True)` defects in
`tests/integration/test_governance_field_wiring.py` all still xfail and their markers must
stay: no `RunManifest` on the corpus path, `human_review` unused, `orientation` unpopulated.
Item 2 of the audit's fix list is now half-done — `harvest_for_kernels` has a production
entry point (`oslt kernel-harvest`) — but it still does not build or save a manifest.
