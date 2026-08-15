"""Tests for the NOMIS connector.

The behaviours asserted here are the ones that have actually gone wrong in this project:
overlapping aggregates summed into a multiple of the truth, a hole coerced to a zero, a
query parameter the API quietly ignored, a date-looking field that measured something
else, and a silently capped response accepted as complete.

All fixtures are shaped from real NOMIS payloads captured live on 2026-08-16. No test
touches the network - every request goes through ``httpx.MockTransport``.
"""

from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.nomis import (
    CENSUS_GENDER_IDENTITY_DATASETS,
    GEOGRAPHY_ENGLAND,
    GEOGRAPHY_ENGLAND_AND_WALES,
    MEASURE_VALUE,
    POPULATION_SINGLE_YEAR,
    SOURCE_ID,
    TS070_DIMENSION,
    TS070_TOTAL_CODE,
    CodeValue,
    DatePeriod,
    DatasetSummary,
    NomisConnector,
    NomisError,
    Observation,
    Series,
    _parse_number,
)

TS070 = CENSUS_GENDER_IDENTITY_DATASETS["TS070"]


# -- fixtures -------------------------------------------------------------------


def _connector(handler, **kwargs) -> NomisConnector:
    """A connector wired to a mock transport, with throttling neutralised for speed."""

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://x")
    kwargs.setdefault("min_interval_seconds", 0.0)
    return NomisConnector(client=client, **kwargs)


def _dataset_list(*families: tuple[str, str]) -> dict:
    return {
        "structure": {
            "keyfamilies": {
                "keyfamily": [
                    {"id": ident, "name": {"value": name}} for ident, name in families
                ]
            }
        }
    }


def _definition(*conceptrefs: str) -> dict:
    dimensions: list[dict] = [
        {"codelist": f"CL_X_{ref.upper()}", "conceptref": ref.upper()} for ref in conceptrefs
    ]
    dimensions.append(
        {"codelist": "CL_X_FREQ", "conceptref": "FREQ", "isfrequencydimension": "true"}
    )
    return {
        "structure": {
            "keyfamilies": {"keyfamily": [{"components": {"dimension": dimensions}}]}
        }
    }


def _codelist(*codes: tuple[str, str, str | None]) -> dict:
    entries = []
    for value, description, parent in codes:
        entry: dict = {"value": value, "description": {"value": description}}
        if parent is not None:
            entry["parentcode"] = parent
        entries.append(entry)
    return {"structure": {"codelists": {"codelist": [{"code": entries}]}}}


def _obs(
    *,
    period: str = "2021",
    value: float | None = 56554891,
    status: tuple[str, str] = ("A", "Normal Value"),
    geography: str = "England",
    geogcode: str = "E92000001",
    dimensions: dict[str, str] | None = None,
) -> dict:
    row: dict = {
        "geography": {"value": 2092957699, "description": geography, "geogcode": geogcode},
        "measures": {"value": MEASURE_VALUE, "description": "Value"},
        "time": {"value": period, "description": period},
        "obs_value": {"value": value},
        "obs_status": {"value": status[0], "description": status[1]},
    }
    for key, description in (dimensions or {}).items():
        row[key] = {"value": 0, "description": description}
    return row


def _data(*rows: dict, truncated: str = "false") -> dict:
    return {"header": {"truncated": truncated, "source": "ONS"}, "obs": list(rows)}


def _population_handler(rows: list[dict], *, truncated: str = "false", record: list | None = None):
    """Serve the population dataset's definition plus a data payload."""

    def handler(request: httpx.Request) -> httpx.Response:
        if record is not None:
            record.append(request.url)
        if request.url.path.endswith(".def.sdmx.json"):
            return httpx.Response(200, json=_definition("geography", "gender", "c_age", "measures"))
        if ".data.json" in request.url.path:
            return httpx.Response(200, json=_data(*rows, truncated=truncated))
        raise AssertionError(f"unexpected request {request.url}")

    return handler


# -- dataset discovery ----------------------------------------------------------


def test_dataset_list_is_parsed_into_summaries() -> None:
    handler = lambda request: httpx.Response(  # noqa: E731
        200, json=_dataset_list((TS070, "TS070 - Gender identity (detailed)"))
    )
    datasets = _connector(handler).list_datasets()
    assert datasets == (
        DatasetSummary(dataset_id=TS070, name="TS070 - Gender identity (detailed)"),
    )


