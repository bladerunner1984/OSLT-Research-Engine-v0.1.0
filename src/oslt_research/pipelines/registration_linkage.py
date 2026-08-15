from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, Sequence

from oslt_research.connectors.base import HarvestQuery, SourceConnector


#: Registration identifiers that appear verbatim in publication metadata and can therefore
#: be used as an exact join key. Nothing here is fuzzy: a registration is either cited or
#: it is not.
REGISTRATION_ID = re.compile(r"\b(NCT\d{8}|ISRCTN\d{8}|CRD4?2?\d{10,13})\b", re.I)


@dataclass(frozen=True)
class RegistrationRecord:
    registration_id: str
    registered_on: date | None = None
    completed_on: date | None = None
    title: str = ""
    status: str = ""


@dataclass(frozen=True)
class LinkageOutcome:
    """The result of looking for publications of one registration.

    `publication_ids` empty means *no publication was found by these searches*. It does
    NOT mean the study went unpublished. Publication may exist without citing its
    registration, may sit outside the indexes searched, or may be phrased so the
    identifier never appears in indexed metadata. The distinction matters because MD11 is
    a claim about publication probability, and treating unfound as unpublished would
    manufacture exactly the asymmetry the hypothesis is testing for.
    """

    registration: RegistrationRecord
    publication_ids: list[str] = field(default_factory=list)
    first_publication_on: date | None = None
    sources_searched: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def linked(self) -> bool:
        return bool(self.publication_ids)

    @property
    def searched_successfully(self) -> bool:
        return bool(self.sources_searched)

    @property
    def days_to_publication(self) -> int | None:
        if not self.first_publication_on or not self.registration.registered_on:
            return None
        delta = (self.first_publication_on - self.registration.registered_on).days
        return delta if delta >= 0 else None


@dataclass(frozen=True)
class LinkageReport:
    outcomes: list[LinkageOutcome] = field(default_factory=list)
    excluded_insufficient_follow_up: int = 0
    follow_up_cutoff: date | None = None

    @property
    def denominator(self) -> int:
        """Registrations that were actually searched - the only valid denominator.

        A registration whose search failed contributes to neither numerator nor
        denominator, because including it would silently count a system failure as a
        non-publication.
        """

        return sum(1 for outcome in self.outcomes if outcome.searched_successfully)

    @property
    def linked_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.linked)

    @property
    def linkage_rate(self) -> float | None:
        return (self.linked_count / self.denominator) if self.denominator else None

    def median_days_to_publication(self) -> float | None:
        deltas = [
            outcome.days_to_publication
            for outcome in self.outcomes
            if outcome.days_to_publication is not None
        ]
        return statistics.median(deltas) if deltas else None

    def summary(self) -> dict[str, object]:
        failed = [o for o in self.outcomes if not o.searched_successfully]
        return {
            "registrations_supplied": len(self.outcomes) + self.excluded_insufficient_follow_up,
            "excluded_insufficient_follow_up": self.excluded_insufficient_follow_up,
            "follow_up_cutoff": self.follow_up_cutoff.isoformat() if self.follow_up_cutoff else None,
            "registrations_searched": len(self.outcomes),
            "denominator_searched": self.denominator,
            "search_failures_excluded": len(failed),
            "linked": self.linked_count,
            "not_linked": self.denominator - self.linked_count,
            "linkage_rate": self.linkage_rate,
            "median_days_to_publication": self.median_days_to_publication(),
            "interpretation_bound": (
                "not_linked counts registrations for which these searches found no "
                "publication. It is not a count of unpublished studies and must never be "
                "reported as one."
            ),
        }


def parse_registration_date(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def extract_registration_ids(text: str) -> set[str]:
    return {match.group(0).upper() for match in REGISTRATION_ID.finditer(text or "")}


class RegistrationPublicationLinker:
    """Joins trial registrations to their publications on an exact identifier.

    This supplies the denominator MD11 requires. Without it, a corpus of publications can
    only show which studies appeared, never which studies were registered and then did
    not appear - and direction-dependent selection is a statement about the second.
    """

    def __init__(self, *, max_records_per_query: int = 25):
        if max_records_per_query < 1:
            raise ValueError("max_records_per_query must be at least 1")
        self.max_records_per_query = max_records_per_query

    async def link(
        self,
        registrations: Sequence[RegistrationRecord],
        connectors: Iterable[SourceConnector],
        *,
        follow_up_cutoff: date | None = None,
    ) -> LinkageReport:
        """Link registrations to publications.

        `follow_up_cutoff` excludes registrations made after it. Without a cutoff a
        publication rate is dominated by recency: a trial registered last month has not
        failed to publish, it has not had time to. Counting it as unpublished invents the
        asymmetry MD11 is trying to measure.
        """

        connector_list = list(connectors)
        outcomes: list[LinkageOutcome] = []
        excluded = 0

        for registration in registrations:
            if (
                follow_up_cutoff is not None
                and registration.registered_on is not None
                and registration.registered_on > follow_up_cutoff
            ):
                excluded += 1
                continue
            identifier = registration.registration_id.upper()
            publications: dict[str, date | None] = {}
            sources: list[str] = []
            errors: list[str] = []

            query = HarvestQuery(
                query_id=f"LINK-{identifier}",
                concept=identifier,
                max_records=self.max_records_per_query,
            )
            for connector in connector_list:
                try:
                    records = await connector.harvest(query)
                except Exception as exc:  # noqa: BLE001 - one index must not void the join
                    errors.append(f"{connector.source_name}:{type(exc).__name__}")
                    continue
                sources.append(connector.source_name)
                for record in records:
                    haystack = " ".join(
                        [record.title, record.content, *map(str, record.identifiers.values())]
                    )
                    # Exact identifier match only. A topic-similar paper is not a link.
                    if identifier not in extract_registration_ids(haystack):
                        continue
                    key = (
                        record.identifiers.get("doi")
                        or record.identifiers.get("pmid")
                        or record.source_record_id
                    )
                    publications[str(key)] = parse_registration_date(record.published_at)

            dates = [value for value in publications.values() if value is not None]
            outcomes.append(
                LinkageOutcome(
                    registration=registration,
                    publication_ids=sorted(publications),
                    first_publication_on=min(dates) if dates else None,
                    sources_searched=sorted(set(sources)),
                    errors=errors,
                )
            )

        return LinkageReport(
            outcomes=outcomes,
            excluded_insufficient_follow_up=excluded,
            follow_up_cutoff=follow_up_cutoff,
        )
