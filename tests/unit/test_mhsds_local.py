"""Tests for the MHSDS local-file reader.

Every test here corresponds to a way MHSDS has been, or could be, misread. The fixtures are
built from real row shapes taken out of the June 2026 archive - including the two genuinely
odd ones (a month-first start date beside a day-first end date, and a rolling-quarter row
sharing a measure id and end date with a monthly one) - because a synthetic fixture that
tidies those away would test a file that does not exist.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from oslt_research.connectors import mhsds_local
from oslt_research.connectors.mhsds_local import (
    MEASURE_NEW_REFERRALS,
    MEASURE_OPEN_REFERRALS,
    MhsdsDataError,
    MhsdsLocalReader,
    MhsdsMonth,
    monthly_window,
)

HEADER = [
    "REPORTING_PERIOD_START",
    "REPORTING_PERIOD_END",
    "STATUS",
    "BREAKDOWN",
    "PRIMARY_LEVEL",
    "PRIMARY_LEVEL_DESCRIPTION",
    "SECONDARY_LEVEL",
    "SECONDARY_LEVEL_DESCRIPTION",
    "MEASURE_ID",
    "MEASURE_NAME",
    "MEASURE_VALUE",
]


def _row(
    start: str,
    end: str,
    *,
    breakdown: str = "England",
    primary: str = "England",
    secondary: str = "NONE",
    measure: str = MEASURE_NEW_REFERRALS,
    name: str = "Referrals starting in RP",
    value: str = "100",
    status: str = "Performance",
) -> list[str]:
    return [
        start,
        end,
        status,
        breakdown,
        primary,
        primary,
        secondary,
        secondary,
        measure,
        name,
        value,
    ]


def _write_csv(path: Path, rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)
    return path


def _write_zip(path: Path, members: dict[str, list[list[str]]]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, rows in members.items():
            buffer = io.StringIO(newline="")
            writer = csv.writer(buffer)
            writer.writerow(HEADER)
            writer.writerows(rows)
            archive.writestr(name, buffer.getvalue())
    return path


def _three_months() -> list[list[str]]:
    return [
        _row("01/04/2026", "30/04/2026", value="462105"),
        _row("01/05/2026", "31/05/2026", value="476278", status="Performance "),
        _row("01/06/2026", "30/06/2026", value="520330"),
    ]


# --------------------------------------------------------------------------------------
# The module must not be able to fetch anything
# --------------------------------------------------------------------------------------


def test_module_imports_no_http_client() -> None:
    """files.digital.nhs.uk disallows automated retrieval; this reader must stay local.

    Asserted against the source text rather than by mocking, because the property that
    matters is that no future edit can add a fetch without this failing.
    """

    source = Path(mhsds_local.__file__).read_text(encoding="utf-8")
    for forbidden in ("import httpx", "import requests", "urllib.request", "http.client"):
        assert forbidden not in source


def test_missing_archive_raises_and_does_not_fetch(tmp_path: Path) -> None:
    reader = MhsdsLocalReader(tmp_path / "absent.zip")
    with pytest.raises(MhsdsDataError, match="never downloads"):
        list(reader.iter_cells())


# --------------------------------------------------------------------------------------
# Periods
# --------------------------------------------------------------------------------------


def test_monthly_window_accepts_day_first_start() -> None:
    month = monthly_window("01/04/2026", "30/04/2026")
    assert month is not None
    assert (month.year, month.month) == (2026, 4)


def test_monthly_window_accepts_month_first_start_from_the_2016_file() -> None:
    """The 2016-2023 CSV writes April 2016 as ``04/01/2016`` beside an end of ``30/04/2016``.

    Read day-first that start is 4 January and the row looks like a four-month window, which
    would silently drop the whole first seven years of the series.
    """

    month = monthly_window("04/01/2016", "30/04/2016")
    assert month is not None
    assert month.label == "2016-04"


def test_monthly_window_rejects_the_rolling_quarter_row() -> None:
    """``MHS32`` also ships as a rolling three-month total with the same end date.

    Its value is roughly three times the monthly one, so admitting it would either duplicate
    a month or replace a monthly count with a quarterly one.
    """

    assert monthly_window("01/04/2026", "30/06/2026") is None
    assert monthly_window("02/01/2022", "30/04/2022") is None


def test_period_end_with_ambiguous_day_is_refused() -> None:
    with pytest.raises(MhsdsDataError, match="also a valid month"):
        monthly_window("01/04/2026", "04/04/2026")


def test_financial_year_labels_are_not_calendar_years() -> None:
    assert MhsdsMonth(2016, 4).financial_year == "2016/17"
    assert MhsdsMonth(2017, 3).financial_year == "2016/17"
    assert MhsdsMonth(2026, 1).financial_year == "2025/26"


def test_month_label_sorts_chronologically() -> None:
    """``Apr 2026`` sorts before ``Jan 2026`` alphabetically; ``2026-04`` does not."""

    labels = sorted(MhsdsMonth(2026, m).label for m in (5, 1, 12, 4))
    assert labels == ["2026-01", "2026-04", "2026-05", "2026-12"]


# --------------------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------------------


def test_reads_a_zip_and_a_bare_csv_alike(tmp_path: Path) -> None:
    zipped = _write_zip(tmp_path / "ts.zip", {"a/one.csv": _three_months()})
    flat = _write_csv(tmp_path / "one.csv", _three_months())
    assert [cell.value for cell in MhsdsLocalReader(zipped).iter_cells()] == [
        462105.0,
        476278.0,
        520330.0,
    ]
    assert len(list(MhsdsLocalReader(flat).iter_cells())) == 3


def test_schema_change_raises_rather_than_selecting_something_else(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("A,B\n1,2\n", encoding="utf-8")
    with pytest.raises(MhsdsDataError, match="schema has changed"):
        list(MhsdsLocalReader(path).iter_cells())


def test_status_whitespace_does_not_split_the_series(tmp_path: Path) -> None:
    """The archive contains ``"Performance "`` beside ``"Performance"``."""

    path = _write_csv(tmp_path / "one.csv", _three_months())
    series = MhsdsLocalReader(path).england_series(with_coverage=False)
    assert series.statuses_observed == ("Performance",)
    assert len(series.cells) == 3


# --------------------------------------------------------------------------------------
# NON-NEGOTIABLE RULE 1: a suppressed cell is missing, never zero
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("marker", ["*", ".", "c", "z", "", "  "])
def test_suppression_markers_are_missing_not_zero(tmp_path: Path, marker: str) -> None:
    rows = _three_months()
    rows[1][-1] = marker
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series(with_coverage=False)
    assert series.missing_months == ("2026-05",)
    with pytest.raises(MhsdsDataError, match="MISSING, never 0"):
        series.to_observed_series()


def test_a_published_zero_is_a_real_observation(tmp_path: Path) -> None:
    rows = _three_months()
    rows[1][-1] = "0"
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series(with_coverage=False)
    assert series.missing_months == ()
    assert series.to_observed_series().values[1] == 0.0


# --------------------------------------------------------------------------------------
# NON-NEGOTIABLE RULE 2: never sum across nesting levels
# --------------------------------------------------------------------------------------


def test_provider_and_icb_rows_never_enter_the_england_series(tmp_path: Path) -> None:
    rows = _three_months() + [
        _row("01/04/2026", "30/04/2026", breakdown="Provider", primary="RX2", value="9999"),
        _row(
            "01/04/2026",
            "30/04/2026",
            breakdown="ICB - GP Practice or Residence",
            primary="00L",
            value="8888",
        ),
    ]
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series(with_coverage=False)
    assert series.to_observed_series().values == (462105.0, 476278.0, 520330.0)


def test_mixed_strata_are_refused(tmp_path: Path) -> None:
    path = _write_csv(tmp_path / "one.csv", _three_months())
    reader = MhsdsLocalReader(path)
    england = reader.england_series(with_coverage=False)
    mixed = mhsds_local.MhsdsSeries(
        measure_id=MEASURE_NEW_REFERRALS,
        breakdown="England",
        primary_level="England",
        secondary_level="NONE",
        cells=england.cells
        + (
            mhsds_local.MhsdsCell(
                measure_id=MEASURE_NEW_REFERRALS,
                measure_name="Referrals starting in RP",
                breakdown="England; Age",
                primary_level="England",
                primary_level_description="England",
                secondary_level="16",
                secondary_level_description="16",
                status="Performance",
                month=MhsdsMonth(2026, 7),
                value=5.0,
                raw_value="5",
            ),
        ),
    )
    with pytest.raises(MhsdsDataError, match="spans 2 strata"):
        mixed.to_observed_series()


def test_age_band_is_a_separate_stratum_not_a_subset(tmp_path: Path) -> None:
    rows = _three_months() + [
        _row(
            "01/04/2026",
            "30/04/2026",
            breakdown="England; Age",
            secondary="16",
            value="1234",
        ),
    ]
    path = _write_csv(tmp_path / "one.csv", rows)
    reader = MhsdsLocalReader(path)
    banded = reader.england_series(age_band="16", with_coverage=False)
    assert [cell.value for cell in banded.cells] == [1234.0]
    assert reader.available_age_bands() == {"16"}


def test_duplicate_month_is_refused(tmp_path: Path) -> None:
    rows = _three_months() + [_row("01/05/2026", "31/05/2026", value="999")]
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series(with_coverage=False)
    with pytest.raises(MhsdsDataError, match="more than one row for month"):
        series.to_observed_series()


# --------------------------------------------------------------------------------------
# NON-NEGOTIABLE RULE 5: a missing month leaves the series incomplete, never zero
# --------------------------------------------------------------------------------------


def test_gap_in_months_is_refused(tmp_path: Path) -> None:
    rows = [
        _row("01/04/2026", "30/04/2026", value="1"),
        _row("01/06/2026", "30/06/2026", value="3"),
    ]
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series(with_coverage=False)
    with pytest.raises(MhsdsDataError, match="no row for month\\(s\\) 2026-05"):
        series.to_observed_series()


def test_empty_selection_is_refused(tmp_path: Path) -> None:
    path = _write_csv(tmp_path / "one.csv", _three_months())
    series = MhsdsLocalReader(path).england_series(MEASURE_OPEN_REFERRALS, with_coverage=False)
    with pytest.raises(MhsdsDataError, match="nothing to calibrate"):
        series.to_observed_series()


# --------------------------------------------------------------------------------------
# NON-NEGOTIABLE RULE 4: coverage travels with the series
# --------------------------------------------------------------------------------------


def test_coverage_is_counted_per_month_and_warns_on_a_ramp(tmp_path: Path) -> None:
    rows = _three_months()
    for month_start, month_end, providers in (
        ("01/04/2026", "30/04/2026", ["RX2"]),
        ("01/05/2026", "31/05/2026", ["RX2", "RW1"]),
        ("01/06/2026", "30/06/2026", ["RX2", "RW1", "RDY", "APX"]),
    ):
        for code in providers:
            rows.append(
                _row(month_start, month_end, breakdown="Provider", primary=code, value="10")
            )
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series()
    assert series.coverage_by_month == {"2026-04": 1, "2026-05": 2, "2026-06": 4}
    warning = series.coverage_warning
    assert warning is not None
    assert "4.00x" in warning
    assert "ascertainment rather than incidence" in warning


def test_month_without_provider_rows_has_unknown_coverage_not_zero(tmp_path: Path) -> None:
    rows = _three_months() + [
        _row("01/05/2026", "31/05/2026", breakdown="Provider", primary="RX2", value="10"),
    ]
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series()
    assert series.coverage_by_month["2026-04"] is None
    assert series.coverage_by_month["2026-05"] == 1


# --------------------------------------------------------------------------------------
# Definition drift and the finished artefact
# --------------------------------------------------------------------------------------


def test_measure_rename_does_not_split_the_series_but_is_reported(tmp_path: Path) -> None:
    """NHS England renamed MHS01 partway through the series; the id is what pins it."""

    rows = [
        _row(
            "04/01/2016",
            "30/04/2016",
            measure=MEASURE_OPEN_REFERRALS,
            name="People in contact with services at the end of the RP",
            value="1168537",
            status="Final",
        ),
        _row(
            "05/01/2016",
            "31/05/2016",
            measure=MEASURE_OPEN_REFERRALS,
            name="People with an open referral with services at the end of the RP",
            value="1212724",
            status="Final",
        ),
        _row(
            "06/01/2016",
            "30/06/2016",
            measure=MEASURE_OPEN_REFERRALS,
            name="People with an open referral with services at the end of the RP",
            value="1278433",
            status="Final",
        ),
    ]
    path = _write_csv(tmp_path / "one.csv", rows)
    series = MhsdsLocalReader(path).england_series(MEASURE_OPEN_REFERRALS, with_coverage=False)
    assert len(series.measure_names_observed) == 2
    observed = series.to_observed_series()
    assert observed.periods == ("2016-04", "2016-05", "2016-06")


def test_observed_series_carries_source_id_and_month_labels(tmp_path: Path) -> None:
    zipped = _write_zip(tmp_path / "ts.zip", {"a/one.csv": _three_months()})
    series = MhsdsLocalReader(zipped).england_series(with_coverage=False)
    observed = series.to_observed_series()
    assert observed.source_id == "DS077"
    assert observed.periods == ("2026-04", "2026-05", "2026-06")
    assert observed.values == (462105.0, 476278.0, 520330.0)
    assert series.financial_years == ("2026/27", "2026/27", "2026/27")


def test_available_measures_reports_every_name_seen(tmp_path: Path) -> None:
    rows = [
        _row("01/04/2026", "30/04/2026", measure="MHS01", name="Old name", value="1"),
        _row("01/05/2026", "31/05/2026", measure="MHS01", name="New name", value="2"),
    ]
    path = _write_csv(tmp_path / "one.csv", rows)
    assert MhsdsLocalReader(path).available_measures()["MHS01"] == {"Old name", "New name"}
