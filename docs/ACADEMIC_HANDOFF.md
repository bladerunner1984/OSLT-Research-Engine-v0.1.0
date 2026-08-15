# Academic handoff dossier

**Prepared:** 2026-08-15 · **Revised:** 2026-08-16 · **Repository:** `bladerunner1984/OSLT-Research-Engine-v0.1.0`
**Status:** instrument built and running; three descriptive comparator analyses complete;
**no proposition answered**; no mechanism calibrated.

This document exists so that a researcher with institutional affiliation can pick this work
up without reconstructing it. The author, Mark Jennings, is an independent researcher with
no institutional affiliation and no funding. Several of the remaining steps are not hard —
they are simply not available to an unaffiliated person. That is the honest reason this
dossier exists.

It states what is built, what is established, what is blocked, what is defective, and
precisely what an incoming collaborator would need to supply.

---

## What this is

A governed research engine for testing competing explanations of change in gender-related
identity, presentation and referral. It carries 64 pre-registered propositions across five
competing model families, each with a stated falsifying condition, and it is built to be
capable of rejecting the investigator's preferred explanation.

The governance is enforced in code rather than asserted in prose. That is the unusual part
and the part worth inheriting. Concretely: evidence that fails admission is refused rather
than flagged; a retracted paper cannot enter the corpus; a claim whose wording exceeds its
evidence tier is refused release; and confirmatory analysis is mechanically blocked when the
specification freeze post-dates the data retrieval.

### The single most important thing to know about this work

**It repeatedly killed its own positive findings.** That is the strongest available evidence
that the instrument is not a confirmation machine, and it is the reason to take the rest
seriously:

- Three separate MD15 "structural coupling" positives were retired by the engine's own
  checks — one for resting on disconnected dyads, one for resting on twelve entity merges
  made on naming coincidence, one for resting on an outcome date that excluded nothing.
  Against a real dated outcome (Cass Review, 2024-04-10) the test returns `MX09`.
- Comparator 2 (below) has an obvious rival reading that would have weakened it. Rather than
  assert the rival away, a negative-control class was harvested specifically to test it. The
  rival reading died; had it survived, comparator 2 would have been substantially devalued,
  and that is what would have been reported.
- One of the three series commissioned *as* a negative control (school SEMH needs, 91871)
  turned out on inspection not to be one — it is a judgement about a presenting child, so it
  belongs on the subjectively ascertained side. It was reclassified as a third comparator
  rather than quietly counted as a passing control.
- A field that would have **inverted** a headline conclusion was caught and excluded (the
  91344 index-not-trend trap, below).

Nothing in this project has been reported as a finding without something being available
that could have destroyed it.

---

## What an incoming academic actually gets

| | Verified figure |
|---|---|
| Test suite | **756 tests** (`pytest --collect-only -q`), CI green on every commit |
| Source connectors | **26** live connectors plus a shared OCDS resolution module; all open, keyless or free-registration |
| Corpus | **6,428 admitted** evidence records; 6 refused at the admission gate (retracted) |
| Institutional graph | **824 typed entities**, **1,286 typed dated relations** — `FUNDS` (926), `ADVISES` (227), `CONTRACTS_WITH` (103), `ISSUES_GUIDANCE_TO` (30) |
| W02 calibration targets | **218 usable series** (56 from the first Fingertips harvest, 162 from the recovery run), against **zero** at the start of this work |
| Census 2021 gender identity | **517 cells**, 13 of 24 tables, zero missing, zero refusals |
| Propositions | 64 pre-registered; **16 open-testable**, 48 access-gated; **0 answered** |
| Descriptive analyses complete | 3 (referral baseline, second comparator, negative-control class) |

Plus, as running code rather than plans: a governance kernel (admission, authority lattice,
claim-release gate, preregistration freeze, continuity preflight, 16-dimension certainty
vector), a simulation layer pinned to `SIMULATION_ONLY` (Monte Carlo power, minimum
detectable effect, VanderWeele–Ding E-values, coder-drift), a lane-coding classifier with
Cohen's kappa, an institutional ontology with tiered entity resolution, and a feasibility
census that costs every blocked proposition.

