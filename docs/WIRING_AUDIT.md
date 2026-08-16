# Wiring audit — is each governance component actually invoked on the corpus?

**Date:** 2026-08-16 · **HEAD:** `922c2cc` · **Store:** `runtime/oslt.db`
(6,434 evidence · 824 entities · 1,286 relations · 2 kernel results · 1 synthesis · **0 run manifests**)

**Scope:** every public class and function under `src/oslt_research/governance/`,
`src/oslt_research/evidence/` and `src/oslt_research/ontology/`, plus the pipeline and
persistence functions that set a governance field on a persisted object.

**Method:** enumerate public symbols; grep production consumers, separating them from
tests; then, for each, **query the live store and re-run the component over what is
there**. Code was never trusted on its own — a field populated with a plausible default
is the exact failure mode. Reproducible via `python scripts/audit_wiring.py` (read-only,
`mode=ro`).

**Nothing was fixed.** Three defects are recorded as `xfail(strict=True)` tests in
`tests/integration/test_governance_field_wiring.py`.

## Counts

| Classification | Count |
|---|---|
| WIRED AND EFFECTIVE | 13 |
| WIRED BUT INERT | 6 |
| NEVER INVOKED | 14 |
| NOT APPLICABLE | 5 |

The audit found several genuinely-fine components, and the most important of them —
the three admission gates and the lane classifier — were verified by re-running them
over all 6,434 / 824 / 1,286 persisted objects and confirming the stored verdict
reproduces exactly. Those are not assumed; they are measured.

---

## The table

### WIRED AND EFFECTIVE

| Component | Production consumers | Store query that verified it |
|---|---|---|
| `evidence.provenance.assess_evidence_admission` / `admit_evidence` | `pipelines/harvest.py`, `evidence/abstract_enrichment.py`, `connectors/retractions.py` | Re-ran the gate over all 6,434 records: **0 mismatches** against stored `admitted`. 6,428 admitted, 6 refused with `SOURCE_WORK_RETRACTED`. |
| `evidence.lane_coding.LaneClassifier` / `apply_lane_assignment` / `LaneAssignment` | `pipelines/harvest.py`, `pipelines/counterevidence.py`, `connectors/retractions.py`, `scripts/backfill_lane_coding.py` | All 6,434 records carry a `LaneCoding` (method + `coder_ref=lane-classifier-v1` + `coded_at`). Re-classification reproduces 6,430/6,434; the 4 differences are `SOURCE_DECLARED` retraction codes correctly taking precedence over the text classifier. Lanes: 5,469 UNCLASSIFIED / 431 NULL / 316 BIAS_CRITIQUE / 192 REPLICATION / 13 CORRECTION_RETRACTION / 13 RIVAL. |
| `evidence.study_family.StudyFamilyResolver` | `pipelines/harvest.py`, `pipelines/pilot1.py`, `scripts/backfill_study_families.py` | `dependency_family` prefix is `family:` on 6,434/6,434; **0** records where `dependency_family == metadata['dedup_key']`; 6,222 families over 6,434 records, 157 multi-member. (Scope caveat below.) |
| `evidence.provenance.sha256_text` / `sha256_bytes` / `canonical_json_hash` | 17 connectors, `pipelines/harvest.py`, `pipelines/run_manifest.py`, `governance/preflight.py` | Every record carries a 64-hex `checksum_sha256` and `metadata['content_sha256']`; the `CONTENT_HASH_MISMATCH` branch re-runs clean over the corpus. |
| `evidence.dependency.EvidenceDependencyGraph.summarise` / `.effective_result_weight` | `kernels/academic_knowledge.py`, `pipelines/synthesis.py` | The stored `certainty.source_independence = 0.9114` on both kernel results is `independent_families / admitted_records` from `summarise`; recomputes identically. |
| `evidence.contradiction.assess_pair` / `find_substantive_contradictions` | `pipelines/synthesis.py` | Stored synthesis has `unresolved_contradictions = []`, reproduced. See the caveat under WIRED BUT INERT — the substantive branch has never executed. |
| `evidence.journal.ResearchComputationJournal` / `JournalEntry` | `pipelines/pilot1.py`, `governance/preregistration.py` | `studies/pilot_01_academic_knowledge/outputs/latest/computation-journal.jsonl` exists with an intact 8-entry hash chain; `preregistration-journal.jsonl` likewise. |
| `governance.preflight.run_preflight` / `PreflightReport` | `cli.py`, `api/app.py`, `scripts/preflight.py`, `scripts/check_ai_boundary.py`, `scripts/check_sensitive_files.py` | Not store-facing by design; invoked on every CLI/API entry and in CI scripts. |
| `governance.claim_gates.calibrate_claim_tier` | `pipelines/synthesis.py`, `governance/simulation.py` | Stored synthesis `claim_tier = ASSOCIATION_ONLY`, `limiting_dimension = transportability (0.25)`; recalibrating from the stored `CertaintyVector` returns the same tier. (Partial — see below.) |
| `ontology.admission.assess_entity_admission` / `admit_entity` | 7 register connectors (`companies_house_officers`, `contracts_finder`, `find_a_tender`, `govuk_guidance`, `parliament_evidence`, `threesixty_giving`, `ukri_gtr`) | Re-ran over all 824 entities: **0 would-reject**, matching stored `admitted=1` on all 824. |
| `ontology.admission.assess_relation_admission` / `admit_relation` | same 7 connectors | Re-ran over all 1,286 relations: **0 would-reject**. The `RELATION_UNDATED` branch is live and satisfied — 379 distinct `valid_from` values, none null. |
| `ontology.entities.*` (`InstitutionalEntity`, `InstitutionalRelation`, `SystemDomain`, `EntityRole`, `RelationType`, `normalise_name`) | 10 connectors, `ontology/graph.py`, `ontology/admission.py`, `persistence/sqlite.py`, `pipelines/strand_b.py` | 824 entities across 5 system domains and 8 roles; 1,286 relations across 4 relation types and 5 register dependency families. |
| `ontology.graph.InstitutionalOntologyGraph` / `ResolutionTier` / `merge_tier` / `assess_coupling` | `scripts/readjudicate_coupling.py`, `scripts/harvest_personnel_edges.py` (both load the live store), `pipelines/strand_b.py` | Loads all 824 entities / 1,286 relations from the store and assesses at `STRONG_IDENTIFIER`; 390/824 entities carry a strong identifier, so the tier gate has real discriminating power. (Result-persistence caveat below.) |