def test_search_term_is_actually_sent_to_the_api() -> None:
    """Two connectors shipped a parameter their API discarded. Assert ours is sent."""

    seen: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params.get("search"))
        return httpx.Response(200, json=_dataset_list((TS070, "TS070 - Gender identity")))

    connector = _connector(handler)
    connector.list_datasets("*gender identity*")
    connector.list_datasets("*population estimates*")
    assert seen == ["*gender identity*", "*population estimates*"]


def test_blank_search_is_refused_rather_than_sent_as_no_filter() -> None:
    handler = lambda request: httpx.Response(200, json=_dataset_list())  # noqa: E731
    with pytest.raises(ValueError):
        _connector(handler).list_datasets("   ")


def test_census_table_code_is_read_from_the_name_not_the_nomis_id() -> None:
    assert DatasetSummary(TS070, "TS070 - Gender identity (detailed)").census_table == "TS070"
    assert DatasetSummary("NM_2263_1", "RM163 - Gender identity by age by sex").census_table == "RM163"
    assert DatasetSummary("NM_2002_1", "Population estimates - by age").census_table is None


def test_gender_identity_datasets_are_registered_by_ons_table_code() -> None:
    """Census 2021 gender identity is the only national enumeration available to W01."""

    assert CENSUS_GENDER_IDENTITY_DATASETS["TS070"] == "NM_2087_1"
    assert CENSUS_GENDER_IDENTITY_DATASETS["TS078"] == "NM_2061_1"
    assert all(value.startswith("NM_") for value in CENSUS_GENDER_IDENTITY_DATASETS.values())


# -- dimension enumeration ------------------------------------------------------


def test_dimension_keys_come_from_conceptrefs_not_display_names() -> None:
    """The population age dimension displays as "Age" and must be queried as ``c_age``."""

    handler = lambda request: httpx.Response(  # noqa: E731
        200, json=_definition("geography", "gender", "c_age", "measures")
    )
    keys = _connector(handler).dimension_keys(POPULATION_SINGLE_YEAR)
    assert keys == ("geography", "gender", "c_age", "measures")
    assert "age" not in keys


def test_frequency_dimension_is_excluded_from_the_keys() -> None:
    handler = lambda request: httpx.Response(200, json=_definition("geography", "measures"))  # noqa: E731
    assert "freq" not in _connector(handler).dimension_keys(TS070)


def test_selectable_dimensions_drop_the_separately_handled_axes() -> None:
    handler = lambda request: httpx.Response(  # noqa: E731
        200, json=_definition("geography", "gender", "c_age", "measures")
    )
    assert _connector(handler).selectable_dimensions(POPULATION_SINGLE_YEAR) == ("gender", "c_age")


def test_unknown_dataset_raises_rather_than_returning_nothing() -> None:
    handler = lambda request: httpx.Response(  # noqa: E731
        200, json={"structure": {"keyfamilies": {"keyfamily": []}}}
    )
    with pytest.raises(NomisError, match="no such dataset"):
        _connector(handler).dimension_keys("NM_9999_9")


def test_ts070_categories_expose_the_total_alongside_its_own_parts() -> None:
    """Code 0 is a Total in the same codelist as the seven categories it sums."""

    handler = lambda request: httpx.Response(  # noqa: E731
        200,
        json=_codelist(
            ("0", "Total: All usual residents aged 16 years and over", None),
            ("3", "Trans woman", None),
            ("4", "Trans man", None),
            ("5", "Non-binary", None),
        ),
    )
    values = _connector(handler).dimension_values(TS070, TS070_DIMENSION)
    assert values[0].value == str(TS070_TOTAL_CODE)
    assert values[0].description.startswith("Total")
    assert len(values) == 4


def test_geography_nesting_is_preserved_so_levels_are_not_mistaken_for_partitions() -> None:
    """The twelve regions include Wales, Scotland and NI, so they do not partition England."""

    handler = lambda request: httpx.Response(  # noqa: E731
        200,
        json=_codelist(
            ("2013265921", "North East", "2092957699"),
            ("2013265927", "London", "2092957699"),
            ("2013265930", "Wales", "2092957700"),
            ("2013265932", "Northern Ireland", "2092957702"),
        ),
    )
    regions = _connector(handler).geographies(POPULATION_SINGLE_YEAR, "TYPE480")
    assert all(region.is_nested for region in regions)
    assert {region.parent_code for region in regions} != {str(GEOGRAPHY_ENGLAND)}


