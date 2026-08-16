# MX09 falsification run: personnel edges added to the graph

This run existed to make the MX09 disposition in `docs/COUPLING_READJUDICATION.md` FAIL.
§7 of that document names personnel overlap as the first bound on its own absence claim:
"Company filings, board memberships, personnel overlap … are absent. Coupling running
through any of those channels is invisible here." This run loads that channel and
re-adjudicates.

**Headline: the disposition is OVERTURNED at one of the twenty-eight dates, and the
overturn is fragile.** `assess_coupling` returns `MD15_COUPLING_SUPPORTED` at
2024-01-01, 2025-01-01 and 2026-01-01, where it previously returned
`MX09_ISOLATED_PROCESSES_BETTER`. Only the 2024-01-01 result is usable: at 2025 and 2026
the engine's own `TEMPORAL_TEST_NOT_DISCRIMINATING` guard fires. And the 2024 result
rests on a **single relation**; deleting that one edge returns the verdict to MX09.

Nothing was lowered to obtain this. Both runs are at `STRONG_IDENTIFIER`, against the
same live legislation.gov.uk dates, fetched once and shared by both runs.

---

## 1. What changed in the ontology (Part 1, the gated decision)

`src/oslt_research/ontology/entities.py`:

- `STRONG_IDENTIFIER_NAMESPACES` gains `ch_officer_id` and `ch_psc_id`. Both are
  register-issued identifiers, not names. This **widens** what can count as a bridge and
  therefore makes MX09 easier to overturn.
- `RelationType.HOLDS_OFFICE_AT` and `RelationType.CONTROLS` added.
- `EntityRole.NATURAL_PERSON` added; persons no longer fall back to `OTHER`.

`src/oslt_research/connectors/companies_house_officers.py` now emits the real relation
types, drops the `relation_type_is_a_substitute` note, keeps `tie_semantics`, and
`missing_ontology_members()` returns `()`.

**The name-merge prohibition is intact and tested.** Three tests were added:

| Test | Guarantee |
|---|---|
| `test_identical_names_with_different_officer_ids_never_merge_at_strong_identifier` | two person records named `JOHN ANDREW SMITH` with different officer ids stay two entities |
| `test_same_officer_id_collapses_even_when_names_differ` | one officer id collapses to one entity across name spellings |
| `test_officer_id_and_psc_id_are_not_interchangeable` | the same raw id string in the two namespaces does not fuse a director with a PSC |

The live data confirms the first test is not hypothetical: `AGILENT TECHNOLOGIES LDA UK
LIMITED` carries **two distinct officer ids both named "WRIGHT, James Philip"**
(`CHO-wpCVHYrvB4dYesSfXH2dicNzXTg`, `CHO-VxBzDDnZ_YY05UUaDcdpc5nOUOI`). At this tier they
remain two people. A name-based tier would have fused them.

**Full suite: 803 passed, exit code 0** (`.venv/Scripts/python.exe -m pytest -q`, exit
code read directly, not through a pipe). Three existing tests asserted the old enum
contents and the substitute note and were updated; none of them guarded the name-merge
prohibition.

### One substantive change forced by live data

Companies House returns records whose end date precedes their start date — a PSC can
cease before the company files the notification, since `notified_on` is a filing date.
Fourteen thousand-odd edges in, this crashed the model validator. The edge is now emitted
**undated**, with both source dates preserved under `interval_inverted_at_source`, so
`assess_relation_admission` refuses it with `RELATION_UNDATED`. That is the treatment an
appointment with no `appointed_on` already received: visible and counted, never silently
dropped, and never given a start date the register does not assert. 505 of 15,048
personnel relations were excluded this way.

---

## 2. Coverage achieved — and what was NOT covered

**Harvested: 94 of 94.** Every entity in `runtime/oslt.db` carrying a `companies_house`
identifier, officers and PSC, then the reverse index `/officers/{id}/appointments` for
**1,798 of 1,798** distinct officer ids found. 1,986 requests, 20.7 minutes wall clock,
0.55 s minimum interval applied from the first request, zero throttling incidents.
No budget truncation: `companies_not_harvested_budget` and
`officer_ids_not_queried_budget` are both empty.

This is a **census of the part of the graph Companies House can speak about at all**, not
a sample of it. It is emphatically **not** a census of the graph.

**Not covered — this must travel with any result below:**

1. **730 of 824 graph entities carry no Companies House number** (charity number,
   360Giving org id, OCDS party id, or nothing) and cannot be looked up in this register.
   Any personnel tie running through them is invisible.
2. **26 PSC endpoints returned HTTP 502.** Unknown, not absence. Those companies have no
   PSC data in this run and that is a gap, not a finding.
3. **29 officer lists returned `EMPTY_UNCONFIRMED`.** An unknown company number also
   returns 200 with an empty list, so this is not "these companies have no officers".
4. **`pagination_honoured` is `false`.** At least one paginated list returned an
   identical second page for a different `start_index`, so the connector stopped rather
   than multiply duplicates. Officer lists longer than one page may therefore be
   truncated. This biases **against** finding bridges: it can hide ties, not invent them.
   It does undermine any absence claim made below.