**W02 is the headline delivery of the last ~30 commits.** Workstream W02 (NHS referrals,
diagnoses and service pathways) is required by 40 of the 64 propositions and was empty,
because individual-level NHS data sits behind processes measured in months. It is no longer
empty. Fingertips cannot supply individual records, but the ascertainment propositions are
claims about *rates*, and rates are what it provides. See `W02_FINGERTIPS_HARVEST.md` and
`W02_FINGERTIPS_RECOVERY.md`.

---

## The analytic findings, at the tier the engine's own rules allow

All three are **descriptive**. Per `mechanism_simulation.compare_mechanisms`, a mechanism
that reproduces an observed series returns `INCONCLUSIVE`, never `SUPPORTS` —
**compatibility is never support**. No mechanism has been calibrated against a gender-service
series, because that series is not yet obtainable. What follows establishes denominators for
a comparison; it is not the comparison. Full detail and every caveat is in
`REFERRAL_BASELINE.md`.

**1 · Background referral growth is not flat (cancer, England, 2009/10–2024/25).**
Urgent suspected cancer referrals rose ×2.98 per 100,000 (CAGR +7.6%) while diagnostic yield
fell ×0.55 (CAGR −3.9%), monotonically but for the COVID year. That is the arithmetic
signature of a lowered referral threshold, and it is the documented intent of successive NICE
revisions — not in dispute. Its methodological consequence is what matters: **a threefold
rise in any English specialist referral series over this window is, on its own,
unremarkable.** Showing a domain-specific cause requires showing departure from this
baseline, not merely that a series rose.

**2 · The adolescent, female-skewed referral signature is not domain-specific (secondary
mental health, 2017/18–2023/24).** New referrals to secondary mental health services rose
×2.02 in under-18s against ×1.08 in the over-65s, monotonically by age; within under-18s the
female:male ratio moved from 1.077 to a 1.556 peak in 2021/22, easing to 1.321. Rapid,
adolescent-concentrated, female-predominant growth — the conjunction usually treated as
requiring a domain-specific explanation — is present in a service with no relation to gender
identity. This refutes no account of gender-service data. It removes the conjunction's status
as *self-evidently* domain-specific, and it does so symmetrically: social-transmission
accounts internal to the domain face the same question.

**3 · The negative controls held; the artefact reading of (2) is dead.** The obvious rival to
(2) is that adolescent distress genuinely deteriorated, making the "background" a real signal.
Two objectively ascertained paediatric series test the other branch — that the health system,
denominators or recording inflated everything. Diabetes admissions in 10–18s **fell** ×0.71
and epilepsy admissions were flat at ×1.05 over twelve years, against a 10–18 population
denominator that grew ×1.15; both sex ratios moved **towards males** while 93623 moved
towards females. Same hospitals, same coding, same denominators, same pandemic. The inflation
account does not survive.

**This narrows the field to two survivors and does not choose between them:** either
adolescent psychological distress genuinely rose in a way objectively ascertained paediatric
conditions would not register, or the threshold, recognition and recording of that distress
changed — as the cancer baseline shows demonstrably happened in a different subjectively
ascertained domain. **Both remain live. Nothing here separates them.**

**One negative institutional result.** The UK public-procurement network and the parliamentary
advisory network share no organisation, across four registers, surviving identifier-level
resolution against Companies House and the Charity Commission. `MX09` (isolated, non-coupled
processes) is favoured over `MD15` (structural coupling). *Caveat:* that disposition was
reached on a 337-relation graph; the persisted graph now holds 1,286 relations and has **not**
been re-adjudicated. A successor should re-run it before citing it.

**Census 2021 gender identity** supplies the only national enumeration: 262,113 of 48,566,373
aged 16+ (0.54%), a monotonic ~4.6× age gradient, and a female excess confined to 16–24 that
reverses at every older band. Read the defect section below before using any of it.

---

## Four things block progress, and who can unblock them

