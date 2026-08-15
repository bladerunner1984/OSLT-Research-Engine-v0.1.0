from __future__ import annotations

from datetime import date

import pytest

from oslt_research.connectors.base import HarvestQuery, RawRecord, SourceConnector
from oslt_research.evidence.provenance import sha256_text
from oslt_research.pipelines.registration_linkage import (
    LinkageOutcome,
    LinkageReport,
    RegistrationPublicationLinker,
    RegistrationRecord,
    extract_registration_ids,
    parse_registration_date,
)


class StubIndex(SourceConnector):
    source_name = "StubIndex"
    connector_version = "1"

    def __init__(self, *, hits: dict[str, list[tuple[str, str]]] | None = None, fail: bool = False):
        #: query concept -> [(content, published_at)]
        self.hits = hits or {}
        self.fail = fail

    async def harvest(self, query: HarvestQuery) -> list[RawRecord]:
        if self.fail:
            raise RuntimeError("index unavailable")
        results = []
        for index, (content, published) in enumerate(self.hits.get(query.concept, [])):
            results.append(
                RawRecord(
                    source_name=self.source_name,
                    source_record_id=f"{query.concept}-{index}",
                    title="A trial report",
                    content=content,
                    source_uri=f"https://example.org/{index}",
                    published_at=published,
                    identifiers={"doi": f"10.1/stub-{sha256_text(content)[:8]}-{index}"},
                    raw_response_hash=sha256_text(f"{query.concept}{index}"),
                )
            )
        return results


REG = RegistrationRecord(registration_id="NCT01234567", registered_on=date(2018, 1, 1))


# ------------------------------------------------------------------ primitives


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Registered NCT01234567 here", {"NCT01234567"}),
        ("isrctn12345678 lowercase", {"ISRCTN12345678"}),
        ("no identifier at all", set()),
    ],
)
def test_extract_registration_ids(text, expected):
    assert extract_registration_ids(text) == expected


@pytest.mark.parametrize(
    "value,expected",
    [("2020-05-04", date(2020, 5, 4)), ("2020-05", date(2020, 5, 1)),
     ("2020", date(2020, 1, 1)), ("junk", None), (None, None)],
)
def test_parse_registration_date(value, expected):
    assert parse_registration_date(value) == expected


# --------------------------------------------------------------------- linking


async def test_exact_identifier_match_creates_a_link():
    index = StubIndex(hits={"NCT01234567": [("Results of NCT01234567", "2020-01-01")]})
    report = await RegistrationPublicationLinker().link([REG], [index])
    outcome = report.outcomes[0]
    assert outcome.linked
    assert outcome.first_publication_on == date(2020, 1, 1)
    assert outcome.days_to_publication == 730  # 2018 and 2019 are both non-leap


async def test_topic_similar_record_without_the_identifier_is_not_a_link():
    """A paper on the same subject is not evidence that this trial was published."""

    index = StubIndex(hits={"NCT01234567": [("A study of the same condition", "2020-01-01")]})
    report = await RegistrationPublicationLinker().link([REG], [index])
    assert not report.outcomes[0].linked
    assert report.linkage_rate == 0.0


async def test_a_different_registration_id_does_not_match():
    index = StubIndex(hits={"NCT01234567": [("Results of NCT09999999", "2020-01-01")]})
    report = await RegistrationPublicationLinker().link([REG], [index])
    assert not report.outcomes[0].linked


async def test_failed_search_is_excluded_from_the_denominator():
    """A system failure must never be counted as a non-publication."""

    report = await RegistrationPublicationLinker().link([REG], [StubIndex(fail=True)])
    assert report.denominator == 0
    assert report.linkage_rate is None
    assert report.summary()["search_failures_excluded"] == 1
    assert report.outcomes[0].errors


async def test_one_failing_index_does_not_void_a_working_one():
    working = StubIndex(hits={"NCT01234567": [("NCT01234567 published", "2019-06-01")]})
    report = await RegistrationPublicationLinker().link([REG], [StubIndex(fail=True), working])
    assert report.denominator == 1
    assert report.outcomes[0].linked
    assert report.outcomes[0].errors  # the failure is still recorded


async def test_publications_are_deduplicated_across_indexes():
    hit = {"NCT01234567": [("NCT01234567 report", "2020-01-01")]}
    report = await RegistrationPublicationLinker().link(
        [REG], [StubIndex(hits=hit), StubIndex(hits=hit)]
    )
    assert len(report.outcomes[0].publication_ids) == 1


async def test_earliest_publication_date_is_used():
    index = StubIndex(hits={"NCT01234567": [
        ("NCT01234567 later report", "2021-01-01"),
        ("NCT01234567 first report", "2019-01-01"),
    ]})
    report = await RegistrationPublicationLinker().link([REG], [index])
    assert report.outcomes[0].first_publication_on == date(2019, 1, 1)


async def test_publication_before_registration_yields_no_interval():
    early = RegistrationRecord(registration_id="NCT01234567", registered_on=date(2022, 1, 1))
    index = StubIndex(hits={"NCT01234567": [("NCT01234567", "2019-01-01")]})
    report = await RegistrationPublicationLinker().link([early], [index])
    assert report.outcomes[0].days_to_publication is None


# ---------------------------------------------------------------------- report


def test_report_summary_carries_the_interpretation_bound():
    report = LinkageReport(outcomes=[LinkageOutcome(registration=REG, sources_searched=["S"])])
    summary = report.summary()
    assert summary["not_linked"] == 1
    assert "not a count of unpublished studies" in summary["interpretation_bound"]


def test_median_days_is_none_when_no_intervals_exist():
    report = LinkageReport(outcomes=[LinkageOutcome(registration=REG, sources_searched=["S"])])
    assert report.median_days_to_publication() is None


def test_linker_rejects_invalid_page_size():
    with pytest.raises(ValueError):
        RegistrationPublicationLinker(max_records_per_query=0)


async def test_follow_up_cutoff_excludes_registrations_too_recent_to_publish():
    """A trial registered last month has not failed to publish; it has not had time."""

    recent = RegistrationRecord(registration_id="NCT09999999", registered_on=date(2026, 7, 1))
    old = RegistrationRecord(registration_id="NCT01234567", registered_on=date(2018, 1, 1))
    index = StubIndex(hits={"NCT01234567": [("NCT01234567 report", "2020-01-01")]})

    report = await RegistrationPublicationLinker().link(
        [recent, old], [index], follow_up_cutoff=date(2024, 1, 1)
    )
    assert report.denominator == 1
    assert report.linkage_rate == 1.0
    summary = report.summary()
    assert summary["excluded_insufficient_follow_up"] == 1
    assert summary["registrations_supplied"] == 2
    assert summary["follow_up_cutoff"] == "2024-01-01"


async def test_no_cutoff_keeps_every_registration():
    recent = RegistrationRecord(registration_id="NCT09999999", registered_on=date(2026, 7, 1))
    report = await RegistrationPublicationLinker().link([recent], [StubIndex()])
    assert report.denominator == 1
    assert report.summary()["excluded_insufficient_follow_up"] == 0
