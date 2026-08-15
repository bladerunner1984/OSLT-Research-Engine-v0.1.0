"""Tests for the NHS open-aggregate connector.

Every behaviour asserted here corresponds to a failure this project has actually had: a
suppressed cell read as zero, overlapping aggregates summed, a date-looking field that
meant something else, a query parameter the API silently discarded, and a host fetched
against its own published policy. No test touches the network.
"""

from __future__ import annotations

import json

import httpx
import pytest

from oslt_research.connectors.nhs_statistics import (
    DECLINED_ROUTES,
    ODS_MAX_LIMIT,
    ODS_ROLE_NHS_TRUST,
    SOURCE_ID,
    AggregateCell,
    NhsDataError,
    NhsEnglandStatisticsIndex,
    NhsOdsConnector,
    NhsPeriod,
    RouteDeclinedError,
    build_series,
    declined_route_for,
    guard_route,
    parse_cell,
)

# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def _cell(
    *,
    period: str,
    value: float | None,
    breakdown_level: str = "England",
    breakdown_code: str = "E92000001",
    breakdown_name: str = "England",
    age_group: str = "18 to 24",
    gender: str = "Persons",
    measure: str = "Referrals received",
) -> AggregateCell:
    return AggregateCell(
        measure=measure,
        breakdown_level=breakdown_level,
        breakdown_code=breakdown_code,
        breakdown_name=breakdown_name,
        age_group=age_group,
        gender=gender,
        period=NhsPeriod.parse(period),
        value=value,
    )


def _ods_client(handler) -> NhsOdsConnector:
    transport = httpx.MockTransport(handler)
    return NhsOdsConnector(
        client=httpx.Client(transport=transport), min_interval_seconds=0.0
    )


def _ods_list_payload(*orgs: dict) -> str:
    return json.dumps({"Organisations": list(orgs)})


def _org(org_id: str, name: str, status: str = "Active") -> dict:
    return {
        "Name": name,
        "OrgId": org_id,
        "Status": status,
        "OrgRecordClass": "RC1",
        "PostCode": "NW1 0PE",
        "LastChangeDate": "2026-04-10",
        "PrimaryRoleId": ODS_ROLE_NHS_TRUST,
        "PrimaryRoleDescription": "NHS TRUST",
        "OrgLink": f"https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations/{org_id}",
    }


# --------------------------------------------------------------------------------------
# 1. A hole is never a zero
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("marker", ["*", "**", ".", "..", "c", "z", "w", "N/A", "", "  ", ":"])
def test_suppression_markers_are_missing_not_zero(marker: str) -> None:
    assert parse_cell(marker) is None


def test_a_published_zero_is_a_real_observation() -> None:
    """Zero is data. Only the markers are holes - conflating them loses real troughs."""

    assert parse_cell("0") == 0.0
    assert parse_cell(0) == 0.0


def test_thousands_separators_survive() -> None:
    assert parse_cell("1,234") == 1234.0


def test_percentages_are_refused_rather_than_guessed() -> None:
    with pytest.raises(NhsDataError, match="percent"):
        parse_cell("12.5%")


def test_build_series_refuses_a_suppressed_cell() -> None:
    cells = [
        _cell(period="2021/22", value=1200.0),
        _cell(period="2022/23", value=None),
        _cell(period="2023/24", value=1400.0),
    ]
    with pytest.raises(NhsDataError, match="never 0"):
        build_series(cells)


def test_build_series_names_the_missing_period() -> None:
    cells = [
        _cell(period="2021/22", value=1200.0),
        _cell(period="2022/23", value=None),
        _cell(period="2023/24", value=1400.0),
    ]
    with pytest.raises(NhsDataError, match="2022/23"):
        build_series(cells)


def test_build_series_succeeds_when_complete() -> None:
    series = build_series(
        [
            _cell(period="2021/22", value=1200.0),
            _cell(period="2022/23", value=1300.0),
            _cell(period="2023/24", value=1400.0),
        ]
    )
    assert series.source_id == SOURCE_ID
    assert series.values == (1200.0, 1300.0, 1400.0)
    assert series.periods == ("2021/22", "2022/23", "2023/24")


# --------------------------------------------------------------------------------------
# 2. Overlapping aggregates are never summed
# --------------------------------------------------------------------------------------


def test_england_total_beside_a_region_is_refused() -> None:
    cells = [
        _cell(period="2021/22", value=1200.0),
        _cell(period="2022/23", value=1300.0),
        _cell(period="2023/24", value=1400.0),
        _cell(
            period="2023/24",
            value=90.0,
            breakdown_level="Region",
            breakdown_code="E40000003",
            breakdown_name="London",
        ),
    ]
    with pytest.raises(NhsDataError, match="strata"):
        build_series(cells)


def test_all_ages_beside_an_age_band_is_refused() -> None:
    cells = [
        _cell(period="2021/22", value=1200.0, age_group="All ages"),
        _cell(period="2022/23", value=1300.0, age_group="All ages"),
        _cell(period="2023/24", value=1400.0, age_group="18 to 24"),
    ]
    with pytest.raises(NhsDataError, match="strata"):
        build_series(cells)


