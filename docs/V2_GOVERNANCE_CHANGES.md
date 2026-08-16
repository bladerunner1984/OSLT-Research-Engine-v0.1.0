# v2 governance changes: severity-weighted corroboration, and the open-testable defect

**Date:** 2026-08-16. **Implements:** `docs/PROJECT_V2_SPECIFICATION.md` §5 "Fix", items 1 and 2.
**Files:** `src/oslt_research/governance/mechanism_simulation.py`,
`src/oslt_research/governance/feasibility.py`,
`src/oslt_research/governance/design_requirements.py`, plus unit tests.
**Not touched:** `registries/hypotheses.csv`, any `access_summary` field,
`docs/ACADEMIC_HANDOFF.md`, `docs/WIRING_AUDIT.md`, `docs/PROJECT_V2_SPECIFICATION.md`,
`docs/OPEN_TESTABLE_FINDINGS.md`.

Both changes make the engine say *less* in one direction and *more* in another. Fix 1 adds a
positive channel that did not exist. Fix 2 removes six propositions from the testable set. The
net is fewer claims and more information, which is the correct trade for this project.

---

## Fix 1 — severity-weighted corroboration

### The defect

`calibrate_mechanism` returned `WEAKENS` on refutation and `INCONCLUSIVE` on survival. A
mechanism that survived a test which could have killed it was recorded identically to one
nobody ran. That is refutation without corroboration: half of falsificationism, and the half
that produces no knowledge.

### What severity is

Severity is a property of the **test**, not of the mechanism, and it is computed from the run
rather than asserted by an analyst. Three factors, each in `[0,1]`:

| Factor | Definition | Why |
|---|---|---|
| `rejection_fraction` | `(grid_size - accepted) / grid_size` | The direct answer to "what could this test have killed?" A grid nothing was rejected from was never a test. |
| `tolerance_tightness` | `max(0, 1 - tolerance / dispersion)` where `dispersion = std(observed) / range(observed)` | Expressed in the same units as `normalised_rmse`, so the comparison is like-for-like. At zero, a flat line through the series mean would have passed. |
| `series_constraint` | `(n - 2) / n` over the observed periods | Two points fix a level and a slope; only what is left over constrains a shape. Three periods constrain almost nothing, eighty-four constrain a great deal. |

```
severity index = (rejection_fraction * tolerance_tightness * series_constraint) ** (1/3)
```

The **geometric** mean is deliberate. Any one factor at zero drives the index to zero, which
is the intended behaviour: a test whose grid could never have been rejected, or whose
tolerance is wider than the series' own variation, or which constrains almost no independent
periods, is uninformative however well the other two score. An arithmetic mean would let two
strong factors launder one fatal weakness into a respectable-looking number.

Bands are declared in `SEVERITY_BANDS`, not tuned per run — a threshold chosen after seeing
which side of it a result fell on is not a threshold:

| Band | Index |
|---|---|
| `HIGH` | ≥ 0.60 |
| `MODERATE` | ≥ 0.35 |
| `LOW` | ≥ 0.15 |
| `NEGLIGIBLE` | ≥ 0.00 |

### The new vocabulary, and where it deliberately does *not* go

`FindingDirection` is the project-wide **claim** vocabulary. It was not extended. Promoting a
survival into `SUPPORTS` there is exactly the confirmationism `CALIBRATION_DISCLOSURE`
forbids, and it would have leaked a simulation-only judgement into every downstream tally.
`finding_direction` still reads `WEAKENS` on refutation and `INCONCLUSIVE` on survival, in
every case, at every severity.

The third outcome lives in a new, module-local, simulation-only enum, `Corroboration`:

| Value | When |
|---|---|
| `NOT_APPLICABLE_REFUTED` | The mechanism was refuted. |
| `NO_CORROBORATION_TEST_NOT_SEVERE` | Survived at `NEGLIGIBLE` severity. This is silence, not a result. |
| `COMPATIBLE_ONLY` | Survived at `LOW` or `MODERATE`. Compatibility and no more. |
| `CORROBORATED_AT_HIGH_SEVERITY` | Survived at `HIGH`. Corroboration **at a stated severity**. |

`compare_mechanisms` gains `corroborated_at_high_severity` (a list, separate from
`compatible`) and a per-mechanism `severity` block. Its `interpretation_bound` keeps every
sentence it had and adds one: a corroborated survivor "is corroboration at a stated severity
and still may not be reported as support for the proposition being true."

### The asymmetry is not weakened

- Compatibility at `LOW` severity returns `INCONCLUSIVE` and `COMPATIBLE_ONLY`
  (`test_low_severity_survival_is_still_inconclusive_and_not_corroboration`).
- Compatibility at `HIGH` severity *still* returns `INCONCLUSIVE`, still carries "This is not
  support: compatibility is cheap", and adds an explicit "NOT a statement that the mechanism
  is true" to the narrative.
- Every pre-existing test in `tests/unit/test_mechanism_simulation.py` passes unmodified,
  including `test_compatibility_is_never_reported_as_support`.

