"""Frozen candidate specification for OSLT Result Package 1.

The committed freeze receipt beside this module binds the exact specification hash.
The existing 2026-08-16 Census harvest predates this specification and is exploratory;
confirmatory data must be retrieved again after the freeze timestamp.
"""

from __future__ import annotations

from oslt_research.domain.models import ScopeContext
from oslt_research.governance.preregistration import (
    DateWindow,
    PreregisteredSpecification,
    SearchConcept,
    SelectionRule,
)


SPECIFICATION = PreregisteredSpecification(
    specification_id="OSLT-RP1-CENSUS-INSTRUMENT-SENSITIVITY-V1",
    objective=(
        "Estimate how sensitive the England and Wales Census 2021 gender-identity response "
        "statistics and selected subgroup contrasts are to response-category construction, "
        "nonresponse, proxy response, language-comprehension indicators and denominator choice, "
        "without estimating latent true prevalence or any individual causal effect."
    ),
    proposition_ids=["AS10", "MX10", "IR07"],
    scope=ScopeContext(
        construct=(
            "sensitivity of published gender-identity response statistics to observable "
            "instrument and response-process features"
        ),
        population=(
            "usual residents aged 16 and over in England and Wales on the Census 2021 "
            "reference date"
        ),
        period="2021-03-21 Census reference date; confirmatory retrieval after specification freeze",
        jurisdiction="England and Wales, with Scotland used only in a separately harmonised sensitivity analysis",
        estimand=(
            "(1) prespecified prevalence ratios and risk differences for a published "
            "'gender identity different from sex registered at birth' response across observable "
            "comprehension/nonresponse strata; (2) the ratio and absolute difference produced by "
            "the two published codelists that attach 'all other gender identities' to different "
            "category contents; and (3) a sensitivity interval for the published national response "
            "proportion under frozen denominator and suspect-response recodes"
        ),
    ),
    search_concepts=[
        SearchConcept(
            concept_id="NOMIS_TABLES",
            concept="Census 2021 gender-identity response tables and prespecified cross-tabs",
            query_terms=[
                "TS070",
                "TS078",
                "RM035",
                "RM038",
                "RM163",
                "RM174",
                "RM175",
            ],
            sources=["NOMIS ONS query API", "ONS Census 2021 publications"],
        ),
        SearchConcept(
            concept_id="INSTRUMENT_EVIDENCE",
            concept="question wording, response process, uncertainty and regulatory status",
            query_terms=[
                "Census 2021 gender identity question wording",
                "quality of Census 2021 gender identity data",
                "language proficiency",
                "proxy response",
                "official statistics in development",
            ],
            sources=["Office for National Statistics", "Office for Statistics Regulation"],
        ),
    ],
    date_windows=[
        DateWindow(
            window_id="CENSUS_REFERENCE_DATE",
            from_date="2021-03-21",
            to_date="2021-03-21",
            applies_to="population reference date; publication/retrieval dates are provenance, not observations",
        )
    ],
    selection_rules=[
        SelectionRule(
            rule_id="INC1",
            rule_type="INCLUSION",
            description=(
                "Use only official published cells whose geography, age eligibility, gender-identity "
                "codelist, denominator role and observation status are explicitly resolved."
            ),
        ),
        SelectionRule(
            rule_id="INC2",
            rule_type="INCLUSION",
            description=(
                "Use the published total cell for a denominator or margin; never derive it by summing "
                "a codelist that contains its own totals or nested aggregates."
            ),
        ),
        SelectionRule(
            rule_id="INC3",
            rule_type="INCLUSION",
            description=(
                "Treat sexual-orientation response behaviour on the same form as a negative-control "
                "instrument, not as an exposure or causal covariate."
            ),
        ),
        SelectionRule(
            rule_id="EXC1",
            rule_type="EXCLUSION",
            description=(
                "Exclude structural zeros, suppressed/non-normal cells and any cell whose codelist or "
                "denominator cannot be resolved before analysis."
            ),
        ),
        SelectionRule(
            rule_id="EXC2",
            rule_type="EXCLUSION",
            description=(
                "The 2026-08-16 harvest is excluded from confirmatory status because it predates this "
                "freeze; it may inform source semantics and test fixtures only."
            ),
        ),
        SelectionRule(
            rule_id="EXC3",
            rule_type="EXCLUSION",
            description=(
                "Do not interpret cross-sectional age gradients as trends or census sex response as a "
                "verified measure of sex registered at birth."
            ),
        ),
    ],
    planned_analysis=(
        "1. Re-retrieve the frozen table set after the committed freeze and record canonical URL, "
        "query, retrieval time, source version and SHA-256 for every response. 2. Build and publish "
        "the codelist/denominator crosswalk before computing estimates. 3. Estimate the prespecified "
        "category-definition ratio and absolute difference, denominator sensitivities, nonresponse "
        "contrasts and observable language/comprehension-related contrasts with perturbation limits "
        "stated. 4. Run the same-form sexual-orientation negative control where definitionally valid. "
        "5. Apply the frozen materiality rule: a relative difference of at least 20% or an absolute "
        "difference of at least 0.10 percentage points in a headline response proportion is material; "
        "report estimates and uncertainty rather than dichotomising when perturbation prevents a "
        "decision. 6. Run denominator, category-recode and table-perturbation sensitivity analyses. "
        "7. Publish regardless of direction. No model converts these aggregate response statistics "
        "into individual exposure, identity-origin, psychological or consciousness claims."
    ),
    primary_outcome=(
        "Published proportion responding that gender identity differs from sex registered at birth, "
        "under each frozen denominator/category definition; this is a response statistic, not latent "
        "true prevalence."
    ),
    cohort_lexicon=[],
    notes=(
        "Selected first because the public source is complete for the bounded question, table and "
        "codelist semantics are auditable, the main alternative explanations have observable negative "
        "controls, data cost is zero, and the claim ceiling is independent of any preferred causal "
        "model. 'Impact on consciousness' is not an outcome. This specification authorises no new "
        "human-participant research."
    ),
)