def test_country_codelist_is_flagged_as_overlapping_not_a_partition() -> None:
    handler = lambda request: httpx.Response(  # noqa: E731
        200,
        json=_codelist(
            ("2092957697", "United Kingdom", None),
            ("2092957699", "England", None),
            ("2092957703", "England and Wales", None),
        ),
    )
    countries = _connector(handler).geographies(POPULATION_SINGLE_YEAR, "TYPE499")
    # NOMIS reports no parent here even though UK contains England and Wales contains
    # England, which is exactly why nothing in this connector ever sums a codelist.
    assert not any(country.is_nested for country in countries)
    assert CodeValue("2092957699", "England").is_nested is False


def test_missing_codelist_raises_rather_than_returning_an_empty_selection() -> None:
    handler = lambda request: httpx.Response(200, json={"structure": {"codelists": {}}})  # noqa: E731
    with pytest.raises(NomisError, match="no codelist"):
        _connector(handler).dimension_values(TS070, "c2021_nonesuch")


# -- date semantics -------------------------------------------------------------


def test_date_codes_are_read_from_the_overview_with_their_labels() -> None:
    handler = lambda request: httpx.Response(  # noqa: E731
        200,
        json={
            "overview": {
                "dimensions": {
                    "dimension": [
                        {
                            "name": "date",
                            "codes": {
                                "code": [
                                    {"value": "2025-06", "name": "Jul 2024-Jun 2025"},
                                    {"value": "2025-09", "name": "Oct 2024-Sep 2025"},
                                ]
                            },
                        }
                    ]
                }
            }
        },
    )
    codes = _connector(handler).date_codes("NM_17_1")
    assert [code.code for code in codes] == ["2025-06", "2025-09"]
    assert codes[0].label == "Jul 2024-Jun 2025"


def test_a_single_date_code_delivered_as_an_object_is_still_enumerated() -> None:
    """Census datasets publish one date, and NOMIS then emits a dict, not a list."""

    handler = lambda request: httpx.Response(  # noqa: E731
        200,
        json={
            "overview": {
                "dimensions": {
                    "dimension": [
                        {"name": "date", "codes": {"code": {"value": 2021, "name": 2021}}}
                    ]
                }
            }
        },
    )
    assert _connector(handler).date_codes(TS070) == (DatePeriod(code="2021", label="2021"),)


def test_rolling_window_codes_are_not_treated_as_calendar_years() -> None:
    """``2025-06`` means Jul 2024-Jun 2025, not June 2025 and not 2025."""

    rolling = DatePeriod(code="2025-06", label="Jul 2024-Jun 2025")
    assert rolling.is_rolling
    assert rolling.overlaps_neighbours
    assert rolling.end_year == 2025  # the year the window ENDS, not the year measured


def test_plain_year_codes_are_not_flagged_as_overlapping() -> None:
    annual = DatePeriod(code="2021", label="2021")
    assert not annual.is_rolling
    assert not annual.overlaps_neighbours
    assert annual.end_year == 2021


def test_a_non_numeric_date_code_yields_no_year_rather_than_a_guess() -> None:
    assert DatePeriod(code="latest", label="latest").end_year is None


# -- data retrieval and pinning -------------------------------------------------


def test_unpinned_dimension_is_refused_because_nomis_defaults_it_to_everything() -> None:
    """A bare England/2021 call returns 726 rows; the omission is the bug, not the query."""

    connector = _connector(_population_handler([_obs()]))
    with pytest.raises(NomisError, match="unpinned dimensions"):
        connector.observations(
            POPULATION_SINGLE_YEAR,
            geography=GEOGRAPHY_ENGLAND,
            dates=["2021"],
            dimensions={"gender": 0},
        )


def test_unknown_dimension_key_is_refused_rather_than_silently_returning_no_rows() -> None:
    connector = _connector(_population_handler([_obs()]))
    with pytest.raises(NomisError, match="not part of"):
        connector.observations(
            POPULATION_SINGLE_YEAR,
            geography=GEOGRAPHY_ENGLAND,
            dates=["2021"],
            dimensions={"gender": 0, "c_age": 200, "age": 200},
        )


def test_empty_dates_are_refused() -> None:
    connector = _connector(_population_handler([_obs()]))
    with pytest.raises(ValueError, match="dates must not be empty"):
        connector.observations(
            POPULATION_SINGLE_YEAR,
            geography=GEOGRAPHY_ENGLAND,
            dates=[],
            dimensions={"gender": 0, "c_age": 200},
        )


