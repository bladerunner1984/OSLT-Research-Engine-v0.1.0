"""Pilot 1 preregistered specification, version 1.

Authored 2026-08-15. This is the frozen specification for the confirmatory phase of the
academic knowledge-production study. It deliberately does NOT cover the exploratory corpus
retrieved on 15 August 2026: that retrieval preceded this freeze, so it can inform search
design and nothing else. `analysis_is_confirmatory` enforces that with
FREEZE_POSTDATES_DATA_RETRIEVAL, and it should be allowed to.
"""

from __future__ import annotations

from oslt_research.domain.models import ScopeContext
from oslt_research.governance.preregistration import (
    DateWindow,
    PreregisteredSpecification,
    SearchConcept,
    SelectionRule,
)


#: Named cohorts and service datasets that recur in this literature. Frozen here rather
#: than chosen later because StudyFamilyResolver uses it to collapse dependent studies, and
#: picking it after seeing the corpus would inflate apparent independence.
COHORT_LEXICON = [
    "amsterdam cohort of gender dysphoria",
    "gender identity development service",
    "transyouth project",
    "trans youth care",
    "dutch protocol",
    "endocrine society clinical practice guideline",
]


SPECIFICATION = PreregisteredSpecification(
    specification_id="OSLT-P1-ACADEMIC-KNOWLEDGE-V1",
    objective=(
        "Determine whether registration, publication, citation and funding processes treat "
        "competing explanatory frameworks differently, after controlling for study design, "
        "quality, field size, year, discipline and evidence dependency."
    ),
    proposition_ids=["MD11", "MX14"],
    scope=ScopeContext(
        construct="publication of registered studies reporting gender-related identity, presentation or referral outcomes",
        population=(
            "studies registered on ClinicalTrials.gov, ISRCTN or PROSPERO between 2010-01-01 "
            "and 2022-08-15 with a gender-related identity, presentation or referral outcome"
        ),
        period="2010-01-01..2022-08-15 registration; publication followed to 2025-08-15",
        jurisdiction="international, English-language bibliographic indexes",
        estimand=(
            "risk difference in the probability of a registered study appearing as an indexed "
            "publication within 36 months of registration, comparing studies coded as reporting "
            "findings favourable versus unfavourable to the intrinsic/recognition framework, "
            "conditional on design, quality, field size, registration year and discipline, with "
            "dependency families collapsed before estimation"
        ),
    ),
    search_concepts=[
        SearchConcept(
            concept_id="SC1",
            concept="gender dysphoria adolescent referral",
            query_terms=[
                "gender dysphoria",
                "gender incongruence",
                "gender identity referral",
                "adolescent gender service",
            ],
            sources=["OpenAlex", "Crossref", "PubMed", "ClinicalTrials.gov"],
        ),
        SearchConcept(
            concept_id="SC2",
            concept="counterevidence lanes",
            query_terms=[
                "no significant association",
                "contradictory findings",
                "alternative explanation",
                "replication study",
                "risk of bias",
                "retracted",
            ],
            sources=["OpenAlex", "PubMed"],
        ),
    ],
    date_windows=[
        DateWindow(
            window_id="W_REG",
            from_date="2010-01-01",
            to_date="2022-08-15",
            applies_to="registration date; the 2022 ceiling leaves a 36-month publication window",
        ),
        DateWindow(
            window_id="W_PUB",
            from_date="2010-01-01",
            to_date="2025-08-15",
            applies_to="publication date used to determine linkage and time-to-publication",
        ),
    ],
    selection_rules=[
        SelectionRule(
            rule_id="INC1",
            rule_type="INCLUSION",
            description=(
                "Registration carries a gender-related identity, presentation or referral "
                "outcome and a resolvable registration date."
            ),
        ),
        SelectionRule(
            rule_id="INC2",
            rule_type="INCLUSION",
            description="Registration date falls inside window W_REG.",
        ),
        SelectionRule(
            rule_id="EXC1",
            rule_type="EXCLUSION",
            description=(
                "Registration whose linkage search failed on every index; excluded from the "
                "denominator so a system failure is never counted as a non-publication."
            ),
        ),
        SelectionRule(
            rule_id="EXC2",
            rule_type="EXCLUSION",
            description=(
                "Records retrieved before this specification was frozen; those are exploratory "
                "and may inform search design only."
            ),
        ),
        SelectionRule(
            rule_id="EXC3",
            rule_type="EXCLUSION",
            description=(
                "Direction coding assigned by the automated classifier alone; a record needs "
                "human adjudication before it enters the confirmatory estimate."
            ),
        ),
    ],
    planned_analysis=(
        "1. Assemble registrations in W_REG and link to publications on exact registration "
        "identifier. 2. Resolve dependency families using COHORT_LEXICON plus trial, accession "
        "and author-network signals; collapse before estimation. 3. Blind dual-code direction "
        "of finding, adjudicate disagreements, report Cohen's kappa with the base rate stated. "
        "4. Estimate the risk difference in 36-month publication conditional on design, "
        "quality, field size, year and discipline. 5. Report the MX14 null as a competing "
        "model, not a residual. 6. Report the E-value for any non-null estimate. 7. Report the "
        "attained power and the minimum detectable effect alongside every estimate, so a null "
        "is never reported as evidence of absence."
    ),
    primary_outcome=(
        "Indexed publication within 36 months of registration (binary), joined on exact "
        "registration identifier."
    ),
    cohort_lexicon=COHORT_LEXICON,
    notes=(
        "Authored by Claude Opus 5 under founder direction. Not yet reviewed by a human "
        "methodologist. The corpus retrieved on 2026-08-15 predates this freeze and is "
        "permanently exploratory. Direction coding requires a second human coder that the "
        "project does not yet have, so step 3 is not executable at the time of freezing."
    ),
)
