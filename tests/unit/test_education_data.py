"""Tests for the DfE Explore Education Statistics connector.

The payload shapes below are trimmed copies of real responses from
``https://api.education.gov.uk/statistics`` (publication ``Pupil absence in schools in
England``, data set ``Absence for persistent and severe absentees``), including its real
quirks: the missing ``2019/2020`` academic year and the literal ``"z"`` cell value.
All network traffic is stubbed with ``httpx.MockTransport``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from oslt_research.connectors.education_data import (
    DATE_FIELD_SEMANTICS,
    DOCUMENT_ROWS_COVERED_ELSEWHERE,
    SOURCE_ID,
    DataSetMeta,
    EducationDataConnector,
    EducationSeries,
    QueryNotHonouredError,
    SeriesPoint,
    parse_cell,
)

FILTER_ABSENCE = "qYfzj"
FILTER_SCHOOL = "uWLso"
INDICATOR = "TuAuP"

DECLARED_PERIODS = ["2021/2022", "2022/2023", "2023/2024", "2024/2025"]


def meta_payload(periods: list[str] | None = None) -> dict[str, Any]:
    return {
        "timePeriods": [
            {"code": "AY", "period": period, "label": period.replace("/20", "/")}
            for period in (periods if periods is not None else DECLARED_PERIODS)
        ],
        "indicators": [
            {
                "id": INDICATOR,
                "column": "enrolment_percent",
                "label": "Percentage of pupil enrolments",
            }
        ],
        "filters": [
            {
                "id": "daL0Z",
                "label": "Absence type",
                "options": [{"id": FILTER_ABSENCE, "label": "Persistent absence"}],
            },
            {
                "id": "OS5CL",
                "label": "School type",
                "options": [{"id": FILTER_SCHOOL, "label": "State-funded secondary"}],
            },
        ],
        "geographicLevels": [{"code": "NAT", "label": "National"}],
    }


def row(period: str, value: Any, *, filters: dict[str, str] | None = None, level: str = "NAT",
        code: str = "AY") -> dict[str, Any]:
    return {
        "timePeriod": {"code": code, "period": period},
        "geographicLevel": level,
        "locations": {"NAT": "dP0Zw"},
        "filters": filters or {"OS5CL": FILTER_SCHOOL, "daL0Z": FILTER_ABSENCE},
        "values": {INDICATOR: value},
    }


def query_payload(rows: list[dict[str, Any]], *, warnings: list[Any] | None = None,
                  total_pages: int = 1, page: int = 1) -> dict[str, Any]:
    return {
        "warnings": warnings or [],
        "paging": {"page": page, "pageSize": 200, "totalResults": len(rows),
                   "totalPages": total_pages},
        "results": rows,
    }


def connector_with(handler) -> EducationDataConnector:
    return EducationDataConnector(
        client=httpx.Client(transport=httpx.MockTransport(handler)), min_interval_seconds=0.0
    )


def routing_connector(
    *,
    meta: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    publications: dict[str, Any] | None = None,
    data_sets: dict[str, Any] | None = None,
    recorder: list[httpx.Request] | None = None,
) -> EducationDataConnector:
    def handler(request: httpx.Request) -> httpx.Response:
        if recorder is not None:
            recorder.append(request)
        path = request.url.path
        if path.endswith("/meta"):
            return httpx.Response(200, json=meta or meta_payload())
        if path.endswith("/query"):
            return httpx.Response(200, json=query or query_payload([]))
        if path.endswith("/data-sets"):
            return httpx.Response(200, json=data_sets or {"paging": {}, "results": []})
        return httpx.Response(200, json=publications or {"paging": {}, "results": []})

    return connector_with(handler)


# -- catalogue -----------------------------------------------------------------


def test_publications_are_parsed_with_release_date_kept_separate_from_coverage():
    payload = {
        "paging": {"page": 1, "pageSize": 2, "totalResults": 1, "totalPages": 1},
        "results": [
            {
                "id": "cbbd299f",
                "title": "Pupil absence in schools in England",
                "slug": "pupil-absence-in-schools-in-england",
                "summary": "Pupil absence...",
                "lastPublished": "2026-08-06T08:30:02+00:00",
            }
        ],
    }
    connector = routing_connector(publications=payload)
    results = connector.list_publications(search="absence")
    assert len(results) == 1
    assert results[0].publication_id == "cbbd299f"
    # lastPublished is a release timestamp, never treated as coverage.
    assert results[0].last_published == "2026-08-06T08:30:02+00:00"


def test_search_term_is_actually_sent_to_the_api():
    seen: list[httpx.Request] = []
    connector = routing_connector(recorder=seen)
    connector.list_publications(search="exclusion")
    assert seen[-1].url.params.get("search") == "exclusion"


def test_search_is_omitted_when_not_requested():
    seen: list[httpx.Request] = []
    connector = routing_connector(recorder=seen)
    connector.list_publications()
    assert "search" not in seen[-1].url.params


def test_data_sets_expose_declared_coverage_and_release_date_as_separate_fields():
    payload = {
        "paging": {"totalPages": 1},
        "results": [
            {
                "id": "019d209c",
                "title": "Absence for persistent and severe absentees",
                "summary": "Persistent and severe absentee enrolments...",
                "status": "Published",
                "latestVersion": {
                    "version": "1.0",
                    "published": "2026-03-26T09:30:42+00:00",
                    "timePeriods": {"start": "2006/07", "end": "2024/25"},
                    "geographicLevels": ["Local authority", "National"],
                    "filters": ["Absence type", "School type"],
                    "indicators": ["Percentage of pupil enrolments"],
                },
            }
        ],
    }
    connector = routing_connector(data_sets=payload)
    summary = connector.list_data_sets("cbbd299f")[0]
    assert summary.published == "2026-03-26T09:30:42+00:00"
    assert (summary.time_period_start, summary.time_period_end) == ("2006/07", "2024/25")
    assert summary.geographic_levels == ("Local authority", "National")


def test_meta_indexes_filter_options_to_their_groups():
    connector = routing_connector()
    meta = connector.data_set_meta("019d209c")
    assert meta.filter_options[FILTER_ABSENCE] == "Persistent absence"
    assert meta.filter_group_of_option[FILTER_ABSENCE] == "daL0Z"
    assert meta.filter_group_of_option[FILTER_SCHOOL] == "OS5CL"
    assert meta.periods_for_code("AY") == tuple(DECLARED_PERIODS)
    assert meta.periods_for_code("CY") == ()


# -- query construction --------------------------------------------------------


def test_each_filter_id_gets_its_own_clause_so_the_api_intersects_rather_than_unions():
    criteria = EducationDataConnector.build_criteria((FILTER_ABSENCE, FILTER_SCHOOL), "NAT")
    filter_clauses = [c for c in criteria["and"] if "filters" in c]
    assert len(filter_clauses) == 2
    assert all(len(c["filters"]["in"]) == 1 for c in filter_clauses)
    assert {"geographicLevels": {"eq": "NAT"}} in criteria["and"]


def test_query_body_is_actually_sent_with_the_requested_indicator_and_filters():
    seen: list[httpx.Request] = []
    connector = routing_connector(
        query=query_payload([row(p, 20.0) for p in DECLARED_PERIODS]), recorder=seen
    )
    connector.query_series(
        "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
    )
    import json

    body = json.loads(seen[-1].content.decode())
    assert body["indicators"] == [INDICATOR]
    assert {"filters": {"in": [FILTER_ABSENCE]}} in body["criteria"]["and"]
    assert {"filters": {"in": [FILTER_SCHOOL]}} in body["criteria"]["and"]


def test_paging_follows_total_pages():
    pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/meta"):
            return httpx.Response(200, json=meta_payload())
        import json

        page = json.loads(request.content.decode())["page"]
        pages.append(page)
        chunk = DECLARED_PERIODS[:2] if page == 1 else DECLARED_PERIODS[2:]
        return httpx.Response(
            200, json=query_payload([row(p, 20.0) for p in chunk], total_pages=2, page=page)
        )

    series = connector_with(handler).query_series(
        "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
    )
    assert pages == [1, 2]
    assert len(series.points) == 4


# -- query-honoured guards -----------------------------------------------------


def test_warnings_are_a_hard_failure_because_the_api_ignored_part_of_the_query():
    warning = {
        "message": "One or more filters could not be found.",
        "code": "FiltersNotFound",
        "detail": {"items": ["ZZZZZ"]},
    }
    connector = routing_connector(query=query_payload([], warnings=[warning]))
    with pytest.raises(QueryNotHonouredError, match="FiltersNotFound"):
        connector.query_series("019d209c", indicator_id=INDICATOR, filter_ids=("ZZZZZ",))


def test_row_outside_the_requested_filter_combination_is_rejected():
    rows = [
        row("2021/2022", 20.0),
        # A union-widened row: right school type, wrong absence type.
        row("2022/2023", 5.0, filters={"OS5CL": FILTER_SCHOOL, "daL0Z": "aKM6L"}),
    ]
    connector = routing_connector(query=query_payload(rows))
    with pytest.raises(QueryNotHonouredError, match="widened"):
        connector.query_series(
            "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
        )


def test_row_from_the_wrong_geography_is_rejected():
    rows = [row("2021/2022", 20.0, level="LA")]
    connector = routing_connector(query=query_payload(rows))
    with pytest.raises(QueryNotHonouredError, match="geographic level"):
        connector.query_series(
            "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
        )


def test_duplicate_period_is_rejected_because_the_filters_do_not_identify_one_series():
    rows = [row("2021/2022", 20.0), row("2021/2022", 21.0)]
    connector = routing_connector(query=query_payload(rows))
    with pytest.raises(QueryNotHonouredError, match="duplicate"):
        connector.query_series(
            "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
        )


def test_rows_with_a_different_time_period_code_are_not_mixed_into_the_series():
    rows = [row(p, 20.0) for p in DECLARED_PERIODS] + [row("2024", 99.0, code="CY")]
    connector = routing_connector(query=query_payload(rows))
    series = connector.query_series(
        "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
    )
    assert [point.period for point in series.points] == DECLARED_PERIODS
    assert all(point.code == "AY" for point in series.points)


# -- cell parsing --------------------------------------------------------------


@pytest.mark.parametrize("marker", ["z", "c", "x", "k", "u", "low", "~", ":", "-", ""])
def test_suppression_markers_never_become_zero(marker: str):
    value, seen = parse_cell(marker)
    assert value is None
    assert seen is not None


def test_numeric_cells_parse_including_strings_and_thousand_separators():
    assert parse_cell("24.94634") == (24.94634, None)
    assert parse_cell("758,887") == (758887.0, None)
    assert parse_cell(12) == (12.0, None)
    assert parse_cell(None) == (None, ":")


def test_a_real_zero_is_kept_as_a_zero():
    assert parse_cell("0") == (0.0, None)


# -- completeness and calibration ---------------------------------------------


def complete_series() -> EducationSeries:
    connector = routing_connector(query=query_payload([row(p, 20.0) for p in DECLARED_PERIODS]))
    return connector.query_series(
        "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
    )


def test_complete_series_converts_to_an_observed_series():
    series = complete_series()
    assert series.complete
    observed = series.to_observed_series()
    assert observed.source_id == SOURCE_ID
    assert observed.periods == tuple(DECLARED_PERIODS)
    assert observed.values == (20.0, 20.0, 20.0, 20.0)
    assert "Percentage of pupil enrolments" in observed.name


def test_a_period_the_source_never_reported_is_a_hole_not_a_zero():
    # Mirrors the real absence data set, which has no 2019/2020 row at all.
    present = [p for p in DECLARED_PERIODS if p != "2022/2023"]
    connector = routing_connector(query=query_payload([row(p, 20.0) for p in present]))
    series = connector.query_series(
        "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
    )
    assert series.missing_periods == ("2022/2023",)
    assert not series.complete
    assert all(point.value == 20.0 for point in series.points)
    with pytest.raises(ValueError, match="not a zero"):
        series.to_observed_series()


def test_a_suppressed_cell_blocks_calibration():
    rows = [row(p, "z" if p == "2023/2024" else 20.0) for p in DECLARED_PERIODS]
    connector = routing_connector(query=query_payload(rows))
    series = connector.query_series(
        "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
    )
    assert series.missing_periods == ()
    assert series.suppressed_periods == ("2023/2024",)
    with pytest.raises(ValueError, match="suppression marker is not a zero"):
        series.to_observed_series()


def test_empty_series_is_refused_rather_than_returned_as_a_flat_line():
    connector = routing_connector(query=query_payload([]), meta=meta_payload(periods=[]))
    series = connector.query_series(
        "019d209c", indicator_id=INDICATOR, filter_ids=(FILTER_ABSENCE, FILTER_SCHOOL)
    )
    assert not series.complete
    with pytest.raises(ValueError, match="nothing to calibrate"):
        series.to_observed_series()


def test_observed_series_name_can_be_overridden():
    observed = complete_series().to_observed_series(name="Persistent absence, secondary, England")
    assert observed.name == "Persistent absence, secondary, England"


# -- documented semantics ------------------------------------------------------


def test_date_field_semantics_distinguish_release_from_coverage():
    assert "release timestamp" in DATE_FIELD_SEMANTICS["dataSet.latestVersion.published"]
    assert "academic year" in DATE_FIELD_SEMANTICS["result.timePeriod.code"]
    assert set(DATE_FIELD_SEMANTICS) >= {
        "publication.lastPublished",
        "dataSet.latestVersion.published",
        "result.timePeriod.period",
        "result.timePeriod.code",
    }


def test_w05_document_rows_are_declared_as_served_by_the_existing_govuk_connector():
    assert DOCUMENT_ROWS_COVERED_ELSEWHERE == {
        "DS054": "oslt_research.connectors.govuk_guidance",
        "DS055": "oslt_research.connectors.govuk_guidance",
    }


def test_series_is_not_labelled_with_a_document_corpus_source_id():
    # DS054/DS055 are guidance corpora; tagging a statistical series with either would
    # misattribute its provenance. DS069 was allocated to this API on 2026-08-16, so the
    # assertion tightened from "not a document corpus and visibly unregistered" to "not a
    # document corpus and registered as its own row".
    assert SOURCE_ID not in {"DS054", "DS055"}
    assert SOURCE_ID == "DS069"
    assert not SOURCE_ID.startswith("UNREGISTERED:")


def test_series_point_usability_flag():
    assert SeriesPoint(period="2021/2022", code="AY", value=1.0).usable
    assert not SeriesPoint(period="2021/2022", code="AY", value=None, marker="z").usable


def test_meta_defaults_are_empty_rather_than_guessed():
    meta = DataSetMeta(data_set_id="x")
    assert meta.periods_for_code("AY") == ()
    assert meta.indicators == {}
