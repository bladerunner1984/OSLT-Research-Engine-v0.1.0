from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from oslt_research.domain.enums import AccessClass, SourceStatus
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.abstract_enrichment import (
    ABSTRACT_ENRICHMENT_TRANSFORMATION_ID,
    SOURCE_EUROPE_PMC,
    SOURCE_OPENALEX,
    AbstractEnricher,
)
from oslt_research.evidence.provenance import assess_evidence_admission, sha256_text


ABSTRACT = (
    "Community-based support was associated with a measured reduction in unplanned admissions "
    "across the observed cohort, with wide confidence intervals and no causal identification."
)
OTHER_ABSTRACT = (
    "A second and clearly distinguishable abstract body used to prove which upstream source "
    "actually answered the lookup for this record."
)

RAW_HASH = "a" * 64


def evidence(
    *,
    evidence_id: str = "EV-1",
    title: str = "Community support and unplanned admissions",
    content: str | None = None,
    identifiers: dict[str, str] | None = None,
    dependency_family: str = "heuristic:community-support:smith:2021",
    transformation_ids: list[str] | None = None,
) -> EvidenceObject:
    body = title if content is None else content
    return EvidenceObject(
        evidence_id=evidence_id,
        title=title,
        content=body,
        source_status=SourceStatus.VERIFIED,
        provenance=ProvenanceRecord(
            source_id="DS033",
            source_uri="https://openalex.org/W1",
            checksum_sha256=RAW_HASH,
            access_class=AccessClass.OPEN,
            licence_or_approval="PUBLIC_API_TERMS_APPLY",
            transformation_ids=list(transformation_ids or ["RAW_RECORD_TO_EVIDENCE_V1"]),
        ),
        dependency_family=dependency_family,
        metadata={
            "identifiers": identifiers or {},
            "content_sha256": sha256_text(body),
        },
    )


def epmc_body(abstract: str | None) -> dict:
    result = {"id": "1", "title": "t"}
    if abstract is not None:
        result["abstractText"] = abstract
    return {"resultList": {"result": [result]}}


def openalex_body(abstract: str | None) -> dict:
    item: dict = {"id": "https://openalex.org/W1", "display_name": "t"}
    if abstract is not None:
        index: dict[str, list[int]] = {}
        for position, word in enumerate(abstract.split()):
            index.setdefault(word, []).append(position)
        item["abstract_inverted_index"] = index
    return {"results": [item]}


def enricher_for(
    handler: Callable[[httpx.Request], httpx.Response], **kwargs
) -> AbstractEnricher:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return AbstractEnricher(client=client, **kwargs)