def test_all_pinned_dimensions_reach_the_wire() -> None:
    seen: list[httpx.URL] = []
    connector = _connector(_population_handler([_obs()], record=seen))
    connector.observations(
        POPULATION_SINGLE_YEAR,
        geography=GEOGRAPHY_ENGLAND,
        dates=["2020", "2021"],
        dimensions={"gender": 0, "C_AGE": 200},
    )
    data_url = [url for url in seen if ".data.json" in url.path][0]
    assert data_url.params["geography"] == str(GEOGRAPHY_ENGLAND)
    assert data_url.params["date"] == "2020,2021"
    assert data_url.params["gender"] == "0"
    assert data_url.params["c_age"] == "200"  # lower-cased, as the API requires
    assert data_url.params["measures"] == str(MEASURE_VALUE)


def test_truncated_response_raises_instead_of_passing_off_a_prefix_as_the_answer() -> None:
    connector = _connector(_population_handler([_obs()], truncated="true"))
    with pytest.raises(NomisError, match="truncated"):
        connector.observations(
            POPULATION_SINGLE_YEAR,
            geography="TYPE434",
            dates=["2021"],
            dimensions={"gender": 0, "c_age": 200},
        )


def test_observation_carries_geography_code_period_and_stratum() -> None:
    connector = _connector(
        _population_handler([_obs(dimensions={"gender": "Total", "c_age": "All Ages"})])
    )
    (observation,) = connector.observations(
        POPULATION_SINGLE_YEAR,
        geography=GEOGRAPHY_ENGLAND,
        dates=["2021"],
        dimensions={"gender": 0, "c_age": 200},
    )
    assert observation.geography_code == "E92000001"
    assert observation.period.code == "2021"
    assert observation.value == 56554891.0
    assert observation.dimensions == {"gender": "Total", "c_age": "All Ages"}
    assert not observation.missing


def test_non_normal_status_becomes_missing_not_a_usable_number() -> None:
    """A disclosure-controlled cell is not a published figure even if a number appears."""

    connector = _connector(
        _population_handler([_obs(value=0, status=("Q", "Value suppressed"))])
    )
    (observation,) = connector.observations(
        POPULATION_SINGLE_YEAR,
        geography=GEOGRAPHY_ENGLAND,
        dates=["2021"],
        dimensions={"gender": 0, "c_age": 200},
    )
    assert observation.missing
    assert observation.value is None
    assert observation.status == "Value suppressed"


def test_null_value_is_missing_rather_than_zero() -> None:
    connector = _connector(_population_handler([_obs(value=None)]))
    (observation,) = connector.observations(
        POPULATION_SINGLE_YEAR,
        geography=GEOGRAPHY_ENGLAND,
        dates=["2021"],
        dimensions={"gender": 0, "c_age": 200},
    )
    assert observation.missing


# -- series construction --------------------------------------------------------


def _population_series_connector(values: dict[str, float | None], **kwargs) -> NomisConnector:
    rows = [
        _obs(period=period, value=value, dimensions={"gender": "Total", "c_age": "All Ages"})
        for period, value in values.items()
    ]
    return _connector(_population_handler(rows, **kwargs))


REAL_ENGLAND_SERIES: dict[str, float | None] = {
    "2015": 54808676,
    "2016": 55289034,
    "2017": 55619548,
    "2018": 55924528,
    "2019": 56230056,
    "2020": 56325961,
    "2021": 56554891,
    "2022": 57189701,
    "2023": 57990791,
}


def test_series_returns_one_row_per_requested_period_in_order() -> None:
    connector = _population_series_connector(REAL_ENGLAND_SERIES)
    series = connector.series(
        POPULATION_SINGLE_YEAR,
        geography=GEOGRAPHY_ENGLAND,
        dates=list(REAL_ENGLAND_SERIES),
        dimensions={"gender": 0, "c_age": 200},
    )
    assert [item.period.code for item in series.observations] == list(REAL_ENGLAND_SERIES)
    assert series.complete
    assert series.geography_name == "England"


def test_series_refuses_when_a_period_returns_more_than_one_row() -> None:
    """Two rows for one period means a total is sitting beside its own parts."""

    rows = [
        _obs(period="2021", value=56554891, dimensions={"c_age": "All Ages"}),
        _obs(period="2021", value=10_000_000, dimensions={"c_age": "Aged 0 to 15"}),
        _obs(period="2022", value=57189701, dimensions={"c_age": "All Ages"}),
    ]
    connector = _connector(_population_handler(rows))
    with pytest.raises(NomisError, match="not a single stratum"):
        connector.series(
            POPULATION_SINGLE_YEAR,
            geography=GEOGRAPHY_ENGLAND,
            dates=["2021", "2022"],
            dimensions={"gender": 0, "c_age": 200},
        )


