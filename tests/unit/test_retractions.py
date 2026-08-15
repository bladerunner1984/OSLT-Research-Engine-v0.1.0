from __future__ import annotations

import httpx
import pytest

from oslt_research.connectors.retractions import (
    DEPENDENCY_FAMILY,
    RetractionConnector,
    RetractionRecord,
)
from oslt_research.domain.enums import AccessClass, EvidenceLane, SourceStatus
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord


def notice(*, doi="10.1/notice", target="10.1/original", update_type="retraction",
           title="Retraction Note: Something") -> dict:
    return {
        "DOI": doi,
        "title": [title],
        "issued": {"date-parts": [[2024, 3, 1]]},
        "update-to": [{"DOI": target, "type": update_type}],
    }


def connector_for(*items: dict) -> RetractionConnector:
    body = {"message": {"items": list(items), "total-results": len(items)}}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    return RetractionConnector(client=httpx.Client(transport=transport))


def corpus_record(doi: str) -> EvidenceObject:
    return EvidenceObject(
        evidence_id=f"EV-{doi[-6:]}",
        title="An original paper",
        source_status=SourceStatus.VERIFIED,
        provenance=ProvenanceRecord(
            source_id="SRC", source_uri="https://example.org/x",
            checksum_sha256="a" * 64, access_class=AccessClass.OPEN,
        ),
        dependency_family=f"doi:{doi}",
        metadata={"identifiers": {"doi": doi}},
    )


def test_notice_becomes_correction_retraction_lane_evidence():
    sweep = connector_for(notice()).sweep()
    assert len(sweep.evidence) == 1
    item = sweep.evidence[0]
    assert item.lane is EvidenceLane.CORRECTION_RETRACTION
    assert item.dependency_family == DEPENDENCY_FAMILY
    assert item.metadata["retracted_doi"] == "10.1/original"


def test_retraction_invalidates_but_corrigendum_only_qualifies():
    assert RetractionRecord("a", "b", "retraction").invalidates is True
    assert RetractionRecord("a", "b", "withdrawal").invalidates is True
    assert RetractionRecord("a", "b", "corrigendum").invalidates is False
    assert RetractionRecord("a", "b", "erratum").invalidates is False


def test_self_referential_notice_is_skipped():
    """A notice pointing at itself says nothing about another work."""

    sweep = connector_for(notice(doi="10.1/same", target="10.1/same")).sweep()
    assert sweep.records == []
    assert sweep.skip_reasons["NO_RESOLVABLE_TARGET"] == 1


def test_doi_matching_is_case_and_prefix_insensitive():
    sweep = connector_for(notice(target="https://doi.org/10.1/Original")).sweep()
    assert sweep.records[0].retracted_doi == "10.1/original"


def test_corpus_check_finds_a_retracted_record():
    """A retraction is a separate later document; re-reading the original never shows it."""

    sweep = connector_for(notice(target="10.1/original")).sweep()
    hits = connector_for().check_corpus([corpus_record("10.1/original")], sweep=sweep)
    assert len(hits) == 1
    assert hits[0][1].update_type == "retraction"


def test_corpus_check_matches_via_the_dependency_family_key():
    sweep = connector_for(notice(target="10.1/original")).sweep()
    record = corpus_record("10.1/original").model_copy(update={"metadata": {}})
    assert len(connector_for().check_corpus([record], sweep=sweep)) == 1


def test_clean_corpus_returns_no_hits():
    sweep = connector_for(notice(target="10.1/other")).sweep()
    assert connector_for().check_corpus([corpus_record("10.1/original")], sweep=sweep) == []


def test_record_without_a_doi_is_not_matched():
    sweep = connector_for(notice()).sweep()
    record = corpus_record("10.1/original").model_copy(
        update={"metadata": {}, "dependency_family": "heuristic:no-doi"}
    )
    assert connector_for().check_corpus([record], sweep=sweep) == []


def test_empty_feed_is_safe():
    sweep = connector_for().sweep()
    assert sweep.records == [] and sweep.notices_seen == 0


def test_http_error_propagates():
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        RetractionConnector(client=httpx.Client(transport=transport)).sweep()


# --------------------------------------------------- retraction blocks admission


def test_a_retracted_work_is_refused_admission():
    """A withdrawn finding is not evidence."""

    from oslt_research.connectors.retractions import apply_retraction_status

    sweep = connector_for(notice(target="10.1/original")).sweep()
    updated, tally = apply_retraction_status(
        [corpus_record("10.1/original")], sweep=sweep, connector=connector_for()
    )
    assert tally["retracted"] == 1
    assert updated[0].admitted is False
    assert "SOURCE_WORK_RETRACTED" in updated[0].admission_failures


def test_a_corrigendum_is_flagged_but_keeps_admission():
    """A corrigendum amends a finding; barring it would discard usable evidence."""

    from oslt_research.connectors.retractions import apply_retraction_status

    sweep = connector_for(
        notice(target="10.1/original", update_type="corrigendum")
    ).sweep()
    updated, tally = apply_retraction_status(
        [corpus_record("10.1/original")], sweep=sweep, connector=connector_for()
    )
    assert tally["corrected"] == 1
    assert updated[0].admitted is True
    assert updated[0].metadata["source_work_retracted"] is False


def test_affected_records_are_moved_into_the_retraction_lane():
    from oslt_research.connectors.retractions import apply_retraction_status

    sweep = connector_for(notice(target="10.1/original")).sweep()
    updated, _ = apply_retraction_status(
        [corpus_record("10.1/original")], sweep=sweep, connector=connector_for()
    )
    assert updated[0].lane is EvidenceLane.CORRECTION_RETRACTION


def test_the_reason_is_written_down_not_applied_silently():
    from oslt_research.connectors.retractions import apply_retraction_status

    sweep = connector_for(notice(doi="10.1/notice", target="10.1/original")).sweep()
    updated, _ = apply_retraction_status(
        [corpus_record("10.1/original")], sweep=sweep, connector=connector_for()
    )
    assert updated[0].metadata["retraction_notice_doi"] == "10.1/notice"
    assert updated[0].metadata["retraction_update_type"] == "retraction"


def test_unaffected_records_are_untouched():
    from oslt_research.connectors.retractions import apply_retraction_status

    original = corpus_record("10.1/clean")
    sweep = connector_for(notice(target="10.1/other")).sweep()
    updated, tally = apply_retraction_status(
        [original], sweep=sweep, connector=connector_for()
    )
    assert tally["unaffected"] == 1
    assert updated[0] == original