def recording_handler(
    responses: dict[str, httpx.Response] | None = None,
    *,
    default: httpx.Response | None = None,
    seen: list[httpx.Request] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    """Route by host so a test can prove which upstream service was actually asked."""

    responses = responses or {}

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        for host_fragment, response in responses.items():
            if host_fragment in request.url.host:
                return response
        if default is not None:
            return default
        return httpx.Response(200, json={"resultList": {"result": []}, "results": []})

    return handler


def test_doi_lookup_hits_europe_pmc_and_writes_the_abstract():
    seen: list[httpx.Request] = []
    handler = recording_handler({"ebi.ac.uk": httpx.Response(200, json=epmc_body(ABSTRACT))},
                                seen=seen)
    record = evidence(identifiers={"doi": "https://doi.org/10.1000/ABC"})

    enriched, summary = enricher_for(handler).enrich([record])

    assert summary.attempted == 1 and summary.enriched == 1 and summary.unenriched == 0
    assert summary.by_source == {SOURCE_EUROPE_PMC: 1}
    assert ABSTRACT in enriched[0].content
    # DOI is normalised out of its URL form and lower-cased before it is sent.
    assert 'DOI:"10.1000/abc"' in seen[0].url.params["query"]


def test_pmid_is_used_when_no_doi_is_present():
    seen: list[httpx.Request] = []
    handler = recording_handler({"ebi.ac.uk": httpx.Response(200, json=epmc_body(ABSTRACT))},
                                seen=seen)
    record = evidence(identifiers={"pmid": "https://pubmed.ncbi.nlm.nih.gov/123456"})

    enriched, summary = enricher_for(handler).enrich([record])

    assert summary.enriched == 1
    assert enriched[0].metadata["abstract_enrichment"]["lookup_kind"] == "pmid"
    assert seen[0].url.params["query"] == "EXT_ID:123456 AND SRC:MED"


def test_title_is_the_last_resort_when_no_identifier_exists():
    seen: list[httpx.Request] = []
    handler = recording_handler({"ebi.ac.uk": httpx.Response(200, json=epmc_body(ABSTRACT))},
                                seen=seen)

    enriched, summary = enricher_for(handler).enrich([evidence()])

    assert summary.enriched == 1
    assert enriched[0].metadata["abstract_enrichment"]["lookup_kind"] == "title"
    assert 'TITLE:"Community support and unplanned admissions"' in seen[0].url.params["query"]


def test_openalex_answers_when_europe_pmc_has_nothing():
    handler = recording_handler(
        {
            "ebi.ac.uk": httpx.Response(200, json=epmc_body(None)),
            "openalex.org": httpx.Response(200, json=openalex_body(OTHER_ABSTRACT)),
        }
    )
    record = evidence(identifiers={"doi": "10.1000/abc"})

    enriched, summary = enricher_for(handler).enrich([record])

    assert summary.by_source == {SOURCE_OPENALEX: 1}
    assert OTHER_ABSTRACT in enriched[0].content


def test_identifier_match_outranks_a_title_search_on_the_preferred_source():
    """A DOI hit anywhere beats a title hit: title search can match the wrong paper."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "openalex.org" in request.url.host:
            return httpx.Response(200, json=openalex_body(ABSTRACT))
        # Europe PMC knows the title but not the DOI.
        query = request.url.params["query"]
        if query.startswith("TITLE:"):
            return httpx.Response(200, json=epmc_body(OTHER_ABSTRACT))
        return httpx.Response(200, json=epmc_body(None))

    record = evidence(identifiers={"doi": "10.1000/abc"})
    enriched, summary = enricher_for(handler).enrich([record])

    assert summary.by_source == {SOURCE_OPENALEX: 1}
    assert ABSTRACT in enriched[0].content


def test_no_result_leaves_the_record_untouched_and_counts_as_unenriched():
    original = evidence()
    enriched, summary = enricher_for(recording_handler()).enrich([original])

    assert enriched[0] == original
    assert summary.attempted == 1 and summary.enriched == 0 and summary.unenriched == 1
    assert summary.by_source == {}


def test_placeholder_length_text_is_not_accepted_as_an_abstract():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body("No abstract.")))
    original = evidence()

    enriched, summary = enricher_for(handler).enrich([original])

    assert enriched[0] == original
    assert summary.unenriched == 1


def test_transformation_id_is_appended_not_replaced():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body(ABSTRACT)))
    enriched, _ = enricher_for(handler).enrich([evidence()])

    assert enriched[0].provenance.transformation_ids == [
        "RAW_RECORD_TO_EVIDENCE_V1",
        ABSTRACT_ENRICHMENT_TRANSFORMATION_ID,
    ]


def test_original_response_checksum_is_preserved():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body(ABSTRACT)))
    enriched, _ = enricher_for(handler).enrich([evidence()])

    assert enriched[0].provenance.checksum_sha256 == RAW_HASH


def test_content_hash_is_recomputed_for_the_new_content():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body(ABSTRACT)))
    enriched, _ = enricher_for(handler).enrich([evidence()])

    item = enriched[0]
    assert item.metadata["content_sha256"] == sha256_text(item.content)
    assert item.metadata["abstract_enrichment"]["abstract_sha256"] == sha256_text(ABSTRACT)


def test_enriched_record_still_passes_admission():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body(ABSTRACT)))
    enriched, _ = enricher_for(handler).enrich([evidence()])

    decision = assess_evidence_admission(enriched[0])
    assert decision.admitted is True
    assert decision.failures == []
    assert enriched[0].admitted is True


def test_http_error_is_absorbed_and_counted_not_raised():
    handler = recording_handler(
        {
            "ebi.ac.uk": httpx.Response(503),
            "openalex.org": httpx.Response(200, json=openalex_body(ABSTRACT)),
        }
    )
    enriched, summary = enricher_for(handler).enrich([evidence()])

    assert summary.enriched == 1
    assert summary.source_errors == {SOURCE_EUROPE_PMC: 1}
    assert ABSTRACT in enriched[0].content


def test_transport_failure_on_every_source_leaves_the_record_intact():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down", request=request)

    original = evidence()
    enriched, summary = enricher_for(handler).enrich([original])

    assert enriched[0] == original
    assert summary.unenriched == 1
    assert summary.source_errors == {SOURCE_EUROPE_PMC: 1, SOURCE_OPENALEX: 1}


def test_records_that_already_have_substance_are_not_attempted():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no network call should be made for a long record")

    long_record = evidence(content="x" * 400)
    enriched, summary = enricher_for(handler).enrich([long_record])

    assert enriched[0] == long_record
    assert summary.attempted == 0 and summary.enriched == 0 and summary.unenriched == 0


def test_an_abstract_already_present_in_content_is_not_duplicated():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body(ABSTRACT)))
    original = evidence(content=f"Title\n\n{ABSTRACT}", identifiers={"doi": "10.1000/abc"})

    enriched, summary = enricher_for(handler, min_content_length=10_000).enrich([original])

    assert enriched[0] == original
    assert summary.attempted == 1 and summary.unenriched == 1


def test_summary_reports_median_content_length_before_and_after():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body(ABSTRACT)))
    records = [
        evidence(evidence_id="EV-1", title="Short one"),
        evidence(evidence_id="EV-2", title="Short two"),
        evidence(evidence_id="EV-3", title="Short three"),
    ]

    enriched, summary = enricher_for(handler).enrich(records)

    assert summary.median_content_length_before == 9.0
    assert summary.median_content_length_after == float(len(enriched[1].content))
    assert summary.median_content_length_after > summary.median_content_length_before


def test_empty_input_is_safe():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no network call should be made for an empty corpus")

    enriched, summary = enricher_for(handler).enrich([])

    assert enriched == []
    assert summary.attempted == 0
    assert summary.median_content_length_before == 0.0
    assert summary.median_content_length_after == 0.0


def test_dependency_family_supplies_the_doi_when_identifiers_are_missing():
    seen: list[httpx.Request] = []
    handler = recording_handler({"ebi.ac.uk": httpx.Response(200, json=epmc_body(ABSTRACT))},
                                seen=seen)
    record = evidence(dependency_family="doi:10.5555/xyz")

    _, summary = enricher_for(handler).enrich([record])

    assert summary.enriched == 1
    assert 'DOI:"10.5555/xyz"' in seen[0].url.params["query"]


def test_inputs_are_not_mutated_in_place():
    handler = recording_handler(default=httpx.Response(200, json=epmc_body(ABSTRACT)))
    original = evidence()
    snapshot = original.model_copy(deep=True)

    enriched, _ = enricher_for(handler).enrich([original])

    assert original == snapshot
    assert enriched[0] is not original


@pytest.mark.parametrize("status", [400, 429, 500, 503])
def test_every_error_status_degrades_rather_than_aborting(status: int):
    handler = recording_handler(default=httpx.Response(status))
    original = evidence()

    enriched, summary = enricher_for(handler).enrich([original])

    assert enriched[0] == original
    assert summary.source_errors == {SOURCE_EUROPE_PMC: 1, SOURCE_OPENALEX: 1}
