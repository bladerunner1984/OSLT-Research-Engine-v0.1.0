"""Media and public-discourse attention volume from GDELT 2.0 (workstream W11).

Why this exists: 23 of the 64 propositions need a dated measure of *public discourse*, and
the register's media source (DS028) is the only open one that supplies it at daily
resolution. The output is deliberately shaped as a calibration target for
``mechanism_simulation.ObservedSeries``, giving a second real series alongside the
parliamentary one in ``connectors.hansard`` - a mechanism that has to reproduce both
media and parliamentary attention is constrained by two independent measurement systems
rather than one.

What the series measures is the volume of monitored online news coverage matching a
query, and nothing else. It is not prevalence, incidence, or opinion. The constitution's
rule that discourse change is not causal proof applies to it directly, and doubly so here
because GDELT's monitored corpus itself grows and shifts over time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx

from oslt_research.governance.mechanism_simulation import ObservedSeries

#: DS028 in the source register.
SOURCE_ID = "DS028"

#: ``timelinevolraw`` rather than ``timelinevol``. ``timelinevol`` returns only a
#: *percentage* of all monitored coverage, which silently fuses the numerator (articles
#: about the topic) with a denominator (everything GDELT crawled that day) that changes
#: for reasons entirely unrelated to the topic - crawler expansion, outages, new source
#: onboarding. ``timelinevolraw`` returns both separately: ``value`` is the absolute
#: article count and ``norm`` is the total articles monitored. Keeping them apart is what
#: makes the missing-interval test below possible at all.
TIMELINE_MODE = "timelinevolraw"

#: GDELT's published limit is one request every five seconds, and it enforces it by
#: returning HTTP 429 with a plain-text body instead of JSON. Exceeding it does not queue
#: the request, it destroys it - the interval is simply never retrieved. That is data
#: loss, so the default interval sits above the stated limit rather than at it.
MIN_INTERVAL_SECONDS = 6.0

#: Observed empirically: GDELT returns 429 sporadically even for a first request from an
#: idle client, so a single 429 is not evidence that the caller misbehaved. Retrying is
#: the difference between a real interval and a fabricated hole.
MAX_ATTEMPTS = 6


@dataclass(frozen=True)
class MediaInterval:
    """One day of the volume series.

    ``missing`` is not the same as a count of zero, and the distinction is the whole
    point of this class. See :class:`MediaVolumeSeries`.
    """

    period: str
    count: int = 0
    monitored: int = 0
    missing: bool = False
    reason: str = ""

    @property
    def intensity_per_million(self) -> float:
        """Count normalised by the size of the corpus that was actually searched.

        GDELT's monitored corpus roughly doubled over some periods, so a raw count rising
        can mean the crawler grew rather than the topic did. The normalised figure is the
        honest series for a trend claim; the raw count is the honest series for a volume
        claim. Both are exposed because which one is right depends on the proposition.
        """

        if self.monitored <= 0:
            return 0.0
        return self.count / self.monitored * 1_000_000


@dataclass(frozen=True)
class MediaArticle:
    """A single matched article.

    ``seen_at`` is GDELT's ``seendate``, and it is *not* a publication date. It is the
    moment GDELT's crawler first observed the article, snapped to the 15-minute crawl
    cycle (observed values end in :00, :15, :30, :45). An article published weeks earlier
    and crawled today is dated today. The field is named ``seen_at`` rather than ``date``
    so that no downstream caller can mistake it for when the thing was published.
    """

    url: str
    title: str
    seen_at: str
    domain: str = ""
    language: str = ""
    source_country: str = ""


@dataclass(frozen=True)
class MediaVolumeSeries:
    """A dated media-attention volume series for one query."""

    query: str
    intervals: list[MediaInterval] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        """A series with a missing interval has a hole, and a hole is not a zero."""

        return bool(self.intervals) and not any(item.missing for item in self.intervals)

    @property
    def missing_periods(self) -> list[str]:
        return [item.period for item in self.intervals if item.missing]

    def to_observed_series(self, *, normalised: bool = False) -> ObservedSeries:
        """Convert to a calibration target.

        Refuses to build a series with a missing interval. A failed request, a throttled
        request, or a day on which GDELT monitored nothing at all would each arrive as an
        absent number; writing zero in its place would insert a fabricated trough into the
        very data a mechanism is being tested against, and a trough is exactly the shape a
        mechanism test is most sensitive to.
        """

        if not self.complete:
            missing = ", ".join(self.missing_periods) or "none recorded"
            raise ValueError(
                f"series has missing intervals ({missing}); a failed or unmonitored "
                "interval is not a zero and must not be calibrated against"
            )
        measure = "normalised article intensity" if normalised else "article count"
        values = tuple(
            item.intensity_per_million if normalised else float(item.count)
            for item in self.intervals
        )
        return ObservedSeries(
            name=f"GDELT daily {measure} matching '{self.query}'",
            source_id=SOURCE_ID,
            values=values,
            periods=tuple(item.period for item in self.intervals),
        )


class GdeltDiscourseConnector:
    """Daily volume of monitored news coverage matching a query.

    Requires no API key.
    """

    source_name = "GDELT 2.0 DOC API"
    connector_version = "1"
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout: float = 90.0,
        min_interval_seconds: float = MIN_INTERVAL_SECONDS,
        max_attempts: int = MAX_ATTEMPTS,
    ):
        self._client = client
        self.timeout = timeout
        self.min_interval_seconds = min_interval_seconds
        self.max_attempts = max(1, max_attempts)
        self._last_call = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_call = time.monotonic()

    def _get(self, params: dict[str, object]) -> dict | None:
        """Fetch one JSON payload, or ``None`` if it could not be retrieved.

        Returns ``None`` rather than raising because the caller converts that into an
        explicitly missing interval. GDELT signals throttling with a plain-text body, so a
        200 whose body is not JSON is treated as a failure too - parsing it optimistically
        is how a rate-limit notice becomes a zero.
        """

        client = self._client or httpx.Client(timeout=self.timeout)
        try:
            for _ in range(self.max_attempts):
                self._throttle()
                try:
                    response = client.get(self.base_url, params=params)
                except httpx.HTTPError:
                    continue
                if response.status_code == 429:
                    continue
                if response.status_code >= 400:
                    return None
                try:
                    payload = response.json()
                except ValueError:
                    continue
                if isinstance(payload, dict):
                    return payload
                return None
            return None
        finally:
            if self._client is None:
                client.close()

    @staticmethod
    def _echoes_query(payload: dict, query: str) -> bool:
        """Confirm GDELT actually applied the query rather than discarding it.

        Two connectors in this project have already shipped against APIs that accepted a
        search term and silently ignored it, returning a plausible but unfiltered series.
        GDELT echoes the applied query in ``query_details.title``; if that echo is absent
        or different, the numbers are not about the requested topic and must not be used.
        """

        details = payload.get("query_details")
        if not isinstance(details, dict):
            return False
        return str(details.get("title", "")).strip() == query.strip()

    def _fetch_window(self, query: str, start: date, end: date) -> list[MediaInterval]:
        expected = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]

        def all_missing(reason: str) -> list[MediaInterval]:
            return [
                MediaInterval(period=day.isoformat(), missing=True, reason=reason)
                for day in expected
            ]

        payload = self._get(
            {
                "query": query,
                "mode": TIMELINE_MODE,
                "format": "json",
                "startdatetime": start.strftime("%Y%m%d000000"),
                "enddatetime": end.strftime("%Y%m%d000000"),
            }
        )
        if payload is None:
            return all_missing("request failed")
        if not self._echoes_query(payload, query):
            return all_missing("query not echoed by API")

        details = payload.get("query_details") or {}
        # GDELT chooses day/hour/15-minute buckets from the span. Anything other than day
        # resolution would silently change what a "period" means mid-series, so it is
        # refused rather than reinterpreted.
        if str(details.get("date_resolution", "")).lower() != "day":
            return all_missing("non-daily date resolution")

        timeline = payload.get("timeline")
        if not isinstance(timeline, list) or not timeline:
            return all_missing("empty timeline")
        points = timeline[0].get("data")
        if not isinstance(points, list):
            return all_missing("malformed timeline")

        observed: dict[str, tuple[int, int]] = {}
        for point in points:
            stamp = str(point.get("date", ""))
            if len(stamp) < 8 or not stamp[:8].isdigit():
                continue
            key = f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}"
            observed[key] = (int(point.get("value") or 0), int(point.get("norm") or 0))

        intervals: list[MediaInterval] = []
        for day in expected:
            key = day.isoformat()
            if key not in observed:
                intervals.append(MediaInterval(period=key, missing=True, reason="day absent"))
                continue
            count, monitored = observed[key]
            if monitored <= 0:
                # GDELT monitored nothing that day, so a count of zero carries no
                # information about the topic - it is an outage, not an absence of news.
                intervals.append(
                    MediaInterval(period=key, missing=True, reason="nothing monitored")
                )
                continue
            intervals.append(MediaInterval(period=key, count=count, monitored=monitored))
        return intervals

    def series(
        self,
        *,
        query: str,
        start: date,
        end: date,
        window_days: int = 90,
    ) -> MediaVolumeSeries:
        """Build a daily volume series, requesting the range in windows.

        Long ranges are split because a single oversized request is the one GDELT is most
        likely to throttle or truncate, and a truncated window returns fewer days than
        asked for - which is detected here as missing days rather than absorbed as zeros.
        """

        if end < start:
            raise ValueError("end cannot precede start")
        if window_days < 1:
            raise ValueError("window_days must be at least 1")

        intervals: list[MediaInterval] = []
        cursor = start
        while cursor <= end:
            window_end = min(cursor + timedelta(days=window_days - 1), end)
            intervals.extend(self._fetch_window(query, cursor, window_end))
            cursor = window_end + timedelta(days=1)
        return MediaVolumeSeries(query=query, intervals=intervals)

    def articles(
        self,
        *,
        query: str,
        start: date,
        end: date,
        max_records: int = 75,
    ) -> list[MediaArticle]:
        """Fetch matched article records.

        Secondary to the series: article lists are capped and ordered by GDELT, so they
        are a qualitative sample for inspecting what a query actually matched, never a
        basis for counting anything.
        """

        payload = self._get(
            {
                "query": query,
                "mode": "artlist",
                "format": "json",
                "startdatetime": start.strftime("%Y%m%d000000"),
                "enddatetime": end.strftime("%Y%m%d000000"),
                "maxrecords": max(1, min(250, max_records)),
                "sort": "datedesc",
            }
        )
        if payload is None:
            return []
        records = payload.get("articles")
        if not isinstance(records, list):
            return []
        return [
            MediaArticle(
                url=str(record.get("url", "")),
                title=str(record.get("title", "")).strip(),
                seen_at=str(record.get("seendate", "")),
                domain=str(record.get("domain", "")),
                language=str(record.get("language", "")),
                source_country=str(record.get("sourcecountry", "")),
            )
            for record in records
            if isinstance(record, dict) and record.get("url")
        ]
