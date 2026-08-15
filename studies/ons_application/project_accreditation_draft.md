# ONS Secure Research Service — project accreditation, working draft

**Status:** draft for founder review. Not submitted. Not reviewed by a methodologist.
**Prepared:** 2026-08-15
**Basis:** the frozen Pilot 1 specification (`studies/pilot_01_academic_knowledge/preregistration_v1.py`),
the feasibility census, and the design-requirement costings — all in this repository.

---

## Before anything else: read this honestly

Three things will decide this application, and only one of them is writing.

1. **Safe Researcher Training is mandatory.** You must attend and pass. Nothing below
   matters until that is done.
2. **You are an independent researcher on a contested topic.** The panel assesses public
   good, ethics and feasibility, and this subject will get closer scrutiny than a study of
   commuting patterns. That is not unfair; it is the system working. The application must
   be visibly stronger than average, not merely adequate.
3. **The strongest asset you have is the design, not the hypothesis.** An application that
   reads as wanting to establish a conclusion will fail, and should. An application whose
   central feature is that it can *reject the investigator's preferred explanation* is
   unusual and genuinely persuasive. That is what the OSLT constitution already encodes,
   and it should be the spine of the submission.

---

## 1. Research aims

To determine which combination of ascertainment, service-capacity, developmental,
institutional and policy mechanisms best explains observed change in gender-related
referral and service-contact patterns in England, and to establish which candidate
explanations the available evidence **cannot** support.

The design is explicitly comparative across five pre-registered competing model families,
each with pre-specified falsifying conditions. No family is privileged. The null family
(NULL_OR_ALTERNATIVE) is carried as a competing model rather than as a residual.

### Primary research question

After adjustment for design, measurement, coding change, service capacity, geography and
period, how much of the observed change in referral and service-contact rates is
attributable to ascertainment and service mechanisms rather than to change in underlying
presentation?

### Why this is not already answered

Published aggregate statistics establish *that* referral counts changed. They cannot
separate change in presentation from change in ascertainment, because that separation
requires individual-level records with consistent coding across the period. This is
precisely the gap the SRS exists to fill.

---

## 2. Public good

Under the Digital Economy Act the test is public benefit, not investigator interest. The
benefit here is specific and, importantly, does not depend on which way the result falls:

- **Service planning.** If capacity and threshold change account for a substantial share of
  observed variation, commissioning models built on presentation-growth assumptions are
  misspecified. If they do not, that is equally decision-relevant.
- **Correcting the evidence base.** This is an area where policy has moved faster than
  evidence and where contested claims circulate with weak empirical support in both
  directions. Research explicitly designed to *eliminate* unsupported explanations
  contributes more than research designed to confirm one.
- **Method transferable beyond the topic.** The governed pipeline — provenance admission,
  dependency-family collapse, claim-tier ceilings, mandatory counterevidence lanes — is
  reusable for any contested multicausal question. It is open and documented.

### What is explicitly NOT claimed as public good

No clinical recommendation. No individual-level inference. No conclusion about any
person's identity, treatment or outcome. The system is constitutionally barred from all
three, and the code enforces the bars rather than merely stating them.

---

## 3. Datasets requested

To be finalised against the SRS catalogue. Indicative, all de-identified:

| Data | Purpose |
|---|---|
| Hospital Episode Statistics (HES) | service contact and coding over time |
| Mental Health Services Data Set (MHSDS) | referral and pathway records |
| ONS Census 2021 gender identity datasets | denominator and standardisation |
| ONS population estimates | rate construction |
| GP Patient Survey | ascertainment and disclosure comparison |

Linkage is at de-identified record level within the secure environment only. No raw
person-level data leaves it, and the repository is architecturally incapable of storing
it: `config/data_boundaries.yaml` marks TRE microdata as prohibited, and the evidence
model raises on any attempt to admit a TRE-class record carrying a person-level payload.

---

## 4. Methodology

1. **Frozen specification before outcome analysis.** Objective, estimand, scope, search
   strategy, inclusion rules and dependency-collapse lexicon are locked and hash-chained
   before any confirmatory analysis. The gate is mechanical: analysis is refused if the
   freeze post-dates data retrieval.
2. **Dependency collapse before triangulation.** Records sharing a cohort, dataset, service
   or research family are collapsed, so one sample cannot present as many independent
   sources.
3. **Comparative estimation across all five model families**, with each family's
   pre-specified falsifier evaluated.
4. **Certainty vector and claim ceiling.** Sixteen dimensions; the weakest governs. Strong
   performance elsewhere cannot average away a fatal weakness in identification,
   temporality or provenance.
5. **Power reported alongside every estimate**, so a null is never reported as evidence of
   absence.
6. **Sensitivity analysis** (E-values) for any non-null estimate.

## 5. Statistical disclosure control

All outputs disclosure-checked before release. Frequency tables suppressed below SRS
thresholds. No small-cell counts, no residual disclosure through differencing across
tables, no unrounded rates. Only aggregate model output and disclosure-checked tables
requested for export. Output checking follows SRS rules without exception.

## 6. Outputs

Peer-reviewed publication; an open methods paper; and the analysis code, which is already
public. Every released claim carries its evidence identifiers, dependency families,
counterevidence search status, certainty vector, limiting dimension and permitted wording.

## 7. Team and roles

Sole researcher. **This is a weakness and should be addressed rather than hidden.** The
panel will reasonably ask who checks the work. Two mitigations worth putting in writing:

- The pipeline enforces its own gates independently of the analyst, and refuses release
  when they are unmet. This is demonstrable, not asserted — the code is public and tested.
- A named independent methodologist for the blind dual-coding and review steps. **You do
  not have one yet, and the application is materially weaker without it.** Securing one
  before submission is probably worth more than any wording change in this document.

---

## Open items before submission

- [ ] Safe Researcher Training completed and passed
- [ ] Researcher accreditation route confirmed (degree, or three years' quantitative experience)
- [ ] Independent methodologist identified
- [ ] Dataset list confirmed against the current SRS catalogue
- [ ] Ethics review expectations checked with the Centre for Applied Data Ethics
- [ ] Frozen specification updated to match the final dataset list