5. **`ADVISES` (227 edges) and `ISSUES_GUIDANCE_TO` (30 edges) remain untouched by
   personnel data.** Verified directly: at every date, no connected component contains
   both an `ADVISES` or `ISSUES_GUIDANCE_TO` edge and a personnel edge. The advisory and
   guidance arms of the graph were never reached, because their members do not carry
   Companies House numbers. The bridge this run was designed to look for — funding
   network to advisory network — was **not testable**, and its absence here is a
   measurement limit.

Machine-readable output: `data/personnel_edges.json`.

Fragment totals: 8,732 entities and 14,762 relations added; 14,991 officer records seen
and **14,991 joined on a Companies House identifier, 0 unjoinable**; 75 individual PSC,
47 corporate PSC, 8 corporate PSC unjoinable (no registration number — not matched by
name). Graph after: 9,556 entities, 16,048 relations, 15,543 admitted.

Entity resolution merged **95 clusters, all `STRONG_IDENTIFIER`, zero `NAME_ONLY`** (5
before). No verdict below depends on a naming coincidence.

---

## 3. Verdict per date, before and after

28 dates, live from legislation.gov.uk (`LegislationConnector.outcome_dates()`, queries
"Gender Recognition", "Equality Act", "Health and Care Act"). The earlier re-adjudication
recorded 29; the feed returned 28 today. The before-column reproduces the published
disposition on the dates common to both.

| Date | Before | After |
|---|---|---|
| 1990, 1997, 2001–2008 (10 dates) | `INSUFFICIENT_ADMITTED_RELATIONS` | `INSUFFICIENT_INDEPENDENT_SOURCES` |
| 2009, 2010 | `INSUFFICIENT_ADMITTED_RELATIONS` | `MX09_ISOLATED_PROCESSES_BETTER` |
| 2011–2017 (7 dates) | `INSUFFICIENT_INDEPENDENT_SOURCES` | `MX09_ISOLATED_PROCESSES_BETTER` |
| 2018–2023 (6 dates) | `MX09_ISOLATED_PROCESSES_BETTER` | `MX09_ISOLATED_PROCESSES_BETTER` |
| **2024-01-01** | `MX09_ISOLATED_PROCESSES_BETTER` | **`MD15_COUPLING_SUPPORTED`** |
| **2025-01-01** | `MX09_ISOLATED_PROCESSES_BETTER` | **`MD15_COUPLING_SUPPORTED`** (guard fires) |
| **2026-01-01** | `MX09_ISOLATED_PROCESSES_BETTER` | **`MD15_COUPLING_SUPPORTED`** (guard fires) |

`TEMPORAL_TEST_NOT_DISCRIMINATING` fires at 2025 and 2026 (14,807 of 15,543 admitted
relations precede 2026-01-01 = 95.3%, above the 90% threshold) and **does not fire at
2024**. By the engine's own rule the 2025 and 2026 verdicts are statements about the
corpus, not about ties preceding a change. **2024-01-01 is the only date at which MD15 is
returned on a discriminating test.**

---

## 4. Which entities, via which person

At 2024-01-01: 13,362 temporally prior relations, 89 components, **24 components mixing
relation types** (before: 0 at every date), **1 qualifying**.

### The qualifying component

| | |
|---|---|
| Size | 6,402 entities |
| Domains (non-UNKNOWN) | `COMMERCIAL`, `POLICY` |
| Relation types | `CONTRACTS_WITH`, `CONTROLS`, `HOLDS_OFFICE_AT` |
| `assess_coupling` conditions | size > 2 ✔ domains > 1 ✔ relation types > 1 ✔ — **fully met** |

It meets the engine's full conditions. It is not merely suggestive. But its structure has
to be stated exactly, because it is not what MD15 describes:

- **Exactly one entity in the component carries a non-UNKNOWN, non-COMMERCIAL domain:**
  `BATH SPA UNIVERSITY` (`CF-GB-SRS-supplierregistration.cabinetoffice.gov.uk/78Bz97mq`,
  typed `POLICY` — a Contracts Finder buyer-role artefact, not a claim that a university
  is a policy body).
- **Exactly one entity sits on both a contract edge and a personnel edge:**
  `AGILENT TECHNOLOGIES LDA UK LIMITED` (`CF-08815891`, `COMMERCIAL`).
- The two are joined by **one relation**: `BATH SPA UNIVERSITY --CONTRACTS_WITH-->
  AGILENT TECHNOLOGIES LDA UK LIMITED`, valid from **2023-12-21 — eleven days before the
  2024-01-01 outcome date**.
- Agilent's personnel edges are ordinary corporate ones: `HOLDS_OFFICE_AT` for WRIGHT
  (two distinct officer ids), BROWNING, SINGH, DAVIES, GOURLAY, JOHNSON, REES, WADDELL,
  and `ABOGADO NOMINEES LIMITED` (a nominee corporate officer); `CONTROLS` from
  `Agilent Technologies Inc.` and `Agilent Technologies Luxco S.A.R.L.`
- The remaining 6,400 members are the general Companies House directorship network,
  reached through officers' other appointments.

