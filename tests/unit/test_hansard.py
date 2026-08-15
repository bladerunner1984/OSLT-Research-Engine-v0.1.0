from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.hansard import (
    SOURCE_ID,
    HansardConnector,
    HansardSeries,
    HansardYear,
)


def payload(contributions: int = 100, debates: int = 3) -> dict:
    return {
        "TotalContributions": contributions,
        "TotalDebates": debates,
        "TotalWrittenStatements": 2,
        "TotalWrittenAnswers": 0,
        "TotalMembers": 0,
    }


def connector_for(*, status: int = 200, body: dict | None = None) -> HansardConnector:
    def handler(request: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status)
        return httpx.Response(200, json=body if body is not None else payload())

    return HansardConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)), min_interval_seconds=0.0
    )


def test_series_spans_the_requested_years():
    series = connector_for().series(term="x", start_year=2020, end_year=2023)
    assert [item.year for item in series.years] == [2020, 2021, 2022, 2023]
    assert series.complete


def test_counts_are_read_from_the_payload():
    series = connector_for(body=payload(contributions=42)).series(
        term="x", start_year=2020, end_year=2020
    )
    assert series.years[0].value("TotalContributions") == 42
    assert series.years[0].value("TotalDebates") == 3


def test_inverted_year_range_is_rejected():
    with pytest.raises(ValueError, match="cannot precede"):
        connector_for().series(term="x", start_year=2024, end_year=2020)


def test_a_failed_year_marks_the_series_incomplete():
    series = connector_for(status=503).series(term="x", start_year=2020, end_year=2021)
    assert not series.complete
    assert all(item.errored for item in series.years)


def test_a_failed_year_is_never_calibrated_against_as_a_zero():
    """A hole in the series is not a trough, and treating it as one fabricates data."""

    series = HansardSeries(
        term="x",
        years=[HansardYear(2020, {"TotalContributions": 10}), HansardYear(2021, errored=True)],
    )
    with pytest.raises(ValueError, match="failed request is not a zero"):
        series.to_observed_series()


def test_observed_series_carries_the_source_and_periods():
    series = connector_for(body=payload(contributions=7)).series(
        term="gender identity", start_year=2020, end_year=2022
    )
    observed = series.to_observed_series()
    assert observed.source_id == SOURCE_ID
    assert observed.values == (7.0, 7.0, 7.0)
    assert observed.periods == ("2020", "2021", "2022")
    assert "gender identity" in observed.name


def test_a_different_countable_field_can_be_selected():
    series = connector_for(body=payload(contributions=5, debates=9)).series(
        term="x", start_year=2020, end_year=2022
    )
    assert series.to_observed_series("TotalDebates").values == (9.0, 9.0, 9.0)


def test_malformed_json_is_treated_as_a_failed_year_not_a_zero():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json")

    connector = HansardConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)), min_interval_seconds=0.0
    )
    series = connector.series(term="x", start_year=2020, end_year=2020)
    assert series.years[0].errored
    assert not series.complete
