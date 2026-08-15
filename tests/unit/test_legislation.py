from __future__ import annotations

from datetime import date

import httpx
import pytest

from oslt_research.connectors.legislation import ATOM, LegislationConnector, LegislationItem


def entry(title="Gender Recognition Act 2004",
          url="https://www.legislation.gov.uk/ukpga/2004/7",
          updated="2024-05-18T00:00:00Z") -> str:
    return f"""<entry><title>{title}</title>
      <link href="{url}"/><updated>{updated}</updated></entry>"""


def feed(*entries: str) -> str:
    return f'<feed xmlns="{ATOM}"><title>Search Results</title>' + "".join(entries) + "</feed>"


def connector_for(body: str, *, status: int = 200) -> LegislationConnector:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status, text=body,
                                       headers={"content-type": "application/atom+xml"})
    )
    return LegislationConnector(client=httpx.Client(transport=transport))


def test_enactment_year_comes_from_the_identifier_not_the_website_revision():
    """The Gender Recognition Act 2004 has a 2024 <updated>; it was made in 2004."""

    result = connector_for(feed(entry())).search(title="x")
    [item] = result.items
    assert item.enacted_year == 2004
    assert item.anchor_date() == date(2004, 1, 1)
    assert item.record_updated == date(2024, 5, 18)


def test_anchor_date_ignores_the_website_revision_entirely():
    item = LegislationItem(title="x", url="y", enacted_year=2004,
                           record_updated=date(2026, 1, 1))
    assert item.anchor_date() == date(2004, 1, 1)


def test_an_item_with_only_a_website_revision_is_not_dated():
    item = LegislationItem(title="x", url="y", record_updated=date(2026, 1, 1))
    assert item.is_dated is False
    assert item.anchor_date() is None


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.legislation.gov.uk/uksi/2023/1234", 2023),
        ("https://www.legislation.gov.uk/asp/2021/3", 2021),
        ("https://www.legislation.gov.uk/ssi/2019/45", 2019),
    ],
)
def test_year_is_parsed_from_several_instrument_types(url, expected):
    [item] = connector_for(feed(entry(url=url))).search(title="x").items
    assert item.enacted_year == expected


def test_year_falls_back_to_the_title_when_the_url_has_none():
    body = feed(entry(title="Some Act 1998", url="https://example.org/nothing"))
    assert connector_for(body).search(title="x").items[0].enacted_year == 1998


def test_undated_entry_is_skipped():
    body = feed(entry(title="No year here", url="https://example.org/nothing"))
    result = connector_for(body).search(title="x")
    assert result.items == []
    assert result.skip_reasons["NO_ENACTMENT_YEAR"] == 1


def test_the_search_results_header_is_not_treated_as_an_instrument():
    result = connector_for(feed(entry(title="Search Results"))).search(title="x")
    assert result.skip_reasons["NOT_AN_INSTRUMENT"] == 1


def test_revoked_instruments_are_flagged_but_kept():
    """A revoked instrument was in force for a period, which is what policy propositions ask about."""

    body = feed(entry(title="The Something Order 2022 (revoked)",
                      url="https://www.legislation.gov.uk/uksi/2022/1"))
    [item] = connector_for(body).search(title="x").items
    assert item.revoked and item.enacted_year == 2022


def test_outcome_dates_are_unique_and_sorted():
    body = feed(
        entry(url="https://www.legislation.gov.uk/uksi/2023/1"),
        entry(url="https://www.legislation.gov.uk/uksi/2023/2"),
        entry(url="https://www.legislation.gov.uk/ukpga/2004/7"),
    )
    assert connector_for(body).search(title="x").outcome_dates() == [
        date(2004, 1, 1), date(2023, 1, 1)
    ]


def test_malformed_atom_does_not_raise():
    result = connector_for("<feed>not closed").search(title="x")
    assert result.items == []
    assert result.skip_reasons["ATOM_PARSE_FAILED"] == 1


def test_http_error_propagates():
    with pytest.raises(httpx.HTTPStatusError):
        connector_for("", status=500).search(title="x")