### WIRED BUT INERT

| Component | Production consumers | What the store actually contains |
|---|---|---|
| `persistence.SQLiteStore.save_run` + `pipelines.run_manifest.build_run_manifest` | `pipelines/pilot1.py` only | `SELECT COUNT(*) FROM run_manifests` → **0**, while `kernel_results` (2) and `synthesis_outcomes` (1) both reference `run_id = P1-20260815123808`. The persisted run's own journal has **no** `RUN_MANIFEST_SEALED` entry (events present: `PILOT_ONE_STARTED`, 4× `SOURCE_HARVEST_COMPLETED`, `CORPUS_SEALED`, 2× `KERNEL_RESULT_CREATED`). |
| `build_run_manifest(preregistration_ref=...)` | none — no caller ever passes it | A frozen preregistration exists (`studies/.../preregistration/frozen-record.json`, `specification_id=OSLT-P1-ACADEMIC-KNOWLEDGE-V1`, hash `220cd1b1…`), but no code path connects it to a run. Even a manifest that were written would carry `preregistration_ref=None`. |
| `governance.claim_gates.calibrate_claim_tier` — result-level application | `pipelines/synthesis.py` only | `KernelResult.claim_tier` is assigned by hand in `kernels/academic_knowledge.py` (`ASSOCIATION_ONLY if denominator_available else DESCRIPTIVE_EVIDENCE_ONLY`) and never passed through the calibrator. Both stored results are `ASSOCIATION_ONLY` set that way, not calibrated. |
| `evidence.contradiction` substantive branch | `pipelines/synthesis.py` | The only 2 stored results have different `proposition_id`s, so `assess_pair` short-circuits to `NOT_COMPARABLE` before any scope or direction comparison. Every scope-mismatch class and the `SUBSTANTIVE_CONTRADICTION` branch have zero executions against real data. |
| `evidence.study_family.StudyFamilyResolver` — scope of the harvest-path call | `pipelines/harvest.py` | In `execute_harvest` the resolver runs on **one connector's response to one query**, so families can only collapse within a single batch. Cross-connector and cross-proposition duplicates were collapsed only by the one-off `scripts/backfill_study_families.py`. The current corpus is correct; the next harvest will not be, without a re-backfill. |
| `ontology.graph.CouplingAssessment` | `pipelines/strand_b.py`, `scripts/readjudicate_coupling.py` | Computed against the live store, but there is **no table** for it. Verdicts survive only in a JSON output file, so the store cannot answer "what did this graph conclude, and at what tier?". |

