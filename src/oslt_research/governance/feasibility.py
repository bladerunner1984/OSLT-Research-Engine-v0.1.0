from __future__ import annotations

import csv
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Reachability(StrEnum):
    """How far a proposition can be taken with the access the project actually has."""

    #: Every required workstream has an open route, and the design does not need
    #: individual-level follow-up. Testable now.
    OPEN_TESTABLE = "OPEN_TESTABLE"

    #: Open data exists but only in aggregate, while the proposition needs individuals
    #: followed over time. Aggregate data cannot answer it at any sample size.
    NEEDS_INDIVIDUAL_LEVEL = "NEEDS_INDIVIDUAL_LEVEL"

    #: A required workstream has no open route at all - licensed corpora, restricted
    #: administrative data, or a secure environment.
    NEEDS_RESTRICTED_ACCESS = "NEEDS_RESTRICTED_ACCESS"

    #: Requires collecting new data from participants: recruitment, consent, ethics.
    NEEDS_PRIMARY_COLLECTION = "NEEDS_PRIMARY_COLLECTION"

    #: Every required workstream is open, but none of them carries the predictor the
    #: proposition's own prediction names. The test cannot be run as registered: one of
    #: its two terms is missing. Being honestly blocked is more useful than being
    #: falsely testable, because a "testable" proposition with no predictor consumes a
    #: run and returns INCONCLUSIVE for a reason that was knowable in advance.
    NEEDS_PREDICTOR_SOURCE = "NEEDS_PREDICTOR_SOURCE"


#: Access tokens in workstreams.csv that represent a route requiring no agreement.
OPEN_TOKENS = frozenset(
    {"OPEN", "OPEN_AGGREGATE", "OPEN_API", "OPEN_ARCHIVE", "OPEN_CORPUS", "PUBLIC_WEB"}
)

#: Tokens meaning new data must be collected from people.
PRIMARY_TOKENS = frozenset({"PRIMARY_RESEARCH"})

#: Temporal requirements that cannot be met with aggregate statistics, because they are
#: statements about the ordering of events within individuals.
INDIVIDUAL_LEVEL_REQUIREMENTS = (
    "pre-exposure baseline and longitudinal follow-up",
    "longitudinal; exposure must precede outcome",
)


@dataclass(frozen=True)
class PredictorConcept:
    """One predictor a prediction can name, and the registry words that would carry it.

    Both halves are declared, narrow and reviewable. The alternative - scoring free-text
    similarity between a prediction and a workstream blurb - would manufacture confident
    answers out of vocabulary overlap, which is the plausible-default failure this project
    keeps finding. A concept that no prediction names costs nothing; a concept that fires
    on the wrong proposition is visible in one line of this table.
    """

    concept_id: str
    #: Phrases whose presence in the prediction means the prediction NAMES this predictor.
    prediction_terms: tuple[str, ...]
    #: Phrases in a workstream's ``data_to_accumulate`` (or its title) that mean the
    #: workstream CARRIES this predictor.
    data_terms: tuple[str, ...]
    #: What is actually missing, in words a reader can act on.
    describes: str


