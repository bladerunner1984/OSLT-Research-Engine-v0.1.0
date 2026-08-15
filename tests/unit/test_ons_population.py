from __future__ import annotations

import io

import pytest

from oslt_research.connectors.ons_population import OnsPopulationConnector, PopulationSlice

HEADER = "v4_0,calendar-years,Time,administrative-geography,Geography,sex,Sex,single-year-of-age,Age"


def csv_rows(*rows: str) -> io.StringIO:
    return io.StringIO("\n".join([HEADER, *rows]))


def row(value, year, geography="Leeds", sex="all", age="total") -> str:
    return f"{value},{year},{year},E08000035,{geography},{sex},{sex.title()},{age},{age}"


def connector() -> OnsPopulationConnector:
    return OnsPopulationConnector()


# ------------------------------------------- the overlapping-aggregate trap


def test_unfiltered_uses_the_published_total_not_a_sum_of_parts():
    """male + female + 'all' would count the population twice."""

    source = csv_rows(
        row(100, 2001, sex="male"), row(120, 2001, sex="female"), row(220, 2001, sex="all"),
    )
    result = connector().slice_population(source, geography="Leeds")
    assert result.by_year[2001] == 220


def test_unfiltered_ignores_single_year_rows():
    """Summing single years alongside the 'total' row inflates the figure."""

    source = csv_rows(
        row(220, 2001, age="total"), row(10, 2001, age="5"), row(12, 2001, age="6"),
    )
    assert connector().slice_population(source, geography="Leeds").by_year[2001] == 220


def test_age_band_sums_single_years_and_excludes_the_total_row():
    source = csv_rows(
        row(999, 2001, sex="female", age="total"),
        row(10, 2001, sex="female", age="10"),
        row(12, 2001, sex="female", age="11"),
        row(14, 2001, sex="female", age="40"),
    )
    result = connector().slice_population(
        source, geography="Leeds", sex="female", age_from=10, age_to=11
    )
    assert result.by_year[2001] == 22


def test_open_ended_band_is_included_only_when_the_range_reaches_it():
    source = csv_rows(row(50, 2001, age="90+"), row(5, 2001, age="20"))

    excluded = connector().slice_population(source, geography="Leeds", age_from=0, age_to=30)
    assert excluded.by_year[2001] == 5

    source.seek(0)
    included = connector().slice_population(source, geography="Leeds", age_from=0)
    assert included.by_year[2001] == 55


def test_a_sex_filter_selects_only_that_sex():
    source = csv_rows(
        row(100, 2001, sex="male"), row(120, 2001, sex="female"), row(220, 2001, sex="all"),
    )
    assert connector().slice_population(source, geography="Leeds", sex="female").by_year[2001] == 120


def test_geography_is_matched_by_name_not_code():
    """Codes change between editions when boundaries are redrawn; names are stable."""

    source = csv_rows(row(220, 2001, geography="Leeds"), row(999, 2001, geography="Bradford"))
    assert connector().slice_population(source, geography="Leeds").by_year[2001] == 220


def test_geography_match_is_case_insensitive():
    source = csv_rows(row(220, 2001, geography="Leeds"))
    assert connector().slice_population(source, geography="leeds").by_year[2001] == 220


# ----------------------------------------------------------- series safety


def test_series_needs_at_least_three_years():
    with pytest.raises(ValueError, match="at least three years"):
        PopulationSlice("Leeds", None, None, None, {2001: 1, 2002: 2}).to_observed_series()


def test_a_gap_in_the_years_is_refused_not_interpolated():
    """A missing year is not a population of zero."""

    with pytest.raises(ValueError, match="gaps at"):
        PopulationSlice(
            "Leeds", None, None, None, {2001: 1, 2002: 2, 2004: 4}
        ).to_observed_series()


def test_contiguous_years_convert_to_an_observed_series():
    observed = PopulationSlice(
        "Leeds", "female", 10, 17, {2001: 10, 2002: 11, 2003: 12}
    ).to_observed_series()
    assert observed.values == (10.0, 11.0, 12.0)
    assert observed.periods == ("2001", "2002", "2003")
    assert "female" in observed.name and "10-17" in observed.name


def test_unparseable_rows_are_skipped_rather_than_counted_as_zero():
    source = csv_rows(row(220, 2001), row("not-a-number", 2002))
    result = connector().slice_population(source, geography="Leeds")
    assert result.by_year == {2001: 220}