### NEVER INVOKED

| Component | Only importers | What the corpus contains instead |
|---|---|---|
| `governance.human_review.kernel_review_decision` / `synthesis_review_decision` / `ReviewDecision` | `tests/unit/test_human_review.py` | `pipelines/synthesis.py` reimplements a narrower rule inline. **Measured divergence:** stored `SYN-P1-20260815123808.human_review_required = False`; `synthesis_review_decision` on the same object returns `required=True` (both standing warnings count as reasons). `kernel_review_decision(KR-…-MD11)` returns `required=True ['FALSIFIER_TRIGGERED']` — and `KernelResult` has no field to hold that verdict at all. |
| `governance.authority.apply_authority_patch` / `AuthorityRecord` / `AuthorityPatch` / `AuthorityError` | `tests/unit/test_authority.py` | The authority lattice is enforced **nowhere**. `LaneCoding.authority_level`, `AIMethodologicalReview.authority_level` and `HumanReviewRecord.authority_level` compute a level that is never compared against anything. No persisted object stores an authority level; the only `"authority": 5` in the repository is inside `frozen-record.json`. `PROTECTED_TYPES` (consent, ethics, legal basis, release) has never gated a mutation. |
| `governance.claim_release.assess_release` / `check_wording` / `wording_for` / `ReleaseDecision` / `WordingCheck` | `tests/unit/test_claim_release.py` | No `ReleasedClaim` has ever been produced or persisted, and no table exists for one. The release gate — counterevidence lanes searched, human review present, wording within tier — has never run. |
| `governance.review_records.AIMethodologicalReview` / `HumanReviewRecord` | `governance/claim_release.py` (itself never invoked) | Zero review records anywhere in the repository or the store. `human_review_reference` on `ReleasedClaim`/`FilmSceneRecord` is therefore unfillable, which is why the release chain has never been attempted. |
| `governance.preregistration.freeze` / `verify_unchanged` / `analysis_is_confirmatory` / `find_freeze_entries` / `PreregisteredSpecification` / `DriftReport` | `tests/unit/test_preregistration.py` | A frozen record exists, so `freeze` was run once ad hoc from an unversioned driver. Nothing in the pipeline calls `verify_unchanged` or `analysis_is_confirmatory`, so no analysis in this repository has ever been *classified* as confirmatory or exploratory. |
| `governance.feasibility.assess_feasibility` / `FeasibilityCensus` | `tests/unit/test_feasibility.py` | No feasibility census is computed or persisted. `Reachability` and `PropositionFeasibility` appear in `design_requirements.py` only, which is itself uninvoked — a two-module island. |
| `governance.design_requirements.requirement_for` / `requirements_for_blocked` / `DesignRequirement` | `tests/unit/test_design_requirements.py` | Nothing derives a design requirement for any blocked proposition. This is the only production consumer of `sample_size.two_group_standardised_mean_sample_per_arm` and `simulation.minimum_detectable_odds_ratio`, so those are transitively dead too. |
| `governance.simulation.simulate_selection_power` / `e_value` / `PowerEnvelope` / `SensitivityBound` / `SimulationResult` | `tests/unit/test_simulation.py` | No power envelope or E-value sensitivity bound is attached to any persisted result. `KernelResult` has no field for one. (Note: the `e_value` grep hit in `connectors/crossref.py` / `nomis.py` is an unrelated local variable, not this function.) |
| `governance.mechanism_simulation.calibrate_mechanism` / `compare_mechanisms` / `normalised_rmse` / `MechanismCandidate` / `CalibrationResult` | `tests/unit/test_mechanism_simulation.py` | `ObservedSeries` is imported by 7 connectors as a data type, which makes the module *look* used; the calibration machinery around it is not. No stored `KernelResult` has `epistemic_status = SIMULATION` or `claim_tier = SIMULATION_ONLY`. |
| `governance.continuity.validate_handoff` / `ResearchState` / `ContinuityHandoff` | `scripts/export_schemas.py` (schema export only), `tests/unit/test_continuity.py` | Exporting a JSON Schema for a type is not invoking it. No handoff has ever been validated. |
| `evidence.lane_coding.cohens_kappa` / `simulate_coder_drift` / `AgreementReport` / `LaneClassifier.coverage` | `tests/unit/test_lane_coding.py` | **No inter-rater reliability has ever been computed on this corpus.** All 6,428 automated codes carry `requires_human_adjudication=True` and there are **zero** `HUMAN_CODER` codings, so kappa's second rater does not exist. `LaneCoding` exists precisely to keep model and human codes distinguishable for IRR — the distinction is recorded and then never used. |
| `evidence.abstract_enrichment.AbstractEnricher` / `EnrichmentSummary` | `tests/unit/test_abstract_enrichment.py` | Yet 204/6,434 records carry `transformation_ids = [RAW_RECORD_TO_EVIDENCE_V1, ABSTRACT_ENRICHED_V1]` — so it was run from an **unversioned ad-hoc script** (`runtime/enrich2.log`). 3.2% coverage, and no versioned code can reproduce it. This directly limits lane coding: 85% of the corpus is UNCLASSIFIED largely because the content is too thin to classify. |
| `pipelines.kernel_harvest.harvest_for_kernels` / `build_proposition_queries` / `KernelHarvestReport` | `tests/unit/test_kernel_harvest.py` | This is the documented main corpus path and it has **no production caller** — not `cli.py`, not `api/app.py`, not any script. 6,434 records exist, so it was driven ad hoc from outside the repository. That is why no `KernelHarvestReport.summary()` (per-proposition coverage, failures, propositions with no results) exists for the corpus. |
| `pipelines.counterevidence.CounterevidenceHarvester` / `LaneSearchRecord` / `CounterevidenceReport` | `tests/unit/test_counterevidence.py` | No `LaneSearchRecord` is persisted anywhere, so the corpus cannot distinguish "the CONTRADICT lane was searched and returned nothing" from "nobody searched it". The store contains **0 CONTRADICT records** and 13 RIVAL — exactly the ambiguity this class was written to remove. `MANDATORY_LANES` is therefore unenforced. |
| `pipelines.strand_b.run_strand_b` / `StrandBRun` | `tests/unit/test_strand_b.py` | The 824 entities and 1,286 relations were written by connector code and ad-hoc scripts, not by the assembly pipeline. Its resolver sequencing, endpoint-survival filter and multi-date coupling assessment have never run on the corpus path. |

