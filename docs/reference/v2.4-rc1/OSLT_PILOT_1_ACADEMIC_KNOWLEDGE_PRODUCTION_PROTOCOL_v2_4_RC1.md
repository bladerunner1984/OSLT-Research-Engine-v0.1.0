# OSLT Pilot 1 — Academic Knowledge Production

## Primary question
Do registration, publication, citation, funding and guideline-diffusion processes treat competing explanatory frameworks differently after controlling for study design, quality, field size, year, discipline and dependency?

## Initial data sources
OpenAlex, Crossref, PubMed/Europe PMC, ClinicalTrials.gov, ISRCTN, WHO ICTRP, PROSPERO, OSF, UKRI Gateway to Research, Retraction Watch/Crossref updates, ORCID/ROR; licensed bibliometrics only as validation if available.

## Corpus construction
1. Preregister search concepts and dates.
2. Retrieve broad candidate corpus; preserve query and API response metadata.
3. Deduplicate by DOI/PMID/title/author/year and cluster study families/datasets.
4. Blind dual-code a validation set for orientation, design, population, outcome and explanatory framework.
5. Train/validate any automated classifier against human coding; report calibration/error by class.
6. Link registrations to publications where possible.
7. Analyse publication probability, time-to-publication, citations, funding and guideline uptake conditional on design/quality.
8. Run null/rival model: asymmetry reflects underlying study distribution/quality, not selection.

## Prohibited inference
Raw publication/citation count cannot establish truth or bias. Direction-dependent selection requires a denominator and appropriate controls.
