# Harvested data artefacts

Versioned outputs of live harvests, kept here rather than in `runtime/` (which is
gitignored) because they are research artefacts the academic handoff depends on and
because a result that cannot be re-fetched identically must be preserved as fetched.

| File | Source | Script | Caveat |
|---|---|---|---|
| `census_2021_gender_identity.json` | ONS Census 2021 via NOMIS | `scripts/harvest_census_gender_identity.py` | **Accreditation removed by OSR, 12 Sep 2024.** Now "official statistics in development". Read `docs/CENSUS_2021_GENDER_IDENTITY.md` before using any figure. |
| `fingertips_w02.json` | OHID Fingertips | `scripts/harvest_fingertips_w02.py` | Proxy for service contact, not gender-service referrals. Read `docs/W02_FINGERTIPS_HARVEST.md`. |

Each harvest is re-runnable from its script. Re-running against a live source may return
different figures if the publisher revises them; that is a reason to keep the fetched copy,
not a reason to distrust it.