#: The declared predictor lexicon.
#:
#: Deliberately small. It covers only predictors that some proposition's registered
#: prediction names explicitly and that a reader can check against workstreams.csv in
#: seconds. Anything a prediction names that is NOT in this table is treated as UNKNOWN
#: and does not block - absence of a lexicon entry is not evidence of absence of data,
#: and this check exists to remove false testability, not to manufacture false blockage.
PREDICTOR_LEXICON: tuple[PredictorConcept, ...] = (
    PredictorConcept(
        concept_id="DISCLOSURE_OR_HELP_SEEKING",
        prediction_terms=("disclosure", "help-seeking", "help seeking"),
        data_terms=("disclosure", "help-seeking", "narrative", "interview"),
        describes="a disclosure or help-seeking indicator",
    ),
    PredictorConcept(
        concept_id="AWARENESS_OR_MEDIA_ATTENTION",
        prediction_terms=("awareness", "media attention", "search/media"),
        data_terms=(
            "search behaviour",
            "media-use",
            "news corpora",
            "gdelt",
            "framing",
            "platform use",
            "web archives",
        ),
        describes="a search-volume, media-attention or professional-awareness measure",
    ),
    PredictorConcept(
        concept_id="ACCESS_GRADIENT",
        prediction_terms=("variation in access", "access predicts", "distance", "travel"),
        data_terms=("distance", "travel time", "need proxy", "access gradient"),
        describes="a distance-to-service or need-proxy measure separable from geography",
    ),
    PredictorConcept(
        concept_id="FOLLOW_UP_OF_INDIVIDUALS",
        prediction_terms=("attrition", "ipw", "mnar", "missingness", "follow-up"),
        data_terms=("repeated measures", "longitudinal", "cohort", "follow-up"),
        describes="a cohort followed through time, so that attrition has an estimate to move",
    ),
    PredictorConcept(
        concept_id="ADOPTION_OUTCOME_PER_NODE",
        prediction_terms=("adoption",),
        data_terms=("adoption", "uptake", "implementation outcome"),
        describes="a per-node adoption or uptake outcome the network could predict",
    ),
    PredictorConcept(
        concept_id="CROSS_JURISDICTION_PANEL",
        prediction_terms=("cross-jurisdiction", "cross jurisdiction", "macro longitudinal"),
        data_terms=("cross-jurisdiction", "international", "country-level", "comparative"),
        describes="a cross-jurisdiction or macro longitudinal panel",
    ),
)


def named_predictors(prediction: str) -> list[PredictorConcept]:
    """Which lexicon concepts a registered prediction explicitly names."""

    text = (prediction or "").casefold()
    return [
        concept
        for concept in PREDICTOR_LEXICON
        if any(term in text for term in concept.prediction_terms)
    ]


def _carries(concept: PredictorConcept, workstream: dict[str, str]) -> bool:
    haystack = " ".join(
        (workstream.get(name) or "") for name in ("data_to_accumulate", "workstream")
    ).casefold()
    return any(term in haystack for term in concept.data_terms)


def missing_predictors(
    prediction: str, required: list[str], workstreams: dict[str, dict[str, str]]
) -> list[PredictorConcept]:
    """Predictors the prediction names that no required workstream carries.

    Reads ``data_to_accumulate``, which is what the registry actually has. If that column
    is absent the function returns nothing: an unpopulated registry must not be read as a
    registry full of holes.
    """

    if not any("data_to_accumulate" in row for row in workstreams.values()):
        return []
    return [
        concept
        for concept in named_predictors(prediction)
        if not any(_carries(concept, workstreams[wid]) for wid in required if wid in workstreams)
    ]


@dataclass(frozen=True)
class PropositionFeasibility:
    proposition_id: str
    model_family: str
    domain: str
    reachability: Reachability
    required_workstreams: list[str] = field(default_factory=list)
    blocking_workstreams: list[str] = field(default_factory=list)
    temporal_requirement: str = ""
    maximum_claim_state: str = ""
    reason: str = ""
    missing_predictors: list[str] = field(default_factory=list)

    @property
    def testable_now(self) -> bool:
        return self.reachability is Reachability.OPEN_TESTABLE