### NOT APPLICABLE

| Component | Reason |
|---|---|
| `governance.sample_size.*` (`attainable_envelope`, `design_effect`, `AttainableInferenceEnvelope`) | Genuine on-demand calculator, correctly exposed via `cli.py sample-envelope` and `POST /sample-size/envelope`. Nothing to persist. (`proportion_sample_size` and `source_population_for_events` have no production consumer, but they are library primitives of the same calculator.) |
| `evidence.study_family` helpers (`family_key`, `dedup_key_of`, `is_container_record`, `normalise_author`, `FamilyLink`, `StudyFamilyResolution`) | Internals of `StudyFamilyResolver`, which is wired. Their effect is visible in the store through it. |
| `evidence.dependency.EvidenceDependencyGraph.add_evidence` / `add_result` / `DependencySummary.shared_bias_signatures` | Instance-level graph construction; only the static methods are used in production. Worth noting that **0/6,434 records carry `metadata['bias_signature']`**, so the shared-bias-signature detector has no input even if it were called. |
| `pipelines.film.build_scene_records` / `FilmSceneRecord` | Strictly downstream of `claim_release`, which has produced nothing. Dead by consequence, not independently. |
| `pipelines.registration_linkage.RegistrationPublicationLinker` / `LinkageReport` | Reachable through `connectors/isrctn.py`. Not a defect of the same class, but note **0/6,434 records carry `registration_id` or `linked_registration_id`** — the linkage has never been applied to the corpus, which is why `linked_registration_publications = 0`. |