### AS08 re-run under the new vocabulary

Re-run over the persisted `data/open_testable_findings.json` quantities (MHSDS MHS01, the 71
providers submitting in all 84 months, seven financial years 2017/18–2023/24, tolerance 0.15):

| Mechanism | Grid | Accepted | Best distance | `finding_direction` | Severity | Band | Corroboration |
|---|---|---|---|---|---|---|---|
| `COVERAGE_ONLY` | 25 | **0** | 36% | `WEAKENS` | **0.74** | `HIGH` | `NOT_APPLICABLE_REFUTED` |
| `REAL_GROWTH_WITHIN_FIXED_COHORT` | 45 | **2** | 12.4% | `INCONCLUSIVE` | **0.73** | `HIGH` | `CORROBORATED_AT_HIGH_SEVERITY` |

Both tests rejected the tolerance against a dispersion 57% wider than it, over seven periods.
`COVERAGE_ONLY` rejected 100% of its grid; `REAL_GROWTH_WITHIN_FIXED_COHORT` rejected 96% of
its own and survived at 2 points.

What the new vocabulary says, precisely:

- `COVERAGE_ONLY` was refuted by a test at severity 0.74. v1 recorded `WEAKENS` with no
  measure of how hard the test was; the refutation was always the strong result here and now
  carries a number that says so.
- `REAL_GROWTH_WITHIN_FIXED_COHORT` is **corroborated at severity 0.73**. It survived a grid
  from which 43 of 45 parameterisations were rejected. Under v1 this was recorded identically
  to a mechanism nobody tested.

What it does **not** say: that real growth within the fixed cohort is true, or that AS08 is
supported. Only 2 of 45 parameterisations survived, so what is corroborated is a narrow band
of growth rates, on **one** aggregate series, and a rival mechanism not yet written may
reproduce the same series equally well. `finding_direction` for AS08 remains `WEAKENS` (of
`COVERAGE_ONLY`), which is the finding the project is licensed to report.

---

## Fix 2 — the open-testable defect

### The defect

`assess_feasibility` marked a proposition `OPEN_TESTABLE` on required-**workstream**
availability alone. It never checked that any required workstream carries the **predictor the
proposition's own prediction names**. Six of the ten inconclusive findings in the 2026-08-16
run trace to this, and each had to record the same limit line after the fact: *"feasibility
marks this OPEN_TESTABLE on required-workstream availability, but no required workstream
carries the predictor the prediction names."*

### What was implemented

A second **necessary** condition, evaluated only after access has been settled. It never
relabels access: `access_summary` tokens still decide `NEEDS_PRIMARY_COLLECTION` and
`NEEDS_RESTRICTED_ACCESS`, and those still take precedence
(`test_access_still_takes_precedence_over_a_missing_predictor`). A new `Reachability` member,
`NEEDS_PREDICTOR_SOURCE`, applies only where every required workstream is open but the
predictor is absent from all of them.

The check uses what the registry actually has:

- `hypotheses.csv → prediction` — the registered prediction text.
- `workstreams.csv → data_to_accumulate` (and `workstream`) — what each workstream carries.

The bridge between them is a **declared lexicon** (`PREDICTOR_LEXICON`): each entry pairs the
phrases whose presence in a prediction means it *names* that predictor with the phrases in
`data_to_accumulate` that mean a workstream *carries* it. Six entries, each auditable against
`workstreams.csv` in seconds:

`DISCLOSURE_OR_HELP_SEEKING`, `AWARENESS_OR_MEDIA_ATTENTION`, `ACCESS_GRADIENT`,
`FOLLOW_UP_OF_INDIVIDUALS`, `ADOPTION_OUTCOME_PER_NODE`, `CROSS_JURISDICTION_PANEL`.

Two conservatism rules, both tested:

1. A prediction naming **no** lexicon concept is never blocked. Absence of a lexicon entry is
   not evidence of absent data; this check exists to remove false testability, not to
   manufacture false blockage.
2. A registry with **no** `data_to_accumulate` column returns no missing predictors at all. An
   unpopulated column is missing evidence, not evidence of missing data.

### The registry limitation, and the minimal column that would fix it

The lexicon is a **workaround, and should be read as one.** The registry cannot express a
proposition's predictor: `hypotheses.csv` carries `primary_outcome_construct` (which is the
*outcome* side, and is the identical string `recorded prevalence/referral/service outcome` for
all twelve AS propositions, so it discriminates nothing) but has **no predictor column at
all**. Matching declared phrases against free text is the least-bad reading of what is there;
it is not a substitute for the registry saying what it means.

**Proposed minimal registry change — one column, not a schema:**

> Add `predictor_construct` to `registries/hypotheses.csv`: a `;`-delimited list of predictor
> concept ids drawn from a controlled vocabulary, human-written, one entry per proposition.
> `missing_predictors` would then read that column directly and the lexicon's
> `prediction_terms` half — the guessing half — would be deleted outright, leaving only the
> `data_terms` half, which is a straightforward mapping onto `data_to_accumulate`.