Ordered by propositions unblocked per unit of effort.

### 1 · The FOI request — drafted, unsent, free, 20 working days

`studies/foi_requests/nhs_gender_service_referrals.md` is written and ready to send. It asks
NHS England for aggregate annual referral volumes to adult Gender Dysphoria Clinics and to
Children and Young People's Gender Services, 2018/19–2025/26. It is pre-defused against s.12
(cost limit), s.40(2) (personal data), s.21 and s.16, with a pre-authorised fallback scope so
the authority can narrow rather than refuse. The premise is verified, not assumed: NHS England
has released this class of figure before (a request marked Successful, 2026-07-06).

**Cost: nil. Requires: a person to press send.** This is the highest value-per-effort action
available anywhere in the project.

**What it unblocks:** the target series. Every comparator above is currently a denominator
without a numerator. With this series in hand the three comparators become an actual
comparison, and `compare_mechanisms` can be run for the first time against real data — which
is the gate on the whole ASCERTAINMENT_SERVICE versus INTRINSIC_RECOGNITION contest.

### 2 · The MHSDS manual download — open data, closed automated path

MHSDS monthly statistics need no login, no application and no key. The
`MHSDS Time_Series_data_Apr_2016_May_2026_Perf v2.zip` is a ten-year monthly referral and
contact series and is the highest-value single artefact for W02. The connector will not fetch
it because the files sit on `files.digital.nhs.uk`, whose robots.txt is a blanket
`Disallow: /`. `guard_route()` makes that refusal executable rather than advisory — links to
declined hosts are stripped from index results, so no later edit can quietly repoint the
connector at the CDN.

**A robots.txt closes the automated path, not the data.** A person clicking a download link on
a public statistics page is not a robot, and this is the ordinary intended use of the
publication. Download to `runtime/mhsds/` and add a local-file reader on the
`ons_population.py` precedent. Details in `SOURCE_ACCESS_NOTES.md`.

**What it unblocks:** monthly-resolution W02 series alongside the annual Fingertips ones, and
a second independent route to referral volumes if the FOI is refused.

### 3 · ONS Secure Research Service accreditation

Draft application at `studies/ons_application/project_accreditation_draft.md`; capability
self-assessment at `sponsor_capability_assessment.md`. Requires an accredited researcher and
an institution behind them.

**What it unblocks:** the 16 `NEEDS_RESTRICTED_ACCESS` propositions **and, more importantly,
the ballot asymmetry described below** — which is the difference between a study that can
adjudicate between explanations and one that cannot.

### 4 · A named methodologist and an ethics review

25 propositions are `NEEDS_PRIMARY_COLLECTION`: recruitment, consent, ethics approval and an
HRA sponsor. There is no route to a sponsor for an unaffiliated researcher — the HRA requires
a managing organisation to accept the role. A costed design exists: one prospective cohort of
~1,900 participants covers all 25 (priced separately they need 46,475).

Separately, and far cheaper: **the frozen Pilot 1 specification has had no methodological
review of any kind**, and neither have the three comparator analyses. That is a few hours of a
qualified person's time and it gates everything downstream of the freeze.

---

## Known defects and limits — read these before anything else

### Census 2021 gender identity lost its accreditation

This is the most consequential defect in any data the project holds, and it is recorded
against the evidence rather than left to be discovered later. Full chronology in
`CENSUS_2021_GENDER_IDENTITY.md`.

- **12 September 2024** — the Office for Statistics Regulation concluded the question "did not
  work as intended" and **removed accreditation**. These are now *official statistics in
  development*, not accredited official statistics.
- **The mechanism is documented and reproduces in this harvest.** Trans identification runs at
  2.24% among people whose main language was not English and who did not speak it well,
  against 0.42% among English speakers (ONS, 26 March 2025). The ethnic-group cross-tab here
  independently shows a 6× spread ordered almost exactly by likely English proficiency, with
  non-response tracking in the same direction.
