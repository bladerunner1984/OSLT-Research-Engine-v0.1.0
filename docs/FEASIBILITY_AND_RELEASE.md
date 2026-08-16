# Feasibility census and claim release — two islands wired

**Date:** 2026-08-16 · **Store:** `runtime/oslt.db` (backed up to `runtime/oslt.db.pre-feasibility`)
**Runs sealed:** `FEAS-20260816023725` (census, `FC-20260816023725`), `REL-20260816023328` (claim release)
**Artefacts:** `data/feasibility_census.json`, `data/claim_release.json`,
tables `feasibility_censuses`, `proposition_feasibility`, `design_requirements`,
`claim_release_assessments`, `released_claims`.

`docs/WIRING_AUDIT.md` recorded `governance/feasibility.py` + `governance/design_requirements.py`
as a two-module island whose only importers were tests, and `governance/claim_release.py` as
never having executed at all. Both now run on the corpus path, persist, and are guarded by
tests against the live store.

---

## 1. The census re-run: nothing moved

| Reachability | Quoted in `ACADEMIC_HANDOFF.md` | Re-run 2026-08-16 | Changed |
|---|---|---|---|
| `OPEN_TESTABLE` | 16 | **16** | no |
| `NEEDS_PRIMARY_COLLECTION` | 25 | **25** | no |
| `NEEDS_RESTRICTED_ACCESS` | 16 | **16** | no |
| `NEEDS_INDIVIDUAL_LEVEL` | 7 | **7** | no |

64 propositions, identical to the figure quoted.

### The ballot asymmetry has not changed, and that matters

| Model family | Propositions | Open-testable |
|---|---|---|
| `ASCERTAINMENT_SERVICE` | 12 | **12** |
| `MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL` | 28 | 4 |
| `INTRINSIC_RECOGNITION` | 8 | **0** |
| `MIXTURE_HETEROGENEITY` | 12 | **0** |
| `NULL_OR_ALTERNATIVE` | 4 | **0** |

The three families with zero open-testable propositions are the same three. `coverage_asymmetry()`
returns the same three warnings it did when the figure was first quoted:

```
MODEL_FAMILIES_WITH_NO_OPEN_TESTABLE_PROPOSITION:INTRINSIC_RECOGNITION,MIXTURE_HETEROGENEITY,NULL_OR_ALTERNATIVE
OPEN_TESTABLE_SET_DOMINATED_BY:ASCERTAINMENT_SERVICE:12/16
COMPARATIVE_SUPPORT_OVER_AN_UNEQUAL_BALLOT_MEASURES_DATA_ACCESS_NOT_EXPLANATION
```

Every one of `ASCERTAINMENT_SERVICE`'s twelve propositions is testable now. Three rival
families have none. **Any comparative support index computed over open data will return
`ASCERTAINMENT_SERVICE` as the leader, and that result carries no evidential weight about
explanation**, because its rivals were never on the ballot. This is unchanged, and it should
be stated every time a comparative figure is produced.

### Why the connector additions could not have moved it — the more useful finding

The task that prompted this run assumed the census might have drifted because connectors for
Fingertips, NOMIS, NHS ODS, Companies House officers and GDELT landed and W02 went from 0 to
218 usable series.

**It could not have drifted, and it cannot.** `assess_feasibility` reads exactly two files —
`registries/workstreams.csv` and `registries/hypotheses.csv` — and derives `Reachability` from
the `access_summary` tokens a human wrote in the workstream row. It never consults the
connector package or the store. Neither registry file has been touched since the initial
import commit (`c6f4012`); the digests are recorded with the stored census.

So the census answers **"is there an open route in principle?"**, not **"have we built the
thing that walks it?"**. Those are different questions and conflating them is dangerous in
both directions:

- A workstream can declare `OPEN_AGGREGATE` with no connector implementing it. W02 was
  `OPEN_AGGREGATE` before Fingertips existed, so its propositions were already counted
  testable while nothing could actually fetch them.
- Feeding connector inventory back into `Reachability` would let an engineering gap
  masquerade as an access gap and vice versa, and the census is quoted as an *access*
  statement.

The census is therefore left as a pure function of the registry, and the live inventory is
recorded **beside** it as a separate overlay (`workstream_source_coverage`). What the overlay
shows:

- Only **12 of 28** connector modules declare a registry `SOURCE_ID` at all. The other 16
  (`openalex`, `europepmc`, `crossref`, `pubmed`, `companies_house*`, `contracts_finder`, …)
  declare none, so their workstream is **UNKNOWN, not absent** — the overlay reports them as
  `connector_status_unknown` and never as "no connector", because understating coverage here
  would be a plausible-looking default in the opposite direction.