@dataclass(frozen=True)
class FeasibilityCensus:
    results: list[PropositionFeasibility] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for item in self.results:
            tally[item.reachability.value] = tally.get(item.reachability.value, 0) + 1
        return dict(sorted(tally.items()))

    def testable_now(self) -> list[PropositionFeasibility]:
        return [item for item in self.results if item.testable_now]

    def testable_by_model_family(self) -> dict[str, int]:
        tally: dict[str, int] = {}
        for item in self.testable_now():
            tally[item.model_family] = tally.get(item.model_family, 0) + 1
        return dict(sorted(tally.items()))

    def coverage_asymmetry(self) -> list[str]:
        """Warn when open-testable propositions are concentrated in a few model families.

        This is the failure mode that matters most here, and it is invisible in any single
        result. If one model family has testable propositions and its rivals do not, then
        running the engine on open data returns that family as the leader regardless of
        what is true - not because the evidence favours it, but because the alternatives
        were never on the ballot. A comparative support index computed over an unequal
        ballot is a measure of data access, not of explanation.
        """

        warnings: list[str] = []
        families = {item.model_family for item in self.results if item.model_family}
        testable = self.testable_by_model_family()
        untestable = sorted(family for family in families if family not in testable)

        if untestable:
            warnings.append(
                "MODEL_FAMILIES_WITH_NO_OPEN_TESTABLE_PROPOSITION:" + ",".join(untestable)
            )
        if testable:
            leader, count = max(testable.items(), key=lambda pair: pair[1])
            total = sum(testable.values())
            # Strict majority: an even split between two families is not dominance.
            if total and count / total > 0.5:
                warnings.append(
                    f"OPEN_TESTABLE_SET_DOMINATED_BY:{leader}:{count}/{total}"
                )
        if warnings:
            warnings.append(
                "COMPARATIVE_SUPPORT_OVER_AN_UNEQUAL_BALLOT_MEASURES_DATA_ACCESS_NOT_EXPLANATION"
            )
        return warnings

    def summary(self) -> dict[str, object]:
        return {
            "propositions": len(self.results),
            "testable_from_open_sources": len(self.testable_now()),
            "by_reachability": self.counts(),
            "testable_ids": [item.proposition_id for item in self.testable_now()],
            "testable_by_model_family": self.testable_by_model_family(),
            "coverage_asymmetry": self.coverage_asymmetry(),
        }


def _split(value: str) -> list[str]:
    return [part.strip() for part in (value or "").replace(",", ";").split(";") if part.strip()]


def assess_feasibility(registry_root: str | Path) -> FeasibilityCensus:
    """Classify every proposition by what access its test would actually require.

    Answers a question that has to be settled before any plan to 'answer everything':
    which propositions are reachable with open data, and which are gated behind data the
    project has no route to. The gate is rarely engineering effort. It is usually that the
    design needs individuals followed through time, and no amount of public aggregate
    statistics substitutes for that.
    """

    root = Path(registry_root)
    workstreams = {
        row["workstream_id"]: row
        for row in csv.DictReader((root / "workstreams.csv").open(encoding="utf-8-sig"))
    }
    hypotheses = list(csv.DictReader((root / "hypotheses.csv").open(encoding="utf-8-sig")))

    results: list[PropositionFeasibility] = []
    for row in hypotheses:
        required = _split(row.get("required_workstreams", ""))
        blocking: list[str] = []
        primary: list[str] = []

        for workstream_id in required:
            workstream = workstreams.get(workstream_id)
            if workstream is None:
                blocking.append(workstream_id)
                continue
            tokens = set(_split(workstream.get("access_summary", "")))
            if tokens & PRIMARY_TOKENS and not tokens & OPEN_TOKENS:
                primary.append(workstream_id)
            elif not tokens & OPEN_TOKENS:
                blocking.append(workstream_id)

        missing = missing_predictors(row.get("prediction", ""), required, workstreams)
        temporal = row.get("temporal_requirement", "")
        needs_individual = any(
            marker in temporal for marker in INDIVIDUAL_LEVEL_REQUIREMENTS
        )

        if primary:
            reachability = Reachability.NEEDS_PRIMARY_COLLECTION
            reason = (
                f"workstream(s) {', '.join(primary)} require collecting new data from "
                "participants: recruitment, consent and ethics approval"
            )
        elif blocking:
            reachability = Reachability.NEEDS_RESTRICTED_ACCESS
            reason = (
                f"workstream(s) {', '.join(blocking)} have no open route; they need "
                "licensed, administrative or secure-environment access"
            )
        elif needs_individual:
            reachability = Reachability.NEEDS_INDIVIDUAL_LEVEL
            reason = (
                f"design requires '{temporal}', which is a statement about ordering within "
                "individuals; open aggregate statistics cannot answer it at any sample size"
            )
        elif missing:
            reachability = Reachability.NEEDS_PREDICTOR_SOURCE
            reason = (
                "every required workstream is open, but none of "
                + ", ".join(required)
                + " carries "
                + "; ".join(concept.describes for concept in missing)
                + " - the prediction names a predictor the required set does not hold, so "
                "the test cannot be run as registered"
            )
        else:
            reachability = Reachability.OPEN_TESTABLE
            reason = "all required workstreams have an open route and the design is not individual-level"

        results.append(
            PropositionFeasibility(
                proposition_id=row.get("proposition_id", ""),
                model_family=row.get("model_family", ""),
                domain=row.get("domain", ""),
                reachability=reachability,
                required_workstreams=required,
                blocking_workstreams=blocking or primary,
                temporal_requirement=temporal,
                maximum_claim_state=row.get("maximum_claim_state", ""),
                reason=reason,
                missing_predictors=[concept.concept_id for concept in missing],
            )
        )

    return FeasibilityCensus(results=results)


