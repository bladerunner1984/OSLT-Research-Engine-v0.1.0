# Project specification v2 — a measurement-validity and decomposition study

**Status:** proposed re-scope, 2026-08-16. Supersedes the five-family contest as the
headline design. Does not discard v1's propositions or machinery; re-purposes both.

---

## 1. Why the current design cannot be completed

Two obstacles, and only one is about rigour.

**The ballot is structurally unequal.** Of 64 pre-registered propositions, 16 are testable
from public data. **Twelve of those 16 belong to one model family** (`ASCERTAINMENT_SERVICE`).
`INTRINSIC_RECOGNITION`, `MIXTURE_HETEROGENEITY` and `NULL_OR_ALTERNATIVE` have **zero
testable propositions between them**. The engine records this itself as
`COMPARATIVE_SUPPORT_OVER_AN_UNEQUAL_BALLOT_MEASURES_DATA_ACCESS_NOT_EXPLANATION`.

No amount of harvesting fixes this. The 48 remaining propositions need NHS patient records,
cohorts followed through time, or new fieldwork. A contest between five explanations where
three cannot be brought to the field is not a contest, and any verdict it produced would
measure what is cheap to observe.

**The engine has no positive channel.** `compare_mechanisms` returns `WEAKENS` when a
mechanism is refuted and `INCONCLUSIVE` when it survives. There is no third outcome, so a
hypothesis that survives a test which *could have killed it* is recorded identically to one
nobody tested. That is refutation without corroboration — half of falsificationism, and the
half that produces no knowledge. It is why ten of sixteen findings came back inconclusive
after a day of real data.

The first problem is fatal to the question. The second is a fixable defect.

---

## 2. The revised question

> **How much of the observed change in UK gender-related service and population statistics
> is attributable to changes in measurement, coverage, composition and denominator — and how
> much remains to be explained?**

This is answerable with data already held. It requires no ethics approval, no individual-level
records, no secure lab, and no institutional affiliation.

It is also the prerequisite everyone in the debate has skipped. Both sides argue about the
cause of a rise whose *size, net of measurement change*, has never been established.
Establishing the size of the thing to be explained is a contribution independent of who is
right about the cause.

### Why this dissolves the ballot problem

Twelve measurement propositions is a **biased sample** if you are adjudicating five
explanations. It is the **appropriate sample** if measurement validity is the subject. The
asymmetry stops being a flaw the moment the project stops claiming to run a fair contest.

---

## 3. Design

A decomposition. For each observed series, partition growth into components that can be
measured, leaving an explicit residual:

```
observed change
  = denominator change          (population growth and structure)
  + coverage change             (who reports into the collection)
  + composition change          (age, sex, provider mix)
  + instrument change           (definitions, question wording, coding revisions)
  + residual                    (what is left to explain)
```

The residual is the deliverable. It is not "the real rise" — it is the part this method
cannot attribute, stated with bounds, and it is what any causal account must actually explain.

### Worked precedent, already computed

| Component | Method | Result |
|---|---|---|
| Coverage | Restrict MHSDS to providers reporting in **all 84 months** (71 of 539) | Providers ×4.32; series ×1.517 unrestricted, ×1.411 fixed-cohort. **17.4% of log growth is coverage**, 82.6% survives |
| Denominator | ONS/NOMIS population against raw counts | Population ×1.0426 vs count ×1.511 — **10.1% of log growth** |
| Composition | Direct age-standardisation | **1.4% of log rate growth** |
| Instrument | Same census category across 7- vs 8-category response lists | **×2.67** for the identical category |
| System baseline | Unrelated referral domain, same system, same period | Cancer referrals ×2.98 with yield ×0.55 — referral growth is system-wide |

Each of those is a real number obtained from public data. Together they are the study.

---

## 4. Scope

### In

1. **Coverage decomposition** — MHSDS fixed-cohort analysis, extended to MHS32 (flow) and to
   age bands, with the CYP-provider question resolved: were later-joining providers
   disproportionately children and young people's services? This is currently unchecked and
   directly determines whether adolescent-specific trends are artefactual.
2. **Denominator decomposition** — all series carrying counts, against ONS mid-year estimates
   and Census 2021.
3. **Composition decomposition** — direct standardisation by age and sex where published.
4. **Instrument analysis** — the Census 2021 gender identity question (accreditation removed
   by OSR 2024-09-12; English-proficiency artefact documented by ONS), MHSDS definitional
   revisions, and coding changes datable against the 121 W09 policy anchors.
5. **System baseline** — referral growth across unrelated clinical domains as the comparator
   for what "a large rise" means in this system, with negative controls (paediatric diabetes
   and epilepsy admissions) that did **not** rise.
6. **The residual**, with bounds.

### Out