- Four connectors declare `UNREGISTERED:` ids (`DFE-EES`, `NHS-ENGLAND-OPEN`, `NOMIS`,
  `OHID-FINGERTIPS`) — real live sources with no row in `registries/sources.csv`. They are not
  matched to a workstream by name. **This is the actionable gap**: the W02 Fingertips work
  cannot be credited to W02 by any mechanical route, because the connector does not say which
  registry source it serves.

### Design requirements

`requirements_for_blocked` now runs over all 48 blocked propositions and persists to
`design_requirements`. Every row carries `claim_tier = SIMULATION_ONLY` and
`epistemic_status = SIMULATION` **in its own columns**, not only inside the payload blob, so a
priced study sitting next to real results cannot be read as a finding by a careless join. A
test asserts this.

---

## 2. Claim release: eleven claims assessed, zero released

`scripts/assess_claim_release.py` puts this project's own published prose through the gate.
**No `ReleasedClaim` was produced.** That is the correct outcome, and the refusals are
persisted — a refusal with no recorded reason is unauditable, so the failure list is stored.

### Wording that FAILS its declared tier

`docs/REFERRAL_BASELINE.md` is the **only** one of the four documents that declares a tier
(`"**Status:** descriptive, no mechanism calibrated."` → `DESCRIPTIVE_EVIDENCE_ONLY`), and it
**fails its own declaration**. Three prohibited phrases, at that tier:

| Phrase | Line | Text | Assessment |
|---|---|---|---|
| `effect of` | 54 | "it is the intended and documented **effect of** successive NICE guideline revisions and awareness campaigns" | **Genuine failure.** A causal attribution about why referrals rose, in a document declaring itself descriptive with no mechanism calibrated. That the attribution is uncontroversial is not a defence — the tier bans the construction, and "it is not in dispute" is precisely the framing under which unearned causal language travels. |
| `predicts` | 76, 77, 198 | "ASCERTAINMENT_SERVICE **predicts** referral growth…"; "…no social-transmission account **predicts** should move at all" | **Genuine, but of a second kind.** These describe what a *model family* predicts, not what the data predict. The tier list cannot tell the two apart. The construction is still the one the ban targets, and a reader skimming the section will take "ASCERTAINMENT_SERVICE predicts X, and X is observed" as support — which the document elsewhere explicitly denies ("compatibility is not support"). |
| `because of` | 55 | "recorded here **because of** what it implies for method" | **False positive.** Editorial rationale for including the section, not a claim about the world. Recorded rather than suppressed: the check is a phrase matcher and its false-positive rate is part of what it is. |

Two headline sentences also fail individually: `REFERRAL-BASELINE-NICE` (`effect of`) and
`REFERRAL-BASELINE-BALLOT` (`predicts`).

**What the check missed.** "That is the arithmetic signature of a **lowered referral
threshold**" passes cleanly, and it is arguably the strongest causal claim in the document —
a mechanism named from a rate and a yield. `TIER_WORDING` has no entry for "signature of",
"consistent with a lowered X", or any of the constructions that carry causal weight without a
banned verb. The wording gate catches vocabulary, not inference. That limit should be stated
wherever the gate's verdict is cited.

### The larger failure: three of four documents declare no tier at all

`CENSUS_2021_GENDER_IDENTITY.md`, `MX09_FALSIFICATION_RUN.md` and `COUNTEREVIDENCE_RUN.md`
state no claim tier anywhere. All three are refused with `CLAIM_TIER_NOT_DECLARED`.

No tier was assumed for them. An assumed tier decides the verdict, which would make the
verdict a statement about the assumption. An **advisory** scan was run at the strictest tier
(`DESCRIPTIVE_EVIDENCE_ONLY`) and is reported in a separate field that can never be mistaken
for a pass: all three are clean of prohibited vocabulary at that tier. **They are clean and
still refused**, because a document making substantive claims without declaring what it claims
at has not been through this control, and no wording scan can tell you whether it passed one.

`MX09_FALSIFICATION_RUN.md` is the borderline case worth naming: it quotes MD15 as "capped at
`LIMITED_CAUSAL_EVIDENCE` by the registry". That is a cap on a *proposition*, not a
declaration of the tier the *write-up* claims at, and it is recorded in `tier_source` as such.

### The result-backed pair, and a retracted paper in both

The two persisted kernel results were put through the full nine-gate `assess_release`. Both
refuse on two gates:

```
RESULT:KR-P1-20260815123808-MD11  ASSOCIATION_ONLY
    - UNADMITTED_EVIDENCE_PRESENT:1
    - HUMAN_REVIEW_RECORD_MISSING
RESULT:KR-P1-20260815123808-MX14  ASSOCIATION_ONLY   (same two)
```

- **`UNADMITTED_EVIDENCE_PRESENT:1` is a new finding.** Both results cite
  `EV-53F188574025CB28692A` — *"Treatment trajectories among children and adolescents referred
  to the Norwegian National Center for Gender Incongruence"* — which is lane
  `CORRECTION_RETRACTION` and `admitted = False`. The retractions connector refused it after
  the pilot run had already frozen its `evidence_ids`. Each result's 361-record evidence list
  therefore contains one record the corpus has since refused. Nothing downstream noticed,
  because nothing downstream ever asked; `assess_release` asks, and refuses.
- **The counterevidence gate passed.** `COUNTEREVIDENCE_LANES_NOT_SEARCHED` does **not**
  appear, because the sweep recorded in `docs/COUNTEREVIDENCE_RUN.md` persisted
  `SEARCHED_COMPLETE` rows for `CONTRADICT`, `RIVAL` and `NULL` on both propositions. That
  gate is now satisfied by evidence rather than by nobody checking.
- **`HUMAN_REVIEW_RECORD_MISSING` is unfixable by code.** Zero `HumanReviewRecord`s exist
  anywhere in this project. Every release is blocked on a named accountable person making a
  decision, which is the intended design.

---

## 3. What was built

| Where | What |
|---|---|
| `governance/feasibility.py` | `registry_digest`, `connector_source_ids` (declared vs undeclared, kept apart), `workstream_source_coverage` — a diagnostic overlay that deliberately does **not** feed back into `Reachability` |
| `governance/claim_release.py` | `ClaimSubmission`, `DocumentedClaimAssessment`, `assess_documented_claim` — routes prose claims to the same gate, refusing `CLAIM_TIER_NOT_DECLARED` and `NO_PERSISTED_RESULT_FOR_CLAIM` rather than synthesising either |
| `persistence/sqlite.py` | five tables plus `save_feasibility_census` / `get_feasibility_census` / `latest_feasibility_census_id` / `save_claim_assessment` / `list_claim_assessments` |
| `scripts/run_feasibility_census.py` | live census, drift comparison against the quoted figures, `--apply` to seal and persist |
| `scripts/assess_claim_release.py` | the release run over this project's documents, `--apply` to persist every verdict |
| `tests/unit/test_feasibility_persistence.py` | 12 guards on the wiring |
| `tests/integration/test_governance_field_wiring.py` | 4 standing guards against the live store |

### Why both writes require a sealed run manifest

`save_feasibility_census` and `save_claim_assessment` both call `require_run_manifest` and
refuse without one, matching `save_kernel_result` / `save_synthesis`.

The census was the closer call, because it is a derivation from a registry rather than a
result about the corpus, and a manifest costs something. It requires one anyway: the census is
quoted as a governance fact that gates what the project attempts, and a governance fact whose
code commit and registry version are unrecorded cannot be re-derived when it is later
disputed. That is exactly the state the four quoted numbers were in before today. The census
additionally stores a digest of its two input files, so a future disagreement can be
attributed to an input change instead of argued about.

Claim assessments were never a close call. A release decision without a recorded run is a
governance decision with no provenance.

### Where values are unknown, they are visibly unknown

- `declared_tier` is stored as **SQL NULL** when a document declares none. NULL is not any
  tier value and the schema keeps it distinct; a test asserts no claim can reach `released`
  with a null tier.
- Connector modules that declare no `SOURCE_ID` are `connector_status_unknown`, never
  "no connector".
- `build_run_manifest(preregistration_ref=...)` is passed `NOT_PREREGISTERED` explicitly by
  both scripts. Neither run is preregistered and both say so.

## 4. What remains

1. **Nothing can be released** until a `HumanReviewRecord` exists. That is a founder action,
   not an engineering one.
2. **`TIER_WORDING` catches vocabulary, not inference.** "the arithmetic signature of" passed.
   The list needs constructions, not only verbs.
3. **The three tier-undeclared documents should declare a tier**, or be marked as
   non-claim-bearing. This document declares none either, and is refused by its own check for
   the same reason — it is a wiring report, not a claim about the world, and that distinction
   should be recorded in the front matter of every document rather than inferred.
4. **Connector-to-registry linkage.** 16 of 28 connectors declare no `SOURCE_ID` and four
   declare `UNREGISTERED:` ids. Until that is closed, no mechanical check can tell whether a
   workstream declared open actually has a route built.