# --------------------------------------------------------------------------- provenance
#
# The census is a pure function of two registry CSVs. Nothing else feeds it - not the
# store, not the connector inventory. That is easy to forget once the numbers are quoted
# in prose, and forgetting it produces the opposite of the truth: "we added five
# connectors, so more propositions must be testable now". They are not, because
# reachability is read from `access_summary` tokens a human wrote in workstreams.csv.
# The digest below is persisted with every census so that a later reader can tell whether
# a difference in the numbers came from the registry changing or from the code changing.

CENSUS_INPUT_FILES = ("workstreams.csv", "hypotheses.csv")


def registry_digest(registry_root: str | Path) -> dict[str, str]:
    """SHA-256 of each file the census actually reads.

    Persisted alongside the counts so a re-run that disagrees can be attributed to an
    input change rather than argued about.
    """

    from oslt_research.evidence.provenance import sha256_bytes

    root = Path(registry_root)
    return {name: sha256_bytes((root / name).read_bytes()) for name in CENSUS_INPUT_FILES}


def connector_source_ids() -> tuple[dict[str, str], list[str]]:
    """Live connector inventory: declared ``SOURCE_ID`` per module, and the undeclared rest.

    Read from the package rather than a hand-maintained list. Returns two things because
    there are two answers and they must not be merged: modules that declare which registry
    source they serve, and modules that declare nothing. The second group is **UNKNOWN**,
    not "serves no workstream" - treating it as absence would understate coverage exactly
    where the evidence is missing, which is the wrong direction to be wrong in.
    """

    import importlib
    import pkgutil

    from oslt_research import connectors as connector_package

    found: dict[str, str] = {}
    undeclared: list[str] = []
    for module_info in pkgutil.iter_modules(connector_package.__path__):
        if module_info.name in {"base", "fixture"}:
            continue
        module = importlib.import_module(f"{connector_package.__name__}.{module_info.name}")
        source_id = getattr(module, "SOURCE_ID", None)
        if isinstance(source_id, str) and source_id:
            found[module_info.name] = source_id
        else:
            undeclared.append(module_info.name)
    return dict(sorted(found.items())), sorted(undeclared)


def workstream_source_coverage(
    registry_root: str | Path,
    *,
    connector_ids: set[str],
    store_source_ids: set[str],
) -> dict[str, dict[str, object]]:
    """Overlay the live connector inventory onto each workstream's declared sources.

    Deliberately kept *separate* from :func:`assess_feasibility` and deliberately not fed
    back into `Reachability`. A workstream can declare an open route that no connector
    implements; that is an engineering gap, not an access gap, and collapsing the two
    would make the census answer a different question than the one it is quoted for.

    ``connector_status_unknown`` means no connector *declares* that source id - not that
    none serves it. Most connector modules declare no ``SOURCE_ID`` at all, and guessing
    which workstream ``UNREGISTERED:NOMIS`` belongs to by name is exactly the
    plausible-default failure this project keeps finding.
    """

    root = Path(registry_root)
    rows = list(csv.DictReader((root / "workstreams.csv").open(encoding="utf-8-sig")))
    registered = {value for value in connector_ids if not value.startswith("UNREGISTERED:")}

    coverage: dict[str, dict[str, object]] = {}
    for row in rows:
        declared = set(_split(row.get("source_ids", "")))
        coverage[row["workstream_id"]] = {
            "declared_source_ids": sorted(declared),
            "with_connector": sorted(declared & registered),
            "with_records_in_store": sorted(declared & store_source_ids),
            "connector_status_unknown": sorted(declared - registered),
        }
    return coverage
