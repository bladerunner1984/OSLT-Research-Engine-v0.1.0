from __future__ import annotations

from datetime import date, timedelta

import httpx
import pytest

from oslt_research.connectors.media_discourse import (
    SOURCE_ID,
    TIMELINE_MODE,
    GdeltDiscourseConnector,
    MediaInterval,
    MediaVolumeSeries,
)

QUERY = '"flood defence"'


def timeline_payload(
    start: date,
    days: int,
    *,
    query: str = QUERY,
    counts: list[int] | None = None,
    norms: list[int] | None = None,
    resolution: str = "day",
) -> dict:
    counts = counts if counts is not None else [1] * days
    norms = norms if norms is not None else [100_000] * days
    data = [
        {
            "date": (start + timedelta(days=i)).strftime("%Y%m%dT000000Z"),
            "value": counts[i],
            "norm": norms[i],
        }
        for i in range(days)
    ]
    return {
        "query_details": {"title": query, "date_resolution": resolution},
        "timeline": [{"series": "Article Count", "data": data}],
    }


def connector_for(handler) -> GdeltDiscourseConnector:
    return GdeltDiscourseConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        min_interval_seconds=0.0,
    )


def static(payload: dict, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return handler


def test_series_covers_every_requested_day_and_uses_the_raw_volume_mode():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=timeline_payload(date(2024, 1, 1), 5))

    series = connector_for(handler).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 5)
    )
    assert [item.period for item in series.intervals] == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
        "2024-01-04",
        "2024-01-05",
    ]
    assert series.complete
    assert seen[0].url.params["mode"] == TIMELINE_MODE
    assert seen[0].url.params["query"] == QUERY


def test_observed_series_carries_source_id_periods_and_values():
    payload = timeline_payload(date(2024, 1, 1), 4, counts=[0, 3, 7, 2])
    series = connector_for(static(payload)).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 4)
    )
    observed = series.to_observed_series()
    assert observed.source_id == SOURCE_ID
    assert observed.values == (0.0, 3.0, 7.0, 2.0)
    assert observed.periods == ("2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04")
    assert QUERY in observed.name


def test_a_failed_request_becomes_a_missing_interval_not_a_zero():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    series = connector_for(handler).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 4)
    )
    assert not series.complete
    assert series.missing_periods == [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
        "2024-01-04",
    ]
    assert all(item.count == 0 and item.missing for item in series.intervals)
    with pytest.raises(ValueError, match="not a zero"):
        series.to_observed_series()


def test_a_day_absent_from_the_response_is_missing_not_zero():
    payload = timeline_payload(date(2024, 1, 1), 3)
    series = connector_for(static(payload)).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 5)
    )
    assert series.missing_periods == ["2024-01-04", "2024-01-05"]
    with pytest.raises(ValueError):
        series.to_observed_series()


def test_a_day_with_nothing_monitored_is_missing_not_zero():
    payload = timeline_payload(
        date(2024, 1, 1), 3, counts=[4, 0, 6], norms=[100_000, 0, 100_000]
    )
    series = connector_for(static(payload)).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3)
    )
    assert series.missing_periods == ["2024-01-02"]
    assert series.intervals[1].reason == "nothing monitored"


def test_a_genuine_zero_with_a_monitored_corpus_is_kept():
    payload = timeline_payload(
        date(2024, 1, 1), 3, counts=[0, 0, 5], norms=[90_000, 90_000, 90_000]
    )
    series = connector_for(static(payload)).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3)
    )
    assert series.complete
    assert series.to_observed_series().values == (0.0, 0.0, 5.0)


def test_a_query_the_api_does_not_echo_is_rejected_rather_than_trusted():
    payload = timeline_payload(date(2024, 1, 1), 3, query="something else entirely")
    series = connector_for(static(payload)).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3)
    )
    assert not series.complete
    assert all(item.reason == "query not echoed by API" for item in series.intervals)


def test_non_daily_resolution_is_refused_rather_than_reinterpreted():
    payload = timeline_payload(date(2024, 1, 1), 3, resolution="hour")
    series = connector_for(static(payload)).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3)
    )
    assert not series.complete
    assert series.intervals[0].reason == "non-daily date resolution"


def test_a_rate_limit_response_is_retried_and_not_parsed_as_data():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="Please limit requests to one every 5 seconds")
        return httpx.Response(200, json=timeline_payload(date(2024, 1, 1), 3))

    series = connector_for(handler).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3)
    )
    assert calls["n"] == 2
    assert series.complete


def test_persistent_rate_limiting_yields_missing_intervals_not_zeros():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Please limit requests to one every 5 seconds")

    connector = GdeltDiscourseConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        min_interval_seconds=0.0,
        max_attempts=3,
    )
    series = connector.series(query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3))
    assert series.missing_periods == ["2024-01-01", "2024-01-02", "2024-01-03"]


def test_the_range_is_split_into_windows_and_each_window_stands_alone():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json=timeline_payload(date(2024, 1, 1), 2))
        return httpx.Response(503)

    series = connector_for(handler).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 4), window_days=2
    )
    assert len(requests) == 2
    assert [item.missing for item in series.intervals] == [False, False, True, True]


def test_throttling_is_enforced_by_default():
    connector = GdeltDiscourseConnector()
    assert connector.min_interval_seconds >= 5.0


def test_normalised_intensity_divides_by_the_monitored_corpus():
    payload = timeline_payload(
        date(2024, 1, 1), 3, counts=[10, 10, 10], norms=[1_000_000, 2_000_000, 500_000]
    )
    series = connector_for(static(payload)).series(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3)
    )
    observed = series.to_observed_series(normalised=True)
    assert observed.values == (10.0, 5.0, 20.0)
    assert "normalised" in observed.name


def test_articles_expose_the_crawl_timestamp_under_an_unambiguous_name():
    payload = {
        "articles": [
            {
                "url": "https://example.org/a",
                "title": " A headline ",
                "seendate": "20240329T120000Z",
                "domain": "example.org",
                "language": "English",
                "sourcecountry": "United Kingdom",
            },
            {"title": "no url", "seendate": "20240329T121500Z"},
        ]
    }
    records = connector_for(static(payload)).articles(
        query=QUERY, start=date(2024, 1, 1), end=date(2024, 4, 1)
    )
    assert len(records) == 1
    assert records[0].seen_at == "20240329T120000Z"
    assert records[0].title == "A headline"
    assert not hasattr(records[0], "published")


def test_articles_return_empty_on_failure_rather_than_inventing_records():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    connector = GdeltDiscourseConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        min_interval_seconds=0.0,
        max_attempts=2,
    )
    assert connector.articles(query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 2)) == []


def test_an_empty_series_is_not_complete():
    assert not MediaVolumeSeries(query=QUERY).complete
    with pytest.raises(ValueError):
        MediaVolumeSeries(query=QUERY).to_observed_series()


def test_intensity_of_an_unmonitored_interval_is_zero_not_a_division_error():
    assert MediaInterval(period="2024-01-01", count=3, monitored=0).intensity_per_million == 0.0


def test_reversed_and_degenerate_ranges_are_rejected():
    connector = connector_for(static(timeline_payload(date(2024, 1, 1), 1)))
    with pytest.raises(ValueError):
        connector.series(query=QUERY, start=date(2024, 2, 1), end=date(2024, 1, 1))
    with pytest.raises(ValueError):
        connector.series(
            query=QUERY, start=date(2024, 1, 1), end=date(2024, 1, 3), window_days=0
        )
