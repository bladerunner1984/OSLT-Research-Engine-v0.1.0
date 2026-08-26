# Result Package 1 — Census instrument sensitivity and validity

**Status:** specification frozen; confirmatory retrieval not started  
**Specification ID:** `OSLT-RP1-CENSUS-INSTRUMENT-SENSITIVITY-V1`  
**Frozen at:** `2026-08-26T11:23:24Z`  
**Specification SHA-256:** `7800ff83f3bad2cf3ca9b7358a5e21faffc12cee9e9d36ebf3a488ef8af1967c`

## Selection decision

This package was selected first on feasibility and identification grounds, not because its
result is expected to favour a model family.

| Candidate | Public/accessible now | Identification for bounded claim | Data readiness | Reproducibility | Scientific value | Total / 25 |
|---|---:|---:|---:|---:|---:|---:|
| Census instrument sensitivity | 5 | 4 | 5 | 5 | 4 | **23** |
| Public-service decomposition | 5 | 3 | 4 | 5 | 3 | 20 |
| Minority-stress meta-analysis | 3 | 4 | 2 | 4 | 5 | 18 |
| Guideline ancestry/diffusion | 4 | 3 | 3 | 4 | 4 | 18 |
| Media diffusion/attention | 4 | 2 | 3 | 4 | 4 | 17 |

The scores are a transparent scheduling aid, not scientific evidence. Census wins because the
bounded outcome is directly observed in a complete public table set, codelist and denominator
semantics can be audited, important alternatives have observable controls, cost is zero, and a
valid measurement result does not depend on any claim about identity origin or individual
causation. The public-service package is nearly as executable but its held MHSDS source has no
gender-service referral measure. The other packages require a new corpus, screening, coding, or
event/ontology freeze before they can produce a confirmatory estimate.

## Freeze semantics

- `preregistration_v1.py` is the live declarative specification.
- `frozen_specification.json` contains its full canonical payload, hash, and freeze time.
- Tests recompute the hash and fail if the live specification drifts.
- The 517 Census cells retrieved on 2026-08-16 predate this freeze and are permanently
  exploratory. They may validate source semantics and fixtures but cannot enter a confirmatory
  claim merely because the same cells are retrieved later.
- Confirmatory retrieval must occur after the freeze and carry canonical URL, exact query,
  retrieval timestamp, source version, access basis, and raw-response hash.

The Git commit containing both specification and receipt is the durable ordering record for this
branch. A later execution run should additionally append the freeze and retrieval events to the
hash-chained research journal.

## Claim boundary

The primary outcome is a **published census response proportion** under frozen category and
denominator definitions. The study may conclude that specified instrument features materially
change—or do not materially change within the equivalence margin—the published statistic.

It cannot estimate latent true prevalence, temporal change, identity origin, or individual effects.
“Impact on consciousness” is not an outcome. No aggregate subgroup association licenses a
psychological or identity-causation claim.

## DONE

The package is complete only when a clean environment runs one documented command that:

1. verifies the unchanged freeze receipt;
2. retrieves only the frozen official source set and writes a complete source/hash manifest;
3. creates the codelist and denominator crosswalk before estimates;
4. recreates primary estimates, materiality decisions, negative control, sensitivities and figures;
5. emits machine-readable results with numerators, denominators, definitions and limitations;
6. passes an independent semantic and numerical audit; and
7. produces an immutable checksummed release regardless of result direction.

No confirmatory retrieval or result analysis is part of this reconciliation branch.