---

## The finding that matters most

`kernels/academic_knowledge.py` computes orientation-stratified publication rates using

```python
str(item.metadata.get("orientation", "NOT_ASSESSABLE"))
```

**Nothing anywhere assigns `metadata['orientation']`** — 0/6,434 records carry it. So every
admitted record lands in a single `NOT_ASSESSABLE` bucket. That bucket has 5 registration
records in it, which clears the `len(group) < 5` guard, so:

```
registrations                    5
orientation_counts               {'NOT_ASSESSABLE': 6428}
publication_rates_by_orientation {'NOT_ASSESSABLE': 0.0}
denominator_available            True      # <-- the gate opens
```

`denominator_available=True` then promotes both kernel results from
`DESCRIPTIVE_EVIDENCE_ONLY` to `ASSOCIATION_ONLY`, and from `EpistemicStatus.OBSERVATION`
to `ASSOCIATION`. With only one rate in the dict, `spread = 0.0 < 0.10`, so the kernel
takes the "no orientation difference" branch and emits a substantive scientific verdict:

```
KR-…-MD11: WEAKENS   ASSOCIATION_ONLY  falsifier=PARTIALLY_TRIGGERED  impact -0.25
KR-…-MX14: SUPPORTS  ASSOCIATION_ONLY  falsifier=NOT_TRIGGERED        impact +0.25
```

Reproduced against the live corpus by `scripts/audit_wiring.py`. A partial falsification
of MD11 and support for the null model are currently being derived from a comparison
between one group and itself, because a governance field nobody populates defaulted to a
string that reads like a legitimate category. This is the same failure as the lane and
study-family defects, one layer up: the default was plausible, so the gate opened
quietly.

A fix has two halves, and only the first is code: (a) `denominator_available` must
require at least two non-`NOT_ASSESSABLE` orientation groups, so a degenerate denominator
refuses instead of passing; (b) something must actually code orientation, which is a
substantive research task, not a wiring one.

---

## What a fix would involve

Ordered by how much the corpus currently misrepresents.

1. **Orientation denominator** (above). Tighten `AcademicCorpusMetrics.denominator_available`
   to require ≥2 coded groups; until orientation coding exists, the pilot's results should
   read `DESCRIPTIVE_EVIDENCE_ONLY` / `OBSERVATION`.
2. **Corpus path has no manifest.** Give `harvest_for_kernels` a production entry point
   (a `cli.py` command) that calls `build_run_manifest` + `save_run` and passes
   `preregistration_ref` from the frozen record. Until then no persisted result is
   reproducible, and the frozen preregistration is decorative.
3. **`human_review` module unused.** Replace the inline rule in `synthesis.py` with
   `synthesis_review_decision`, and add a field to `KernelResult` to carry
   `kernel_review_decision`. Re-deriving the flag today flips the stored synthesis from
   `human_review_required=False` to `True`.
4. **Counterevidence lanes unproven.** Persist `LaneSearchRecord` and make
   `MANDATORY_LANES` a precondition of any release. 0 CONTRADICT records is currently
   uninterpretable.
5. **Abstract enrichment is unversioned.** Bring the ad-hoc driver into `scripts/`; 3.2%
   enrichment coverage is the main reason 85% of the corpus is UNCLASSIFIED.
6. **IRR machinery has no second rater.** `cohens_kappa` cannot run until some human
   coding exists. Sample and human-code a slice, then compute kappa on it.
