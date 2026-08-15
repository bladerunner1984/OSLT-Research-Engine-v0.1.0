# Academic handoff dossier

**Prepared:** 2026-08-15 · **Repository:** `bladerunner1984/OSLT-Research-Engine-v0.1.0`
**Status:** instrument complete and tested; no proposition answered.

This document exists so a researcher with institutional affiliation can pick this up
without reconstructing it. It states what is built, what is established, what is blocked,
and precisely what an incoming collaborator would need to supply.

---

## What this is

A governed research engine for testing competing explanations of change in gender-related
identity, presentation and referral. It carries 64 pre-registered propositions across five
competing model families, each with a stated falsifying condition, and it is built to be
capable of rejecting the investigator's preferred explanation.

The governance is enforced in code rather than asserted in prose. That is the unusual part
and the part worth inheriting.

| | |
|---|---|
| Tests | 442, CI green on every commit |
| Coverage | 92% |
| Corpus | 6,428 admitted records, all 64 propositions covered |
| Connectors | 13, all open or keyless except two free registry keys |
| Propositions answered | **0 of 64** |

---

## What is established

**One negative result.** The UK public-procurement network and the parliamentary advisory
network share no organisation. Tested across four registers with 337 typed, dated
relations, and it survives identifier-level entity resolution against Companies House and
the Charity Commission — the strictest join the system can make. `MX09` (isolated,
non-coupled processes) is favoured over `MD15` (structural coupling) on this evidence.

**Three results were retired by the engine's own checks**, which is the strongest evidence
that the instrument works:

1. Coupling declared from disconnected dyads — connectivity was not required
2. Coupling resting on 12 merges made on naming coincidence — reversed under any
   corroboration requirement
3. Coupling decided by an outcome date that excluded nothing — against a real dated
   outcome (Cass Review, 2024-04-10) it returns `MX09`

**Six retracted papers were found admitted as evidence**, including two that circulate
widely in this literature. A retraction notice is a separate later document, so no amount
of re-reading the originals surfaces it; only a DOI join against Crossref does. They are
now refused at the admission gate.

---

## What is NOT established, and why

### The Pilot 1 result is well-powered and unexecuted

The kernel returns `WEAKENS` for MD11 and `SUPPORTS` for MX14 at `ASSOCIATION_ONLY`.
**Do not cite this.** The corpus has no orientation coding, so the stratifying variable the
design depends on has never been measured. The kernel is reporting the absence of a
difference it was never in a position to observe.

What did change is the power envelope:

| Corpus | Minimum detectable OR at 80% power |
|---|---|
| 361 records (first run) | 1.86 |
| 6,428 records (current) | **1.16** |

So the sample is no longer the constraint. **The coding is.** That is a tractable,
well-defined piece of work rather than an access problem.

### 48 of 64 propositions cannot be tested at all

| Reachability | Count | What it needs |
|---|---|---|
| `OPEN_TESTABLE` | 16 | nothing — testable now |
| `NEEDS_PRIMARY_COLLECTION` | 25 | recruitment, consent, ethics, sponsor |
| `NEEDS_RESTRICTED_ACCESS` | 16 | licensed, administrative or TRE data |
| `NEEDS_INDIVIDUAL_LEVEL` | 7 | individual records followed over time |

### The ballot is unequal, and this is the most important caveat

Of the 16 openly testable propositions, **12 belong to `ASCERTAINMENT_SERVICE`**.
`INTRINSIC_RECOGNITION`, `MIXTURE_HETEROGENEITY` and `NULL_OR_ALTERNATIVE` have **zero**
openly testable propositions between them.

An open-data-only study therefore cannot be a contest between explanations. It would
return `ASCERTAINMENT_SERVICE` as leader whatever is true, because its rivals cannot be
run. The engine detects this and emits
`COMPARATIVE_SUPPORT_OVER_AN_UNEQUAL_BALLOT_MEASURES_DATA_ACCESS_NOT_EXPLANATION`.

**Any comparative claim published before this is corrected would be an artefact of data
access.** Restoring the balance requires ONS or UK Data Service accreditation.

---

## What an incoming collaborator would supply

Ordered by how much each unblocks.

**1. A sponsor organisation** — unblocks 25 propositions. The single hardest gate. The HRA
requires a managing organisation to accept the sponsor role, and there is no route for an
unaffiliated researcher. A costed design exists: one prospective cohort of ~1,900
participants covers all 25 (priced separately they need 46,475).

**2. ONS Accredited Researcher status and an SRS project** — unblocks ~16 and, more
importantly, corrects the ballot asymmetry above. A draft project application is at
`studies/ons_application/project_accreditation_draft.md`.

**3. A second human coder** — unblocks the Pilot 1 analysis. Blind dual coding needs
someone who is not the author. The classifier, Cohen's kappa machinery and coder-drift
simulation are built; a validation sample of a few hundred records is enough, not the full
6,428.

**4. Methodological review** — the frozen specification has had none.

---

## What is already done and need not be repeated

- **Pre-registered, frozen specification** — hash-chained, with a gate that mechanically
  refuses confirmatory analysis if the freeze post-dates data retrieval. The 15 August
  corpus is permanently exploratory as a result, and that is enforced rather than promised.
- **Corpus** — 6,428 admitted records, retraction-screened, all 64 propositions covered.
  Thinnest coverage is MD05 (10 records), MD07 (14), AS02 (15).
- **Dependency-family resolution** — clusters on shared trial registration, dataset
  accession, preregistered cohort name and author-network overlap, not DOI equality.
- **Feasibility census and design costings** for every blocked proposition.
- **Claim release gate** implementing the nine-point standard, including tier-bound wording
  checks and a typed human-review record that a model review cannot satisfy.
- **Institutional ontology layer** with tiered entity resolution and identifier-level joins.

---

## Known limitations a reviewer should check first

- **Lane coverage is 14.8%.** Automated coding cannot assign SUPPORT or CONTRADICT because
  those are proposition-relative. Most of the corpus is `UNCLASSIFIED`.
- **Two source APIs silently discard search terms.** Contracts Finder and UKRI GtR both
  accepted a query and ignored it. Both now refuse the parameter. **Assume any new source
  does the same until proven otherwise: send two different queries and check the results
  differ.**
- **No Strand B graph is topic-scoped**, for that reason.
- **753 records have empty abstracts** and have not been enriched.
- **The observed-series input for calibrated mechanism simulation was never found.** The
  registry's own candidate (DS047, clinic waiting statistics) is documented as having
  inconsistent definitions and an incomplete public series.

---

## Where to start reading

1. `config/constitution.yaml` — the rules the code enforces
2. `docs/IMPLEMENTATION_STATUS.md` — what is and is not claimed
3. `registries/hypotheses.csv` — the 64 propositions
4. `src/oslt_research/governance/` — the gates
5. `studies/pilot_01_academic_knowledge/preregistration_v1.py` — the frozen specification

The commit history is part of the record. It documents which defects were found, how they
surfaced, and what was decided — including several results the engine retired after they
had already been reported as findings.
