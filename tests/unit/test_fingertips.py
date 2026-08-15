"""Tests for the Fingertips connector.

The behaviours asserted here are the ones that were actually got wrong elsewhere: a hole
becoming a zero, a query the API quietly ignored, a date field that measured something
else, and overlapping aggregates summed into a multiple of the truth.
"""

from __future__ import annotations

import json

import httpx
import pytest

from oslt_research.connectors.fingertips import (
    ENGLAND_AREA_CODE,
    PRIORITY_INDICATORS,
    SOURCE_ID,
    FingertipsConnector,
    FingertipsError,
    Observation,
    TimePeriod,
    _span_years,
)

CSV_HEADER = (
    "Indicator ID,Indicator Name,Parent Code,Parent Name,Area Code,Area Name,Area Type,"
    "Sex,Age,Category Type,Category,Time period,Value,Lower CI 95.0 limit,"
    "Upper CI 95.0 limit,Lower CI 99.8 limit,Upper CI 99.8 limit,Count,Denominator,"
    "Value note,Recent Trend,Compared to England value or percentiles,"
    "Compared to percentiles,Time period Sortable,New data,Compared to goal,"
    "Time period range"
)


def _row(
    *,
    parent: str = "",
    area_code: str = ENGLAND_AREA_CODE,
    area_name: str = "England",
    sex: str = "Persons",
    age: str = "10-24 yrs",
    category_type: str = "",
    category: str = "",
    period: str = "2011/12",
    sortable: str = "20110000",
    value: str = "347.36",
    count: str = "35241",
    denominator: str = "9987942",
    note: str = "",
) -> str:
    return (
        f"90813,Hospital admissions as a result of self-harm (10 to 24 years),{parent},"
        f"England,{area_code},{area_name},England,{sex},{age},{category_type},{category},"
        f"{period},{value},1,2,3,4,{count},{denominator},{note},Increasing,Similar,"
        f"Not compared,{sortable},,,1y"
    )


def _csv(*rows: str) -> str:
    return "\n".join((CSV_HEADER, *rows)) + "\n"


def _connector(handler) -> FingertipsConnector:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    # No throttle wait in tests; the live default is one second per request.
    return FingertipsConnector(client=client, min_interval_seconds=0.0)


def _csv_handler(body: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body)

    return handler


# --- time fields ------------------------------------------------------------------


def test_sortable_is_a_start_year_key_not_a_date():
    period = TimePeriod(label="2020/21", sortable="20200000", year_type="Financial")
    assert period.start_year == 2020
    assert period.is_financial
    assert not period.is_pooled


def test_financial_label_is_not_coerced_to_a_calendar_year():
    """"2020/21" runs April-March. Preserving the label is what stops a silent shift."""

    period = TimePeriod(label="2020/21", sortable="20200000", year_type="Financial")
    assert period.label == "2020/21"
    assert TimePeriod(label="2020", sortable="20200000", year_type="Calendar").is_financial is False


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("2020/21", 1),
        ("2019", 1),
        ("2001 - 03", 3),
        ("2016/17 - 20/21", 5),
        ("2011 - 13", 3),
    ],
)
def test_pooled_period_spans_are_recognised(label: str, expected: int):
    assert _span_years(label) == expected


# --- missingness ------------------------------------------------------------------


def test_suppressed_value_is_missing_not_zero():
    body = _csv(
        _row(),
        _row(
            area_code="E06000017",
            area_name="Rutland",
            value="",
            count="",
            denominator="",
            note="Value suppressed for disclosure control due to small count",
        ),
    )
    rows = _connector(_csv_handler(body)).observations(indicator_id=90813, year_type="Financial")
    suppressed = [row for row in rows if row.area_name == "Rutland"][0]
    assert suppressed.missing
    assert suppressed.value is None
    assert suppressed.value != 0


@pytest.mark.parametrize("raw", ["", "  ", "-", "*", "n/a", "-1", None])
def test_missing_sentinels_never_become_zero(raw):
    from oslt_research.connectors.fingertips import _parse_number

    assert _parse_number(raw) is None