- **Therefore 262,113 is an upper bound with an unquantified positive bias, not a count.** ONS
  itself declined to say whether the figure is an over- or under-estimate, and states the
  figures "should not be used as precise estimates to support service delivery".
- Sexual orientation, riding the same form with the same voluntariness and the same 16+
  restriction, was **not** downgraded. So this is not a generic "sensitive question on a
  census" problem, which constrains which explanations of the failure are available.
- The table is not worthless — for the ascertainment family the quality failure *is* the data.
  But it must never be cited as a prevalence count.

Three further census traps: it is a **cross-section and cannot show a trend** (the question
was new in 2021, so there is no second measurement by the same instrument); `c_sex` is the
**census sex response**, not birth-registered sex, and differs for roughly two-thirds of trans
respondents; and **"all other gender identities" means two different things** across codelists
— 18,074 in TS070 versus 48,331 in the 7-category tables, a silent 2.7× difference.

### Six confirmed cases of a date field meaning something other than it appears

Not a hypothetical risk. Confirmed, each caught in use:

| Field | Looks like | Actually is |
|---|---|---|
| legislation.gov.uk Atom `<updated>` | enactment date | website record revision — put a 2004 Act in 2024 |
| OpenAIRE `dri:dateOfCollection` | publication date | OpenAIRE's own harvest timestamp, identical on every record |
| OpenAIRE `relevantdate[created]` | publication date | metadata registration — a 2018 article carried 2020 |
| ISRCTN element dates | registration date | study dates; the registration date is an attribute |
| WHO ICTRP `Date_enrollement` | registration date | enrolment; only `Date_registration` anchors a publication window |
| Fingertips period labels | calendar years | Financial, Calendar **and** Academic bases coexist; `YearType` is authoritative |

**Standing rule for a successor: any field that looks like a date probably measures something
else. Check before anchoring a window on it.**

### The 91344 index-not-trend trap

Fingertips indicator 91344, "Urgent suspected cancer referrals (indirectly age-gender
standardised)", carries a value of exactly 100.0 in every one of its 15 periods, with
`count == denominator` throughout. It is **England indexed against itself**, not a time series.
Its first-to-last ratio is therefore 1.00. Read naively alongside the real series it says
"referrals did not change" — which **inverts the finding**. It is excluded by id with the
reason recorded inline, and every stratum in the negative-control run was tested for the same
failure mode before use.

This is the first case in the project where a misreading would have *reversed* a conclusion
rather than merely degrading it.

### Other limits a reviewer should check

- **Two source APIs silently discard search terms.** Contracts Finder and UKRI GtR both
  accepted a query and ignored it. Both now refuse the parameter rather than pretend.
  **Consequence: no Strand B graph built so far is topic-scoped.** Assume any new source does
  the same until proven otherwise — send two genuinely different queries and check the results
  differ.
- **Lane coding is effectively absent in the persisted store.** All 6,428 admitted records
  carry `UNCLASSIFIED`; the 6 refused carry `CORRECTION_RETRACTION`. Classifier output has not
  been persisted back into the store. SUPPORT/CONTRADICT are proposition-relative and cannot
  be assigned automatically in any case.
- **811 records have empty abstracts and this is not recoverable.** They are conference
  front-matter and session headers — container records with no abstract to hold. Two
  enrichment passes recovered 0. Exclude them with a recorded reason; do not build a backfill
  pipeline, and do not treat them as an outstanding gap.
- **OpenAlex enforces a daily *budget*, not a rolling window.** One unthrottled run drew 1,379
  requests and cost roughly a day of access to a P0 source. Throttle from the first request
  against any source whose limit model is unknown.
- **Corpus coverage is thin in places** — MD05 (10 records), MD07 (14), AS02 (15).
- **A failed request is not a zero, and a suppressed cell is not a zero.** A hole read as a
  trough is fabricated data in the very series a mechanism is tested against.

### The ballot is unequal — the most important caveat in the project

