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
            )
        )

    return FeasibilityCensus(results=results)
