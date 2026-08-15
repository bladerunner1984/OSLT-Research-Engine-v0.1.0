# OSLT Data Access and Harvest Sequence v2.4 RC1

## Track A — begin immediately: public/open evidence
These sources can be used to validate OSLT ingestion, provenance, dependency and historical concept handling before restricted-data approvals arrive.

### Academic/meta-research
- DS033 OpenAlex — works/authors/institutions/sources/topics/funders/awards.
- DS034 Crossref — DOI metadata, references, funding, updates, licences, retraction metadata.
- DS035 Europe PMC / DS036 PubMed — biomedical literature and identifiers.
- DS037 ClinicalTrials.gov; DS038 ISRCTN; DS039 WHO ICTRP; DS040 PROSPERO; DS041 OSF — registration/preregistration layer.
- DS042 UKRI Gateway to Research — funding layer.
- DS043 Crossref/Retraction Watch — correction/retraction layer.
- DS059 ORCID/ROR — identity and institutional disambiguation.

**Instruction:** backfill historical corpus first, preserve canonical identifiers and raw API/query manifests, cluster duplicate works and shared study families before any orientation/bias analysis.

### Policy/history
- DS029 UK Government Web Archive.
- DS030 GOV.UK publications/consultations.
- DS031 Hansard.
- DS032 legislation.gov.uk.
- DS045 NICE.
- DS046 NHS England gender-service publications.
- DS054/DS055 DfE guidance.
- DS058 professional-body guidance where public.

**Instruction:** capture publication date, effective date, supersession date, jurisdiction, document version and archived URL. Do not overwrite older versions with current guidance.

### Population/media aggregates
- DS014 ONS published census data.
- DS015 GP Patient Survey.
- DS022 Ofcom child media-use research.
- DS028 GDELT where suitable.

## Track B — applications to start concurrently

### OpenSAFELY / NHS
Prepare a minimal field list and code lists derived from Pilot 2/3 estimands. The study should be designed as code-to-data. Do not request raw patient extracts merely to populate OSLT. OpenSAFELY announced non-COVID research access in February 2026, but its initial application window closed on 30 April 2026; therefore verify the current intake route/window before treating an application as immediately available.

### ONS SRS
Obtain researcher accreditation/approval route and search the SRS metadata catalogue before writing the project application. Map each requested variable to a proposition/estimand and public-benefit justification.

### DfE NPD
Use the NPD field-discovery service to create the exact field list before application. Preserve academic year, collection source and sensitivity/identifiability metadata.

### Cohorts/linked data
MCS, Understanding Society, ALSPAC, Born in Bradford, CPRD, SAIL/eDRIS/HBS and similar sources require provider-specific eligibility, governance and linkage planning. Apply only after checking exact instrument/field availability.

## Track C — research-platform applications
- Google Trends API alpha: apply if current rolling-window analysis is useful; archive older public trend evidence separately because the API window is limited.
- TikTok Research Tools: apply through eligible academic/public-interest institution; request only public platform data necessary for the protocol.
- Licensed bibliometric/news archives: acquire only if Pilot 1/11 demonstrates incremental information beyond open sources.

## Track D — primary participant programme
Do not recruit until sponsor/ethics/data-protection/safeguarding documents are approved. Begin with the most attainable deep cohort, use matched comparators, and create nested optional modules for platform exports/private digital histories rather than making them mandatory for participation.

## Track E — experiments
Run only after observational work identifies a discriminatory question. Preregister vignette/framing/peer-review experiments before recruitment and power them for the smallest effect worth detecting.