- Adjudicating between the five model families. Retained as a documented agenda (§7), not a
  headline claim.
- Any individual-level analysis.
- Any causal claim. Maximum tier is `DESCRIPTIVE_EVIDENCE_ONLY` throughout.

### The one outstanding input worth waiting for

The **FOI request to NHS England** (`studies/foi_requests/nhs_gender_service_referrals.md`,
drafted, unsent, free, 20-working-day statutory deadline). Gender-service referral figures
appear in **no** public dataset — MHSDS was checked and all 121 England-level measures were
scanned; none carries a gender-service measure. Without it the decomposition applies to
comparator and adjacent series only. With it, it applies to the target.

---

## 5. Governance changes

### Keep — every one caught a real error

Provenance admission gate; date-field discipline (**eight** confirmed cases of a date field
meaning something else, one of which would have inverted a conclusion); a hole is never a
zero; coverage warnings carried alongside every series; dependency-family collapse; the
wiring audit's standing check that each governance field on the persisted corpus is not
uniformly at its default.

The coverage warning caught an error in this project's *own* analysis within an hour of being
written. These rules earn their cost.

### Fix

1. **Add severity-weighted corroboration.** Record how likely a test was to fail, and let
   survival at high severity register as something other than silence. `COVERAGE_ONLY` was
   refuted across 25 parameterisations at 36% best distance — that is a hard-won result the
   current vocabulary flattens into `WEAKENS` with no measure of how severe the test was.
2. **Fix the open-testable defect.** `assess_feasibility` marks a proposition testable on
   required-*workstream* availability without checking that any required workstream carries
   the **predictor the proposition's own prediction names**. This alone caused six of the ten
   inconclusive results. AS05's awareness predictor sits in W11, which is not in its required
   set.
3. **Demote the human-review gate from blocking to labelling.** Zero `HumanReviewRecord`s
   exist and none is coming. A gate that can never be satisfied stops being a control and
   becomes an excuse for nothing being finished.

### Retire

The five-family contest as the project's headline claim. Keep the propositions; stop
asserting they can be balanced.

### Keep separate

The institutional-network strand (`MX09`/`MD15`). It is a genuine bounded negative result —
funding, procurement, advisory and guidance networks share no organisation at
`STRONG_IDENTIFIER`, surviving a personnel-edge falsification attempt that flipped one date
on a single artefactual edge. But it answers a different question, and it needs more than
five registers before it can say anything strong. Separate paper.

---

## 6. Deliverables

1. **The decomposition paper** — what fraction of observed change in each series is
   attributable to each component, with the residual and its bounds.
2. **A measurement-validity register** — every field in every source whose meaning differs
   from its name, with the error it would have caused. Eight are documented; this is directly
   useful to anyone else working these datasets and costs nothing further to publish.
3. **The comparator method** — establishing that referral growth is a system-wide English
   phenomenon over this period, so that "referrals rose N-fold" is not by itself evidence of
   a domain-specific cause. Applies well beyond this subject.
4. **The blocked-proposition agenda** (§7).

---

## 7. The 48 blocked propositions become the agenda, not the failure

25 need primary collection, 16 need restricted access, 7 need individuals followed through
time. `governance/design_requirements.py` already prices each: the design needed, the
governance needed, participants required, and the minimum detectable odds ratio.

Nobody has written down what it would actually take to settle this question. That register —
"here is the study that would answer this, here is what it costs, here is the approval it
needs" — is a contribution in its own right, and it is the natural ask of any academic
collaborator who *does* have secure-data access.

---

## 8. What is needed, and from whom

**Founder, free, this week**
- Send the FOI request. It is the only route to the target series.
- Code ~100 records against a codebook. Every lane assignment is currently an unvalidated
  automated guess; zero human codes exist, so inter-rater reliability cannot be computed at
  all. One afternoon converts that from unmeasurable to measured.

**Collaborator with an institution**
- ONS Secure Research Service sponsorship
- Ethics approval for anything individual-level
- A named methodologist — required by several designs and currently absent

**Neither is needed for §4's in-scope work.** The decomposition can be completed without
either, which is the point of the re-scope.

---

## 9. What the work already demonstrates about its own reliability

Stated plainly because a reviewer of a contested subject will look for it.

Three earlier positive findings on institutional coupling were killed by the engine's own
checks. The headline institutional result was overturned by a test built specifically to
break it, then shown to rest on a single artefactual edge. A commissioned negative control
was reclassified when it turned out not to qualify as one. An analysis presented as
significant was withdrawn when new data undermined it, then partially reinstated when the
fixed-cohort computation came in at 82.6%. The claim-release gate caught overclaiming in this
project's own prose and the text was changed rather than the gate.

That record is the strongest evidence available that the conclusions here are not motivated,
and it matters more than any single finding.