This was **not** done here: populating it is human judgement over 64 registered predictions,
it is a registry edit this task excludes, and a guessed column would be worse than none.

### The new split

| Reachability | Before | After | Δ |
|---|---|---|---|
| `OPEN_TESTABLE` | 16 | **10** | **−6** |
| `NEEDS_PREDICTOR_SOURCE` | — | **6** | **+6** |
| `NEEDS_RESTRICTED_ACCESS` | 16 | 16 | 0 |
| `NEEDS_PRIMARY_COLLECTION` | 25 | 25 | 0 |
| `NEEDS_INDIVIDUAL_LEVEL` | 7 | 7 | 0 |
| **Total** | 64 | 64 | 0 |

**Every proposition that changed status, and why.** All six moved
`OPEN_TESTABLE → NEEDS_PREDICTOR_SOURCE`; no proposition moved in any other direction.

| ID | Required set | Predictor its prediction names | Where that predictor actually lives |
|---|---|---|---|
| **AS04** Disclosure | W01;W02;W09;W10 | `DISCLOSURE_OR_HELP_SEEKING` — a disclosure or help-seeking indicator | W12 (narratives, interviews) — `PRIMARY_RESEARCH` |
| **AS05** Awareness | W01;W02;W09;W10 | `AWARENESS_OR_MEDIA_ATTENTION` — search volume, media attention | W11 (news corpora, GDELT), W06 (search behaviour) |
| **AS07** Geographic access | W01;W02;W09;W10 | `ACCESS_GRADIENT` — distance-to-service or need proxy | **no workstream** carries it |
| **AS12** Follow-up attrition | W01;W02;W09;W10 | `FOLLOW_UP_OF_INDIVIDUALS` — a cohort followed through time | W04 (repeated measures) — `RESTRICTED_COHORT` |
| **TH05** Network effects | W07;W09;W10 | `ADOPTION_OUTCOME_PER_NODE` — a per-node adoption outcome | **no workstream** carries it |
| **TH08** Cultural displacement | W01;W05;W10;W11 | `CROSS_JURISDICTION_PANEL` — a cross-jurisdiction / macro panel | **no workstream** carries it |

This is exactly the set the 2026-08-16 findings run identified after the fact, now caught
before the run. AS05 is the clearest case and the one §5 names: its awareness predictor sits
in W11, which is not in its required set.

Two further propositions name a lexicon predictor their required set lacks — **MD06**
(`ADOPTION_OUTCOME_PER_NODE`) and **MX15** (`CROSS_JURISDICTION_PANEL`) — but both were already
blocked for a stronger reason (`NEEDS_INDIVIDUAL_LEVEL` and `NEEDS_RESTRICTED_ACCESS`
respectively) and their status is unchanged. Their `missing_predictors` field is populated
regardless, because it is true of them.

### Consequences that must be reported plainly

- **The open-testable set is now 10, not 16.** Six of the sixteen could not be run. Reporting
  them as testable produced six `INCONCLUSIVE` findings for a reason knowable in advance.
- **The ballot is still unequal, and slightly more so.** The testable set is now
  ASCERTAINMENT_SERVICE 8 / MULTIFACTORIAL 2 — dominance rises from 12/16 (75%) to 8/10 (80%).
  `INTRINSIC_RECOGNITION`, `MIXTURE_HETEROGENEITY` and `NULL_OR_ALTERNATIVE` still have zero.
  Every asymmetry warning still fires, and
  `COMPARATIVE_SUPPORT_OVER_AN_UNEQUAL_BALLOT_MEASURES_DATA_ACCESS_NOT_EXPLANATION` is
  unchanged. Fix 2 removes false testability; it does not improve the ballot.
- **`docs/OPEN_TESTABLE_FINDINGS.md` and `data/open_testable_findings.json` are now a record
  of a superseded census.** They were left untouched as instructed. The six affected findings
  already state the defect in their own limits; they should be re-issued as
  `NEEDS_PREDICTOR_SOURCE` rather than as inconclusive results.
- **`design_requirements` prices the new class correctly.** `NEEDS_PREDICTOR_SOURCE` gets its
  own branch: registry amendment plus a harvest, no participants, no ethics. Pricing it as a
  prospective cohort would have overstated it by orders of magnitude.
- **The persisted census was re-run** via `scripts/run_feasibility_census.py --apply`, as
  `test_a_feasibility_census_is_persisted_and_still_reproduces` requires. Its
  `asymmetry_changed` flag is now `true` against the figures quoted in
  `docs/ACADEMIC_HANDOFF.md`, which that document will need to reflect when it is next
  revised.

---

## Test result

`.venv/Scripts/python.exe -m pytest -q` → **963 passed, 3 xfailed, exit code 0.**

No existing test was edited, no `xfail(strict=True)` was removed, and no assertion was
weakened. 16 tests were added (9 for severity, 7 for predictor availability), including
`test_low_severity_survival_is_still_inconclusive_and_not_corroboration` and
`test_registry_without_the_data_column_is_not_read_as_full_of_holes`.