def test_series_refuses_when_a_requested_period_is_absent() -> None:
    connector = _population_series_connector({"2019": 56230056.0, "2021": 56554891.0})
    with pytest.raises(NomisError, match="missing data, not a"):
        connector.series(
            POPULATION_SINGLE_YEAR,
            geography=GEOGRAPHY_ENGLAND,
            dates=["2019", "2020", "2021"],
            dimensions={"gender": 0, "c_age": 200},
        )


def test_series_name_records_the_stratum_it_pinned() -> None:
    connector = _population_series_connector(REAL_ENGLAND_SERIES)
    series = connector.series(
        POPULATION_SINGLE_YEAR,
        geography=GEOGRAPHY_ENGLAND,
        dates=list(REAL_ENGLAND_SERIES),
        dimensions={"gender": 0, "c_age": 200},
    )
    assert "England" in series.name
    assert "All Ages" in series.name
    assert "Total" in series.name


# -- ObservedSeries conversion --------------------------------------------------


def test_observed_series_carries_the_real_england_population_and_source_id() -> None:
    connector = _population_series_connector(REAL_ENGLAND_SERIES)
    observed = connector.series(
        POPULATION_SINGLE_YEAR,
        geography=GEOGRAPHY_ENGLAND,
        dates=list(REAL_ENGLAND_SERIES),
        dimensions={"gender": 0, "c_age": 200},
    ).observed()
    assert observed.source_id == SOURCE_ID == "UNREGISTERED:NOMIS"
    assert observed.periods == tuple(REAL_ENGLAND_SERIES)
    assert observed.values[6] == 56554891.0  # 2021, matching the ons_population CSV route
    assert len(observed.values) == len(observed.periods)


def _series_of(*observations: Observation) -> Series:
    return Series(
        dataset_id=POPULATION_SINGLE_YEAR,
        name="test",
        geography_name="England",
        observations=observations,
    )


def _observation(period: str, value: float | None) -> Observation:
    return Observation(
        dataset_id=POPULATION_SINGLE_YEAR,
        geography_code="E92000001",
        geography_name="England",
        period=DatePeriod(code=period, label=period),
        measure="Value",
        value=value,
    )


def test_a_hole_refuses_to_become_a_calibration_target() -> None:
    series = _series_of(
        _observation("2019", 56230056.0),
        _observation("2020", None),
        _observation("2021", 56554891.0),
    )
    with pytest.raises(NomisError, match="not a zero"):
        series.observed()
    assert series.missing_periods == ("2020",)


def test_an_empty_series_refuses_rather_than_producing_nothing_quietly() -> None:
    with pytest.raises(NomisError, match="nothing to calibrate"):
        _series_of().observed()


def test_rolling_periods_refuse_unless_the_overlap_is_acknowledged() -> None:
    series = _series_of(
        _observation("2024-12", 100.0),
        _observation("2025-03", 101.0),
        _observation("2025-06", 102.0),
    )
    assert series.overlapping
    with pytest.raises(NomisError, match="not independent observations"):
        series.observed()
    allowed = series.observed(allow_overlapping_periods=True)
    assert allowed.periods == ("2024-12", "2025-03", "2025-06")


# -- census 2021 gender identity ------------------------------------------------


def test_ts070_gender_identity_series_is_retrievable_for_england_and_wales() -> None:
    """The published TS070 figures, which this connector reproduced live."""

    published = {
        "Trans woman": 47572,
        "Trans man": 48435,
        "Non-binary": 30257,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".def.sdmx.json"):
            return httpx.Response(
                200, json=_definition("geography", TS070_DIMENSION, "measures")
            )
        rows = [
            _obs(
                period="2021",
                value=value,
                geography="England and Wales",
                geogcode="K04000001",
                dimensions={TS070_DIMENSION: label},
            )
            for label, value in published.items()
        ]
        return httpx.Response(200, json=_data(*rows))

    observations = _connector(handler).observations(
        TS070,
        geography=GEOGRAPHY_ENGLAND_AND_WALES,
        dates=["2021"],
        dimensions={TS070_DIMENSION: "3,4,5"},
    )
    assert [item.value for item in observations] == [47572.0, 48435.0, 30257.0]
    assert all(item.geography_code == "K04000001" for item in observations)
    # The categories are NOT summed here, and none of them is the Total in code 0.
    assert TS070_TOTAL_CODE == 0


# -- helpers --------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        (56554891, 56554891.0),
        ("56554891", 56554891.0),
        (None, None),
        ("", None),
        ("-", None),
        (":", None),
        ("not a number", None),
        (True, None),
    ],
)
def test_parse_number_treats_every_non_number_as_missing(raw, expected) -> None:
    assert _parse_number(raw) == expected