def test_duplicate_period_within_one_stratum_is_refused() -> None:
    """A revised figure beside the original is not two observations."""

    cells = [
        _cell(period="2021/22", value=1200.0),
        _cell(period="2022/23", value=1300.0),
        _cell(period="2022/23", value=1310.0),
    ]
    with pytest.raises(NhsDataError, match="more than one row"):
        build_series(cells)


def test_empty_selection_is_refused() -> None:
    with pytest.raises(NhsDataError, match="nothing to calibrate"):
        build_series([])


# --------------------------------------------------------------------------------------
# 3. Date-looking fields mean different things
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,basis",
    [
        ("2023/24", "financial_year"),
        ("2022-23", "financial_year"),
        ("Q4 2022-23", "financial_quarter"),
        ("May 2026", "reporting_month"),
        ("2019", "calendar_year"),
        ("Provisional, month 5", "unknown"),
    ],
)
def test_period_basis_is_established_not_assumed(label: str, basis: str) -> None:
    assert NhsPeriod.parse(label).basis == basis


def test_period_label_is_preserved_verbatim() -> None:
    assert NhsPeriod.parse("  2023/24 ").label == "2023/24"


def test_financial_year_refuses_calendar_coercion() -> None:
    with pytest.raises(NhsDataError, match="financial year"):
        NhsPeriod.parse("2023/24").as_calendar_year()


def test_financial_quarter_refuses_calendar_coercion() -> None:
    with pytest.raises(NhsDataError, match="financial quarter"):
        NhsPeriod.parse("Q4 2022-23").as_calendar_year()


def test_calendar_year_converts() -> None:
    assert NhsPeriod.parse("2019").as_calendar_year() == 2019


def test_start_year_is_only_the_start_of_the_window() -> None:
    assert NhsPeriod.parse("2023/24").start_year == 2023


def test_mixed_period_bases_are_refused() -> None:
    cells = [
        _cell(period="2021/22", value=1.0),
        _cell(period="2022/23", value=2.0),
        _cell(period="2024", value=3.0),
    ]
    with pytest.raises(NhsDataError, match="not points on the same axis"):
        build_series(cells)


def test_ods_last_change_date_is_not_an_operational_date() -> None:
    """The most authoritative-looking date on an ODS record is the least useful one."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "Organisation": {
                    "Name": "HAMPSHIRE AND ISLE OF WIGHT HEALTHCARE NHS FOUNDATION TRUST",
                    "Date": [{"Type": "Operational", "Start": "2001-04-01"}],
                    "OrgId": {"extension": "RW1"},
                    "Status": "Active",
                    "LastChangeDate": "2025-08-19",
                    "orgRecordClass": "RC1",
                    "GeoLoc": {"Location": {"PostCode": "SO40 2RZ"}},
                    "Roles": {
                        "Role": [
                            {
                                "id": "RO197",
                                "uniqueRoleId": 117291,
                                "primaryRole": True,
                                "Status": "Active",
                                "Date": [{"Type": "Operational", "Start": "2001-04-01"}],
                            },
                            {"id": "RO57", "uniqueRoleId": 155240, "Status": "Active"},
                        ]
                    },
                }
            },
        )

    org = _ods_client(handler).organisation("rw1")
    assert org.last_change_date == "2025-08-19"
    assert org.operational_start == "2001-04-01"
    assert org.last_change_date != org.operational_start
    assert org.primary_role_id == ODS_ROLE_NHS_TRUST
    assert org.role_ids == ("RO197", "RO57")
    assert org.active


# --------------------------------------------------------------------------------------
# 4. A query parameter must be shown to be honoured
# --------------------------------------------------------------------------------------


def test_filters_reach_the_wire() -> None:
    seen: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(
            200,
            text=_ods_list_payload(_org("G6V2S", "NORTH LONDON NHS FOUNDATION TRUST")),
            headers={"X-Total-Count": "273", "Returned-Records": "1"},
        )

    connector = _ods_client(handler)
    result = connector.search_organisations(primary_role_id=ODS_ROLE_NHS_TRUST, limit=5)
    assert result.total_count == 273
    assert result.returned_records == 1
    assert result.exhausted
    assert "PrimaryRoleId=RO197" in str(seen[0])
    assert "Limit=5" in str(seen[0])


def test_verify_filter_honoured_detects_a_discarded_parameter() -> None:
    """The exact failure two other connectors shipped: the term was ignored."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=_ods_list_payload(_org("001", "CLWYD")),
            headers={"X-Total-Count": "305791"},
        )

    connector = _ods_client(handler)
    assert not connector.verify_filter_honoured(
        field_name="Name", value_a="tavistock", value_b="maudsley"
    )