def test_series_with_a_hole_refuses_to_become_a_calibration_target():
    body = _csv(
        _row(period="2011/12", sortable="20110000", value="347.36"),
        _row(
            period="2012/13",
            sortable="20120000",
            value="",
            note="Value suppressed for disclosure control due to small count",
        ),
        _row(period="2013/14", sortable="20130000", value="414.56"),
    )
    series = _connector(_csv_handler(body)).series(indicator_id=90813, year_type="Financial")
    assert series.missing_periods == ("2012/13",)
    assert not series.complete
    with pytest.raises(FingertipsError, match="not a zero"):
        series.observed()


def test_complete_series_becomes_an_observed_series():
    body = _csv(
        _row(period="2011/12", sortable="20110000", value="347.36"),
        _row(period="2012/13", sortable="20120000", value="348.99"),
        _row(period="2013/14", sortable="20130000", value="414.56"),
    )
    series = _connector(_csv_handler(body)).series(indicator_id=90813, year_type="Financial")
    observed = series.observed()
    assert observed.source_id == SOURCE_ID
    assert observed.values == (347.36, 348.99, 414.56)
    assert observed.periods == ("2011/12", "2012/13", "2013/14")


def test_pooled_series_refuses_by_default_because_windows_overlap():
    body = _csv(
        _row(period="2001 - 03", sortable="20010000", value="10"),
        _row(period="2002 - 04", sortable="20020000", value="11"),
        _row(period="2003 - 05", sortable="20030000", value="12"),
    )
    series = _connector(_csv_handler(body)).series(indicator_id=41001, year_type="Calendar")
    assert series.pooled
    with pytest.raises(FingertipsError, match="not independent"):
        series.observed()
    assert series.observed(allow_pooled=True).values == (10.0, 11.0, 12.0)


# --- overlapping aggregates -------------------------------------------------------


def test_parent_duplicate_rows_are_deduplicated_not_summed():
    """Fingertips emits each area twice; naive summing would double every figure."""

    body = _csv(
        _row(parent=""),
        _row(parent=ENGLAND_AREA_CODE),
    )
    rows = _connector(_csv_handler(body)).observations(indicator_id=90813, year_type="Financial")
    assert len(rows) == 1
    assert rows[0].value == 347.36


def test_male_and_female_are_excluded_when_selecting_persons():
    body = _csv(
        _row(sex="Persons", value="347.36"),
        _row(sex="Male", value="250.0"),
        _row(sex="Female", value="440.0"),
        _row(sex="Persons", period="2012/13", sortable="20120000", value="348.99"),
        _row(sex="Male", period="2012/13", sortable="20120000", value="251.0"),
        _row(sex="Persons", period="2013/14", sortable="20130000", value="414.56"),
    )
    series = _connector(_csv_handler(body)).series(indicator_id=90813, year_type="Financial")
    assert series.sex == "Persons"
    assert series.observed().values == (347.36, 348.99, 414.56)


def test_deprivation_decile_rows_are_excluded_from_the_headline_series():
    """Deciles re-partition the same population; keeping them duplicates the total."""

    body = _csv(
        _row(period="2011/12", sortable="20110000"),
        _row(
            period="2011/12",
            sortable="20110000",
            category_type="County & UA deprivation deciles in England",
            category="Most deprived decile",
            value="500.0",
        ),
        _row(period="2012/13", sortable="20120000", value="348.99"),
        _row(period="2013/14", sortable="20130000", value="414.56"),
    )
    series = _connector(_csv_handler(body)).series(indicator_id=90813, year_type="Financial")
    assert series.observed().values == (347.36, 348.99, 414.56)


def test_multiple_age_bands_raise_rather_than_mixing_populations():
    body = _csv(
        _row(age="10-24 yrs"),
        _row(age="25-44 yrs", value="120.0"),
    )
    with pytest.raises(FingertipsError, match="several age bands"):
        _connector(_csv_handler(body)).series(indicator_id=93972, year_type="Calendar")


