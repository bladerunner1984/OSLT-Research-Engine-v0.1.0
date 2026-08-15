from __future__ import annotations

import pytest

from oslt_research.domain.enums import AccessClass
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.study_family import (
    StudyFamilyResolver,
    normalise_author,
)


def evidence(
    evidence_id: str,
    *,
    title: str = "A study",
    content: str = "",
    authors: list[str] | None = None,
    dependency_family: str | None = None,
    identifiers: dict[str, str] | None = None,
) -> EvidenceObject:
    return EvidenceObject(
        evidence_id=evidence_id,
        title=title,
        content=content,
        provenance=ProvenanceRecord(
            source_id="SRC",
            source_uri=f"https://example.org/{evidence_id}",
            checksum_sha256="a" * 64,
            access_class=AccessClass.OPEN,
        ),
        dependency_family=dependency_family or f"doi:{evidence_id.lower()}",
        metadata={"authors": authors or [], "identifiers": identifiers or {}},
    )


# --------------------------------------------------------------------- helpers


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Smith, John A.", "smith,j"),
        ("John A. Smith", "smith,j"),
        ("de Vries, Annelou L. C.", "de vries,a"),
        ("", ""),
    ],
)
def test_normalise_author(raw, expected):
    assert normalise_author(raw) == expected


# ------------------------------------------------------------------- signals


def test_shared_trial_registration_collapses_records():
    resolver = StudyFamilyResolver()
    resolution = resolver.resolve(
        [
            evidence("EV1", content="Registered as NCT01234567."),
            evidence("EV2", content="Trial registration NCT01234567 reported here."),
            evidence("EV3", content="Unrelated work."),
        ]
    )
    assert resolution.family_count == 2
    assert resolution.signal_counts["SHARED_TRIAL_REGISTRATION"] == 1
    families = {frozenset(members) for members in resolution.families.values()}
    assert frozenset({"EV1", "EV2"}) in families


def test_shared_dataset_accession_collapses_records():
    resolver = StudyFamilyResolver()
    resolution = resolver.resolve(
        [
            evidence("EV1", content="Data available at GSE123456."),
            evidence("EV2", content="Reanalysis of GSE123456."),
        ]
    )
    assert resolution.family_count == 1
    assert resolution.signal_counts["SHARED_DATASET_ACCESSION"] == 1


def test_named_cohort_only_applies_when_lexicon_is_preregistered():
    records = [
        evidence("EV1", title="Findings from the Amsterdam Cohort of Gender Dysphoria"),
        evidence("EV2", title="Long-term outcomes, Amsterdam Cohort of Gender Dysphoria"),
    ]
    assert StudyFamilyResolver().resolve(records).family_count == 2

    declared = StudyFamilyResolver(cohort_lexicon=["Amsterdam Cohort of Gender Dysphoria"])
    resolution = declared.resolve(records)
    assert resolution.family_count == 1
    assert resolution.signal_counts["SHARED_NAMED_COHORT"] == 1


def test_same_dedup_key_still_collapses_cross_source_duplicates():
    resolver = StudyFamilyResolver()
    resolution = resolver.resolve(
        [
            evidence("EV1", dependency_family="doi:10.1/abc"),
            evidence("EV2", dependency_family="doi:10.1/abc"),
        ]
    )
    assert resolution.family_count == 1
    assert resolution.signal_counts["SAME_DEDUP_KEY"] == 1


# ------------------------------------------------------- author-network overlap


def test_author_overlap_needs_both_count_and_ratio():
    shared_group = ["A Smith", "B Jones", "C Brown"]
    resolver = StudyFamilyResolver(min_shared_authors=2, author_jaccard_threshold=0.6)
    resolution = resolver.resolve(
        [
            evidence("EV1", authors=shared_group),
            evidence("EV2", authors=shared_group),
        ]
    )
    assert resolution.family_count == 1
    assert resolution.signal_counts["AUTHOR_NETWORK_OVERLAP"] == 1


def test_one_prolific_shared_author_does_not_collapse_distinct_groups():
    """A single shared author is collaboration, not a shared sample."""

    resolver = StudyFamilyResolver()
    resolution = resolver.resolve(
        [
            evidence("EV1", authors=["A Smith", "B Jones", "C Brown", "D White"]),
            evidence("EV2", authors=["A Smith", "E Green", "F Black", "G Grey"]),
        ]
    )
    assert resolution.family_count == 2
    assert "AUTHOR_NETWORK_OVERLAP" not in resolution.signal_counts


def test_records_with_no_authors_are_not_merged():
    resolver = StudyFamilyResolver()
    resolution = resolver.resolve([evidence("EV1"), evidence("EV2")])
    assert resolution.family_count == 2


# -------------------------------------------------------------- resolution API


def test_transitive_merging_across_different_signals():
    resolver = StudyFamilyResolver()
    resolution = resolver.resolve(
        [
            evidence("EV1", content="NCT01234567", authors=["A Smith", "B Jones"]),
            evidence("EV2", content="NCT01234567"),
            evidence("EV3", authors=["A Smith", "B Jones"]),
        ]
    )
    assert resolution.family_count == 1
    assert resolution.collapse_rate == pytest.approx(2 / 3)


def test_apply_rewrites_dependency_family_and_reports_links():
    resolver = StudyFamilyResolver()
    updated, resolution = resolver.apply(
        [
            evidence("EV1", content="NCT01234567"),
            evidence("EV2", content="NCT01234567"),
            evidence("EV3", content="standalone"),
        ]
    )
    families = {item.evidence_id: item.dependency_family for item in updated}
    assert families["EV1"] == families["EV2"] != families["EV3"]
    assert all(link.signal for link in resolution.links)
    assert resolution.raw_count == 3
    assert resolution.collapse_rate == pytest.approx(1 / 3)


def test_empty_input_is_safe():
    resolution = StudyFamilyResolver().resolve([])
    assert resolution.family_count == 0
    assert resolution.collapse_rate == 0.0


def test_resolver_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        StudyFamilyResolver(min_shared_authors=0)
    with pytest.raises(ValueError):
        StudyFamilyResolver(author_jaccard_threshold=0)