Of the 16 open-testable propositions, **12 belong to `ASCERTAINMENT_SERVICE`** and 4 to
`MULTIFACTORIAL_DEVELOPMENTAL_INSTITUTIONAL`. `INTRINSIC_RECOGNITION`,
`MIXTURE_HETEROGENEITY` and `NULL_OR_ALTERNATIVE` have **zero** open-testable propositions
between them.

An open-data-only study therefore cannot be a contest between explanations. It would return
`ASCERTAINMENT_SERVICE` as leader whatever is true, because its rivals cannot be run. The
engine detects this and emits
`COMPARATIVE_SUPPORT_OVER_AN_UNEQUAL_BALLOT_MEASURES_DATA_ACCESS_NOT_EXPLANATION`.

**Any comparative claim published before this is corrected would be an artefact of data
access, not a result.** Correcting it requires item 3 above.

---

## What has NOT been done

Stated flatly, because a sceptical reader should not have to infer it.

- **No mechanism has been calibrated against any target series.** `compare_mechanisms` is
  built and tested and has never been run against real gender-service data, because no such
  series is held.
- **No human coder has verified any lane coding.** Every AI-produced review record in this
  repository is pinned to `A5_MODEL_PROPOSAL` and is mechanically barred from satisfying an
  `A2_HUMAN_GOVERNANCE_DECISION`. The classifier, Cohen's kappa machinery and coder-drift
  simulation exist; a second human coder does not. **The AI work is a starting point requiring
  verification, not a finished result.**
- **No individual-level data of any kind.** Everything held is aggregate and public.
- **48 of 64 propositions cannot be tested at all** — 25 need primary collection, 16 need
  restricted access, 7 need individuals followed through time. Only 16 are open-testable, and
  see the ballot caveat above for why those 16 are not a fair sample.
- **The Pilot 1 result is unexecuted.** The kernel returns `WEAKENS` for MD11 and `SUPPORTS`
  for MX14 at `ASSOCIATION_ONLY`. **Do not cite this.** The corpus has no orientation coding,
  so the stratifying variable the design depends on has never been measured; the kernel is
  reporting the absence of a difference it was never in a position to observe. What *did*
  change is the power envelope — minimum detectable OR at 80% power fell from 1.86 (361
  records) to **1.16** (6,428). The sample is no longer the constraint. The coding is.
- **The 15 August corpus is permanently exploratory**, because it predates the preregistration
  freeze. Enforced by `FREEZE_POSTDATES_DATA_RETRIEVAL`, not by convention.
- **No independent statistical, clinical, ethical or publication peer review.**

### Routes declined on published-policy grounds — do not quietly reopen these

A successor may be tempted to treat these as engineering problems. They are not. Each was
declined because a published access policy forbids the automated route, and reopening any of
them would put the project's conduct in question in a way no finding would be worth.

| Route | Why it is closed |
|---|---|
| **PROSPERO** | `prospero-auth-token` is a base64-encoded client timestamp — a deliberate anti-automation gate with no public enrolment path. Reproducing it circumvents an access control CRD put there on purpose. **Legitimate route:** email CRD at York requesting bulk or documented API access for research use. |
| **WhatDoTheyKnow** | robots.txt disallows the search, feed and response paths; House Rules explicitly forbid scripts and unapproved automation. That is a prior-approval regime, not a rate limit politeness satisfies. **Legitimate route:** the FOI request — free, statutory, and better. |
| **files.digital.nhs.uk** | Blanket `Disallow: /`, unchanged since 2018. **Legitimate route:** manual download by a person (item 2 above). |
| **data.gov.uk CKAN / GrantNav** | Declined on the same published-policy grounds. |
| **WHO ICTRP** | No API exists; the bulk export needs a Microsoft account and an access request, and WHO terms require attribution and bar commercial use — a licensing decision for the researcher, not for an agent to accept on his behalf. |

**Standing lesson:** "find a workaround" reaches the end of its authority at a published
access policy. In every case above a legitimate route exists, and in two cases it is faster
and better than the automated one would have been.

---

## If you have a week / a month / a year

Keyed to what unblocks the most propositions per unit of effort.

### A week