**Robustness check.** Removing the single `BATH SPA UNIVERSITY --CONTRACTS_WITH-->
AGILENT` edge and re-assessing 2024-01-01 with everything else unchanged returns
`MX09_ISOLATED_PROCESSES_BETTER`. The entire overturn rests on that one edge and that one
articulation node.

### The two shared officers between graph organisations

Independently of the qualifying component, the reverse index found exactly **2 persons
appointed at more than one organisation already in the graph** (out of 1,057 sharing
officers once companies outside the graph are counted):

1. **`SWIFT INCORPORATIONS LIMITED`** (`CHO-8d_bnTiwfxh8JIr3YfuwkmkWkCg`, 38 appointments
   in total) at `SAVILLS (UK) LIMITED`, `Causeway Technologies Limited`, and
   `CSA (Services) Ltd`. This is a **company-formation agent acting as nominee first
   subscriber**, not a natural person and not evidence of anything. Reporting it as a
   board overlap would be a fabrication.
2. **`CASSIDY, Stacey Anne`** (`CHO-jlS_27S2FvJbKQHugMZidCDXZMs`, 2 appointments) at
   `TLT LLP` (`OC308658`) and `Addleshaw Goddard LLP` (`OC318149`). A real person at two
   law firms — a real tie, reported as such.

**Neither contributes to the qualifying component.** All five organisations are
`COMMERCIAL`, so these overlaps span one domain and cannot satisfy the domain condition.
They are reported because they are real, not because they carry the verdict.

### The funding-network tie that does NOT qualify

A 411-entity component at 2024-01-01 mixes `FUNDS`, `CONTROLS` and `HOLDS_OFFICE_AT` —
a genuine join between the 360Giving funding network and the personnel network, through
Lincolnshire and Grimsby grantees that carry Companies House numbers
(`Feeding Gainsborough`, `Hammond House, Grimsby`, `Cudox Wellbeing CIC`,
`Disability Network CIC`, `Blue Light Brigade, Grimsby`, `Sage Gardener, Lincoln`,
`The Islamic Association of Lincoln`, and others). **It fails the domain condition**:
every member is `UNKNOWN` or `PHILANTHROPIC`, so only one non-UNKNOWN domain is spanned.
It is suggestive, and it does not qualify. The engine's conditions decide.

---

## 5. Disposition

**OVERTURNED at 2024-01-01, on the engine's own conditions, without lowering any tier.**

The re-adjudication's §6 stated what would have had to be true for it to flip: "at least
one connected component of more than two entities, spanning more than one non-UNKNOWN
domain, joined by more than one relation type — i.e. some entity appearing as both, say,
a funding counterparty and a contract or advisory counterparty under a shared strong
identifier. Not one such entity exists in this graph at this tier." One now does:
`AGILENT TECHNOLOGIES LDA UK LIMITED`, a contract counterparty and a personnel
counterparty under a shared Companies House number.

It should be read as an overturn of a **narrow, technical claim** — "no component in this
graph mixes relation types" — which was true and is now false, at three dates and on one
discriminating date. It is not evidence of a coordinated cross-system network:

- The verdict is carried by **one procurement contract dated 11 days before the outcome**
  and by **one articulation node**. Removing either restores MX09.
- The single `POLICY` member is a Contracts Finder buyer-role label on a university.
- The 6,400-entity bulk is the ambient UK directorship network, dragged in by officers'
  unrelated appointments. Personnel data glues large parts of the corporate register
  together by construction; that is a property of directorships, not of this subject
  matter.
- MD15 remains capped at `LIMITED_CAUSAL_EVIDENCE` by the registry, and the assessment
  itself records that MX09 is not excluded.

The honest summary: **MX09's absence claim did not survive contact with the channel its
own §7 named as missing — but what replaced it is one contract meeting one boardroom, not
a coupled system.**

---

## 6. What remains unexamined

- **The advisory and guidance networks.** `ADVISES` and `ISSUES_GUIDANCE_TO` share no
  component with any personnel edge at any date. Their members carry no Companies House
  number, so the funding-to-advisory bridge — the tie that would have been substantively
  decisive — could not be tested at all.
- **730 of 824 graph entities**, unreachable in this register.
- **26 companies with no PSC data** (HTTP 502) and **29 `EMPTY_UNCONFIRMED` officer
  lists**. Unknown, not absent.
- **Officer lists beyond the first page** where pagination was not honoured.
- **Charity trustee registers**, which would reach the 296 charity-numbered entities and
  is the obvious next attack on the same claim.
- **505 personnel relations excluded as undated**, including every inverted-interval
  record. A tie among them could not be placed in time and so could not be tested.
- Whether the Bath Spa / Agilent contract is one of many such contract-to-boardroom
  adjacencies or genuinely isolated: only 94 organisations were reachable, so the
  denominator for that question is unknown.

Reproduce with `scripts/harvest_personnel_edges.py` (writes `data/personnel_edges.json`)
and the before/after re-adjudication over `scripts/readjudicate_coupling.py`'s own
`component_detail` and `live_outcome_dates`.