def test_two_distinct_rows_for_one_period_raise_rather_than_being_combined():
    body = _csv(
        _row(period="2011/12", sortable="20110000", value="347.36"),
        _row(period="2011/12", sortable="20110000", value="999.0"),
    )
    with pytest.raises(FingertipsError, match="double-count"):
        _connector(_csv_handler(body)).series(indicator_id=90813, year_type="Financial")


def test_england_and_regions_are_never_mixed_into_one_series():
    body = _csv(
        _row(period="2011/12", sortable="20110000", value="347.36"),
        _row(
            area_code="E12000004",
            area_name="East Midlands",
            period="2011/12",
            sortable="20110000",
            value="300.0",
        ),
        _row(period="2012/13", sortable="20120000", value="348.99"),
        _row(period="2013/14", sortable="20130000", value="414.56"),
    )
    series = _connector(_csv_handler(body)).series(indicator_id=90813, year_type="Financial")
    assert series.area_code == ENGLAND_AREA_CODE
    assert len(series.observations) == 3


def test_missing_area_raises_instead_of_returning_an_empty_series():
    with pytest.raises(FingertipsError, match="no rows"):
        _connector(_csv_handler(_csv(_row()))).series(
            indicator_id=90813, area_code="E06000017", year_type="Financial"
        )


# --- query honoured ---------------------------------------------------------------


def test_search_term_reaches_the_api_and_different_terms_differ():
    """Two connectors elsewhere accepted a term their API silently discarded."""

    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        term = request.url.params["search_text"]
        captured.append(term)
        payload = {"6": [90813, 21001]} if term == "self-harm" else {"6": [10602, 41101, 90282]}
        return httpx.Response(200, text=json.dumps(payload))

    connector = _connector(handler)
    self_harm = connector.search_indicators("self-harm")
    mental_health = connector.search_indicators("mental health")
    assert captured == ["self-harm", "mental health"]
    assert self_harm != mental_health
    assert self_harm[6] == (90813, 21001)


def test_blank_search_text_is_rejected():
    with pytest.raises(ValueError):
        _connector(_csv_handler("")).search_indicators("   ")


def test_year_type_comes_from_metadata_not_from_the_label():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["indicator_ids"] == "90813"
        return httpx.Response(
            200, text=json.dumps({"90813": {"IID": 90813, "YearType": {"Id": 2, "Name": "Financial"}}})
        )

    assert _connector(handler).year_type(90813) == "Financial"


def test_available_area_types_lists_published_levels():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["indicator_id"] == "90813"
        return httpx.Response(
            200,
            text=json.dumps(
                [{"IndicatorId": 90813, "AreaTypeId": 15}, {"IndicatorId": 90813, "AreaTypeId": 502}]
            ),
        )

    assert _connector(handler).available_area_types(90813) == (15, 502)


def test_indicator_ids_are_sent_as_asked():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["indicator_ids"])
        return httpx.Response(200, text=_csv(_row()))

    _connector(handler).observations(indicator_id=90813, year_type="Financial")
    assert seen == ["90813"]


def test_http_error_propagates_rather_than_yielding_an_empty_series():
    """A failed request must not look like an area with no admissions."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(httpx.HTTPStatusError):
        _connector(handler).observations(indicator_id=90813, year_type="Financial")


def test_priority_indicators_cover_the_w02_targets():
    assert PRIORITY_INDICATORS["self_harm_admissions_10_to_24"] == 90813
    assert set(PRIORITY_INDICATORS) >= {"self_harm_admissions_all_ages", "suicide_rate"}


def test_observation_carries_count_and_denominator_for_rate_reconstruction():
    rows = _connector(_csv_handler(_csv(_row()))).observations(
        indicator_id=90813, year_type="Financial"
    )
    row: Observation = rows[0]
    assert row.count == 35241
    assert row.denominator == 9987942
    assert row.period.year_type == "Financial"
