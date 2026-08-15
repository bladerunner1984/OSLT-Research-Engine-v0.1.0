# Pilot 01 — Academic Knowledge Production

Primary question: do registration, publication, citation, funding and guideline-diffusion processes
treat competing explanatory frameworks differently after appropriate controls and dependency
collapse?

The initial implementation provides public-source connectors, deterministic normalisation,
deduplication, study-family grouping, descriptive metrics and a fail-closed rule: publication bias is
not asserted without a denominator such as registrations/submissions or another defensible selection
model.

## Initial connector set

The bootstrap vertical slice can acquire OpenAlex, Crossref, PubMed and ClinicalTrials.gov
records. Trial registrations provide part of the planned-registration denominator; the current
bootstrap does not yet claim complete registration-to-publication linkage.