1. **Send the FOI request.** Twenty minutes. Free. It starts a 20-working-day statutory clock
   that runs while you do everything else. Nothing else in this list has a comparable ratio.
2. **Download the MHSDS time-series ZIP** and place it in `runtime/mhsds/`. Half an hour, no
   application, no key, no interpretation of anyone's policy required.
3. **Read the frozen Pilot 1 specification**
   (`studies/pilot_01_academic_knowledge/preregistration_v1.py`) and record a methodological
   opinion. It has had none. A few hours; it gates everything downstream of the freeze.
4. **Re-run the MD15/MX09 coupling test on the current 1,286-relation graph** and record the
   disposition. The published result rests on 337 relations and has not been re-adjudicated.

### A month

5. **Write the MHSDS local-file reader** on the `ons_population.py` precedent (stream and
   aggregate rather than load), applying the standing rules: a suppressed cell is missing and
   never zero; nothing sums across England, region and provider levels; monthly-within-
   financial-year periods must not be coerced to calendar years.
6. **Run `compare_mechanisms` against whatever target series has arrived**, with the three
   comparators as background. Restrict to the overlapping window, and do not align the three
   different year bases — financial, calendar and academic genuinely do not share period
   boundaries, and "2020/21" denotes three different intervals across these analyses.
7. **Add further comparators before running the comparison.** IAPT access (90592, 78 monthly
   points) is already harvested and is the obvious next one; 92622/92623 are now committed as
   negative controls rather than comparators.
8. **Blind dual-code a validation sample** of a few hundred records with a second human coder.
   This does not need the full 6,428, and it is what lifts review records from A5 to A2.
9. **Start the ONS Accredited Researcher application.** The draft is written; it needs an
   institution behind it.

### A year

10. **Prosecute the ONS SRS project.** This is the only thing that corrects the unequal
    ballot, and until it is corrected no comparative claim from this project means what it
    appears to mean.
11. **Take the costed primary-collection design to an ethics committee with a sponsor.** One
    prospective cohort of ~1,900 covers all 25 primary-collection propositions; priced
    separately they need 46,475.
12. **Complete registration-to-publication linkage at study scale** under the frozen
    specification — and only then activate master synthesis, whose gate requires three
    independently tested kernel result families to exist.

---

## What the founder needs from a collaborator, specifically

Not funding. Not endorsement. Four things, none of which an unaffiliated person can obtain:

1. **Sponsorship for data access.** The HRA requires a managing organisation to accept the
   sponsor role, and there is no route for an unaffiliated researcher. This is the single
   hardest gate and it blocks 25 propositions outright.
2. **A named methodologist.** The frozen specification has had no methodological review, and
   neither have the three comparator analyses, which are the project's only substantive
   analytic output.
3. **Ethics review**, for anything involving primary collection.
4. **Human dual-coding.** Every AI review record in the repository is `A5_MODEL_PROPOSAL`, and
   the constitution bars it from becoming `A2_HUMAN_GOVERNANCE_DECISION`. That is deliberate
   and it means what it says: **the AI work is a starting point requiring verification, not a
   finished result.** A second human coder, on a few hundred records, converts a large amount
   of built machinery from inert to usable.

---

## Where to start reading

1. `config/constitution.yaml` — the rules the code enforces
2. `docs/IMPLEMENTATION_STATUS.md` — what is and is not claimed, in detail
3. `docs/REFERRAL_BASELINE.md` — the three comparators, with every caveat
4. `docs/SOURCE_ACCESS_NOTES.md` — what is closed, declined and unblockable
5. `docs/CENSUS_2021_GENDER_IDENTITY.md` — read the caveats before any figure
6. `registries/hypotheses.csv` — the 64 propositions
7. `src/oslt_research/governance/` — the gates
8. `studies/pilot_01_academic_knowledge/preregistration_v1.py` — the frozen specification

The commit history is part of the record. It documents which defects were found, how they
surfaced, and what was decided — including several results the engine retired after they had
already been reported as findings. If you want to assess whether this work is trustworthy,
that history is a better place to look than this document.