7. **Authority lattice unenforced.** Route governance-field mutations through
   `apply_authority_patch`, or delete it — a lattice that is documented and unenforced is
   worse than none, because it reads as a control.
8. **Coupling verdicts not persisted.** Add a table for `CouplingAssessment`.
9. **Study-family scope.** Resolve families corpus-wide after a sweep, not per batch
   inside `execute_harvest`.

---

## The failure mode, named

**Silent default substitution.** A component computes a governance value; no production
caller on the corpus path invokes it; the persisted field falls back to a schema default
or a `.get(key, "PLAUSIBLE_LOOKING_STRING")`; and because the default is a *valid member
of the type*, nothing raises, nothing logs, and every unit test stays green — the
component itself was never wrong.

Its recognisable signatures, all of which appeared here:

- A governance column with **exactly one distinct value** across the whole corpus
  (`source_status=VERIFIED` 6434/6434, `epistemic_status=OBSERVATION` 6434/6434,
  `access_class=OPEN` 6434/6434, `orientation=NOT_ASSESSABLE` 6434/6434).
- An enum whose default is the "unknown" member and which nothing ever moves off it
  (`lane=UNCLASSIFIED`, before the fix).
- A component whose **only importers are `tests/`**.
- A component whose only production importer is another component whose only importers
  are tests (`feasibility` → `design_requirements` → tests).
- A parameter that exists on a production function and is **never passed by any caller**
  (`build_run_manifest(preregistration_ref=...)`).
- A table with **0 rows** whose foreign concept is referenced by populated tables
  (`run_manifests` = 0, referenced by `kernel_results` and `synthesis_outcomes`).
- A gate whose refusal path has **never fired** on the corpus, because the field it tests
  is hardcoded upstream (`SOURCE_STATUS_UNVERIFIED`, `LICENCE_OR_APPROVAL_MISSING`,
  `TRE_SDE_*` — all unreachable while `harvest.py` hardcodes `VERIFIED` / `OPEN`).

Unit tests cannot see any of this, because in every case the unit under test is correct.
Only the store, queried against the code, can.

## Proposed standing check

`tests/integration/test_governance_field_wiring.py` (added by this audit) runs the
components against the **live persisted corpus** rather than a fixture — a fixture proves
a component works, only the store proves it *ran*. It skips when no corpus is present, so
a fresh clone and CI stay honest rather than passing on an empty database.

It currently holds five passing guards and three `xfail(strict=True)` defect records:

| Test | Asserts | Status |
|---|---|---|
| `test_every_record_carries_lane_coding_provenance` | no record has a lane without a `LaneCoding` | passes |
| `test_stored_lanes_reproduce_from_the_classifier` | every `AUTOMATED_CLASSIFIER` lane re-derives | passes |
| `test_dependency_families_are_resolved_not_naive_dedup_keys` | <10% of families equal their `dedup_key` | passes |
| `test_evidence_admission_gate_reproduces_the_stored_verdict` | the gate re-runs to the stored verdict | passes |
| `test_ontology_admission_gates_reproduce_the_stored_verdicts` | same for entities and relations | passes |
| `test_every_persisted_run_has_a_manifest` | every `run_id` in `kernel_results`/`synthesis_outcomes` resolves to a `RunManifest` | **xfail** |
| `test_stored_human_review_flag_agrees_with_the_governance_module` | stored flag == `synthesis_review_decision` | **xfail** |
| `test_orientation_coding_is_populated_for_the_denominator` | some admitted record carries a real orientation | **xfail** |

The markers are **strict** on purpose: when the wiring is fixed the test turns red and
forces the marker to be removed, rather than a repaired defect quietly staying filed as
expected.

**The generalisable rule the three xfails encode:** for every governance field on a
persisted object, assert that the corpus is not uniformly at that field's default, and
assert that re-running the owning component over the store reproduces the stored value.
The first catches "never invoked"; the second catches "invoked, then overwritten". Add a
row to this file whenever a new governance field is introduced — that is cheaper than
finding the fourth defect of this shape by accident.
