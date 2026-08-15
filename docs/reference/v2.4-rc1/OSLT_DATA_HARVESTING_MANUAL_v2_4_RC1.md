# OSLT Data Harvesting Manual v2.4 RC1

## Purpose
This manual turns the 13 acquisition workstreams and 65-source register into a controlled acquisition process. "Harvest" means lawful research acquisition under the source's licence, API terms, consent or data-access approval.

## Universal sequence
1. Select one preregistered proposition/estimand.
2. Resolve its required variable IDs and workstreams.
3. Freeze a **minimum necessary field list**.
4. Verify actual source fields/instruments before application/download.
5. Record source access tier and approval/licence/consent route.
6. Acquire using the source-specific runbook.
7. Create immutable ingest/provenance record.
8. Validate schema, duplicates, coverage, missingness and time range.
9. Harmonise definitions/diagnostic eras without deleting source values.
10. Build dependency links and evidence families.
11. Seal analysis dataset/version.
12. Run prespecified SAP and robustness/falsification analyses.
13. Export only permitted/disclosure-checked results from restricted environments.

## Current high-value routes (verified 25 July 2026)
- **NHS England SDEs:** approved research access is moving to secure data environments; raw data should remain in the secure setting.
- **OpenSAFELY:** code-to-data primary-care analysis; non-COVID research is now supported.
- **ONS SRS:** accredited/approved researcher TRE; metadata catalogue available before application.
- **DfE NPD:** use the field-discovery service to specify exact data items before applying for extracts.
- **OpenAlex/Crossref/ClinicalTrials.gov:** programmatic scholarly/registry harvesting suitable for Pilot 1.
- **UK Government Web Archive:** public historical government snapshots.
- **Ofcom:** 2026 child media-use research provides baseline exposure/context data.
- **Google Trends API:** alpha/application access, rolling five-year window; historical web/UI sources are needed for earlier periods.
- **TikTok Research Tools:** qualifying UK/European researchers can apply for public platform research data.

## Public web/API harvesting
Respect published API limits/licences/robots and copyright. Store metadata/identifiers and only the text necessary/permitted for analysis. Prefer canonical IDs (DOI, PMID, NCT, ORCID, ROR, URL+capture timestamp).

## Restricted/TRE harvesting
Do not request a data dump. Prepare field list, code lists, linkage requirements, SAP, public-benefit rationale, approvals and executable code. Run within the TRE/SDE. Export aggregate/model results only after output checking.

## Primary participant harvesting
Use an approved consent protocol. Collect only selected periods/data types. Separate identifiers. Provide a manifest of every donated archive. Never assume access to a participant's account grants rights to third-party data.

## Dataset rejection conditions
Reject or quarantine a dataset when provenance cannot be established; definitions changed without resolvable versions; missingness makes the target estimand non-identifiable; linkage quality is unknown; licence/approval does not permit proposed use; duplicate/dependency cannot be resolved; or the data were collected in a way inconsistent with consent/ethics.

## Workstream instructions
See `harvest_runbooks/W01...W13` for source-by-source operating instructions.