def test_verify_filter_honoured_passes_when_totals_differ() -> None:
    counts = iter(["69", "12"])
    ids = iter(["5CV03", "RJ8"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=_ods_list_payload(_org(next(ids), "SOMEWHERE")),
            headers={"X-Total-Count": next(counts)},
        )

    connector = _ods_client(handler)
    assert connector.verify_filter_honoured(
        field_name="Name", value_a="tavistock", value_b="maudsley"
    )


def test_identical_probe_values_are_refused() -> None:
    connector = _ods_client(lambda request: httpx.Response(200, text=_ods_list_payload()))
    with pytest.raises(ValueError, match="genuinely differ"):
        connector.verify_filter_honoured(field_name="Name", value_a="x", value_b="x")


def test_unfiltered_search_is_refused() -> None:
    connector = _ods_client(lambda request: httpx.Response(200, text=_ods_list_payload()))
    with pytest.raises(ValueError, match="at least one"):
        connector.search_organisations(limit=5)


def test_limit_above_the_ods_ceiling_is_refused_locally() -> None:
    connector = _ods_client(lambda request: httpx.Response(200, text=_ods_list_payload()))
    with pytest.raises(ValueError, match="406"):
        connector.search_organisations(status="Active", limit=ODS_MAX_LIMIT + 1)


def test_next_page_header_is_surfaced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=_ods_list_payload(_org("G6V2S", "NORTH LONDON NHS FOUNDATION TRUST")),
            headers={"Next-Page": "https://directory.spineservices.nhs.uk/x?Offset=5"},
        )

    result = _ods_client(handler).search_organisations(status="Active", limit=5)
    assert not result.exhausted


def test_malformed_envelope_raises() -> None:
    connector = _ods_client(lambda request: httpx.Response(200, json={"oops": []}))
    with pytest.raises(NhsDataError, match="Organisations envelope"):
        connector.search_organisations(status="Active")


# --------------------------------------------------------------------------------------
# 5. Declined routes are enforced, not merely documented
# --------------------------------------------------------------------------------------


def test_mhsds_file_host_is_declined() -> None:
    url = "https://files.digital.nhs.uk/0A/ADDA1F/MHSDS%20Time_Series_data.zip"
    route = declined_route_for(url)
    assert route is not None
    assert "Disallow: /" in route.policy
    with pytest.raises(RouteDeclinedError, match="files.digital.nhs.uk"):
        guard_route(url)


def test_ckan_api_is_declined_but_only_under_api() -> None:
    assert declined_route_for("https://ckan.publishing.service.gov.uk/api/3/action/x") is not None
    assert declined_route_for("https://ckan.publishing.service.gov.uk/dataset/x") is None


def test_permitted_hosts_pass_through() -> None:
    url = "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
    assert guard_route(url) == url


def test_every_declined_route_records_its_citation() -> None:
    for route in DECLINED_ROUTES:
        assert route.policy_url.endswith("robots.txt")
        assert route.checked_on
        assert route.offers


# --------------------------------------------------------------------------------------
# 6. NHS England publication index: references only
# --------------------------------------------------------------------------------------

# Shape and irregularity copied from the live cyped-waiting-times page (2026-08-15).
_UPLOAD = "https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2023/05"
_XLSX = f"{_UPLOAD}/CYP-ED-Waiting-Times-Timeseries-Q4-2022-23-England-Imputed.xlsx"

_PAGE = f"""
<html><body>
<a href="{_XLSX}">Timeseries</a>
<a href="{_XLSX}">Duplicate listing</a>
<a href="/statistics/wp-content/uploads/sites/2/2019/11/EIP-September-2019.csv">CSV</a>
<a href="https://files.digital.nhs.uk/11/AD6F86/MHSDS%20Data.zip">MHSDS bulk</a>
<a href="https://www.england.nhs.uk/statistics/statistical-work-areas/">Not a file</a>
</body></html>
"""


def _index(page: str = _PAGE) -> NhsEnglandStatisticsIndex:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=page))
    return NhsEnglandStatisticsIndex(
        client=httpx.Client(transport=transport), min_interval_seconds=0.0
    )


def test_publication_files_are_discovered_and_deduplicated() -> None:
    files = _index().publication_files("cyped-waiting-times")
    assert [item.extension for item in files] == ["xlsx", "csv"]
    assert files[0].filename.endswith("England-Imputed.xlsx")
    assert files[0].is_spreadsheet
    assert not files[1].is_spreadsheet


def test_relative_links_are_resolved_against_the_nhse_host() -> None:
    files = _index().publication_files("cyped-waiting-times")
    assert files[1].url.startswith("https://www.england.nhs.uk/statistics/")


def test_declined_hosts_are_never_handed_back_to_the_caller() -> None:
    """A caller cannot be given a URL this project has undertaken not to fetch."""

    files = _index().publication_files("cyped-waiting-times")
    assert all("files.digital.nhs.uk" not in item.url for item in files)


def test_page_url_is_recorded_for_provenance() -> None:
    files = _index().publication_files("cyped-waiting-times")
    assert files[0].page_url.endswith("/statistical-work-areas/cyped-waiting-times/")


def test_empty_work_area_is_refused() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        _index().publication_files("  ")


def test_index_yields_no_numbers() -> None:
    """The class deliberately exposes no value-bearing attribute to inherit a wrong figure from."""

    item = _index().publication_files("cyped-waiting-times")[0]
    assert not hasattr(item, "value")
    assert not hasattr(item, "period")
