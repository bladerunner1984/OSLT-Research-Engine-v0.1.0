from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from oslt_research.governance.mechanism_simulation import ObservedSeries


#: DS031 in the source register. Hansard is the official report of parliamentary
#: proceedings, so a count of contributions mentioning a term is a published, consistently
#: defined, dated measure - which is what the calibrated mechanism simulation needs and
#: what the registry's own candidate series (clinic waiting statistics, DS047) could not
#: supply, its definitions differing by clinic and its public series being incomplete.
SOURCE_ID = "DS031"

#: Which counted thing to build a series from. Contributions are individual spoken or
#: written interventions; debates are whole items. Contributions give a finer series and
#: are less sensitive to how proceedings happen to be split into items.
COUNTABLE_FIELDS = (
    "TotalContributions",
    "TotalDebates",
    "TotalWrittenStatements",
    "TotalWrittenAnswers",
)


@dataclass(frozen=True)
class HansardYear:
    year: int
    counts: dict[str, int] = field(default_factory=dict)
    errored: bool = False

    def value(self, field_name: str = "TotalContributions") -> int:
        return self.counts.get(field_name, 0)


@dataclass(frozen=True)
class HansardSeries:
    term: str
    years: list[HansardYear] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        """A series with a failed year has a hole, and a hole is not a zero."""

        return bool(self.years) and not any(item.errored for item in self.years)

    def to_observed_series(self, field_name: str = "TotalContributions") -> ObservedSeries:
        """Convert to a calibration target.

        Refuses to build a series with a failed year. Silently treating a failed request
        as a zero would put a fabricated trough into the very data a mechanism is being
        tested against.
        """

        if not self.complete:
            failed = [str(item.year) for item in self.years if item.errored]
            raise ValueError(
                f"series has failed years ({', '.join(failed)}); a failed request is not a "
                "zero and must not be calibrated against"
            )
        return ObservedSeries(
            name=f"Hansard {field_name} mentioning '{self.term}'",
            source_id=SOURCE_ID,
            values=tuple(float(item.value(field_name)) for item in self.years),
            periods=tuple(str(item.year) for item in self.years),
        )


class HansardConnector:
    """Counts of parliamentary contributions mentioning a term, by year.

    Produces a dated aggregate series suitable as a calibration target: a mechanism that
    cannot reproduce the observed shape of parliamentary attention under any admitted
    parameter is disfavoured by real data rather than by assumption.

    What the series measures is parliamentary attention, and nothing else. It is not a
    proxy for prevalence, referral, or public opinion, and the constitution's rule that
    discourse change is not causal proof applies to it directly.

    Requires no API key.
    """

    source_name = "Hansard"
    connector_version = "1"
    base_url = "https://hansard-api.parliament.uk/search.json"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 45.0,
        min_interval_seconds: float = 0.25,
    ):
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _year(self, term: str, year: int) -> HansardYear:
        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            self._throttle()
            response = client.get(
                self.base_url,
                params={
                    "queryParameters.searchTerm": term,
                    "queryParameters.startDate": f"{year}-01-01",
                    "queryParameters.endDate": f"{year}-12-31",
                    "queryParameters.take": 1,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return HansardYear(year=year, errored=True)
        finally:
            if self._client is None:
                client.close()

        return HansardYear(
            year=year,
            counts={
                name: int(payload.get(name) or 0)
                for name in COUNTABLE_FIELDS
                if isinstance(payload.get(name), (int, float))
            },
        )

    def series(self, *, term: str, start_year: int, end_year: int) -> HansardSeries:
        if end_year < start_year:
            raise ValueError("end_year cannot precede start_year")
        return HansardSeries(
            term=term,
            years=[self._year(term, year) for year in range(start_year, end_year + 1)],
        )
