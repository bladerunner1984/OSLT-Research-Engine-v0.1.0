from __future__ import annotations

import pytest

from oslt_research.domain.enums import AccessClass, EvidenceLane
from oslt_research.domain.models import EvidenceObject, ProvenanceRecord
from oslt_research.evidence.lane_coding import (
    LaneClassifier,
    cohens_kappa,
    simulate_coder_drift,
)


def evidence(evidence_id: str, title: str = "A study", content: str = "") -> EvidenceObject:
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
        dependency_family=f"doi:{evidence_id}",
    )


# ------------------------------------------------------------------- classifier


@pytest.mark.parametrize(
    "text,expected",
    [
        ("This article has been retracted by the publisher", EvidenceLane.CORRECTION_RETRACTION),
        ("An independent replication of the earlier finding", EvidenceLane.REPLICATION),
        ("Risk of bias in the included studies", EvidenceLane.BIAS_CRITIQUE),
        ("There was no significant association between groups", EvidenceLane.NULL),
        ("An alternative explanation is reverse causation", EvidenceLane.RIVAL),
    ],
)
def test_surface_cues_route_to_the_expected_lane(text, expected):
    assignment = LaneClassifier().classify(evidence("EV1", content=text))
    assert assignment.lane is expected
    assert assignment.matched_signals


def test_retraction_outranks_other_cues():
    """A retracted paper is a correction record whatever it originally reported."""

    text = "Retracted: an independent replication showing no significant association"
    assert LaneClassifier().classify(evidence("EV1", content=text)).lane is (
        EvidenceLane.CORRECTION_RETRACTION
    )


def test_support_and_contradict_are_never_assigned_automatically():
    """Those lanes are proposition-relative and cannot be read off a text alone."""

    texts = [
        "These results strongly support the hypothesis",
        "Our findings contradict the prevailing model",
        "This confirms the theory",
    ]
    for text in texts:
        assignment = LaneClassifier().classify(evidence("EV1", content=text))
        assert assignment.lane not in {EvidenceLane.SUPPORT, EvidenceLane.CONTRADICT}


def test_no_cue_yields_unclassified_and_defers_to_a_human():
    assignment = LaneClassifier().classify(evidence("EV1", title="Cohort profile"))
    assert assignment.lane is EvidenceLane.UNCLASSIFIED
    assert assignment.confidence == 0.0
    assert assignment.requires_human_adjudication is True


def test_every_assignment_is_flagged_for_adjudication():
    """The classifier is a screening pass, never a final code."""

    items = [
        evidence("EV1", content="no significant difference"),
        evidence("EV2", content="nothing notable here"),
    ]
    assert all(a.requires_human_adjudication for a in LaneClassifier().classify_all(items))


def test_confidence_rises_with_corroborating_cues_but_stays_capped():
    single = LaneClassifier().classify(evidence("EV1", content="no significant difference"))
    multiple = LaneClassifier().classify(
        evidence(
            "EV2",
            content="no significant difference, no association, and non-significant results",
        )
    )
    assert multiple.confidence > single.confidence
    assert multiple.confidence <= 0.9


def test_confidence_floor_downgrades_weak_matches_to_unclassified():
    strict = LaneClassifier(confidence_floor=0.95)
    assignment = strict.classify(evidence("EV1", content="no significant difference"))
    assert assignment.lane is EvidenceLane.UNCLASSIFIED
    assert assignment.matched_signals  # the cue is still reported for the human coder


def test_classifier_rejects_invalid_floor():
    with pytest.raises(ValueError):
        LaneClassifier(confidence_floor=0)


def test_coverage_reports_assigned_fraction():
    items = [
        evidence("EV1", content="no significant association"),
        evidence("EV2", content="ordinary descriptive text"),
    ]
    coverage = LaneClassifier().coverage(LaneClassifier().classify_all(items))
    assert coverage["total"] == 2
    assert coverage["assigned"] == 1
    assert coverage["assigned_fraction"] == pytest.approx(0.5)


# ------------------------------------------------------- inter-rater reliability


def test_kappa_is_one_for_identical_coders_and_zero_for_chance():
    labels = ["A", "B", "A", "B"]
    assert cohens_kappa(labels, labels).kappa == pytest.approx(1.0)

    # Perfectly opposed coders on a balanced two-label problem land at -1.
    assert cohens_kappa(["A", "A", "B", "B"], ["B", "B", "A", "A"]).kappa == pytest.approx(-1.0)


def test_kappa_exposes_the_dominant_category_trap():
    """High raw agreement with a dominant label can still mean poor reliability.

    This is why kappa is reported rather than percentage agreement: the lane
    distribution is overwhelmingly UNCLASSIFIED, so a coder who agrees 95% of the time
    may still be little better than chance.
    """

    first = ["UNCLASSIFIED"] * 95 + ["NULL"] * 5
    second = ["UNCLASSIFIED"] * 97 + ["NULL"] * 3
    report = cohens_kappa(first, second)
    assert report.observed_agreement > 0.90
    assert report.kappa < report.observed_agreement


def test_kappa_reports_directional_disagreements():
    report = cohens_kappa(["A", "A"], ["A", "B"])
    assert report.per_label_disagreement == {"A->B": 1}


def test_kappa_rejects_mismatched_or_empty_input():
    with pytest.raises(ValueError):
        cohens_kappa(["A"], ["A", "B"])
    with pytest.raises(ValueError):
        cohens_kappa([], [])


# -------------------------------------------------------------- drift simulation


def test_zero_drift_returns_the_original_labels():
    labels = ["A", "B", "C", "A"]
    assert simulate_coder_drift(true_labels=labels, drift_probability=0.0) == labels


def test_drift_degrades_kappa_monotonically():
    labels = (["A", "B", "C"] * 40)[:100]
    kappas = [
        cohens_kappa(
            labels, simulate_coder_drift(true_labels=labels, drift_probability=probability)
        ).kappa
        for probability in (0.0, 0.2, 0.5)
    ]
    assert kappas[0] > kappas[1] > kappas[2]


def test_drift_is_reproducible_for_a_fixed_seed():
    labels = ["A", "B"] * 20
    first = simulate_coder_drift(true_labels=labels, drift_probability=0.3, seed=11)
    second = simulate_coder_drift(true_labels=labels, drift_probability=0.3, seed=11)
    assert first == second


def test_drift_is_a_noop_when_only_one_label_exists():
    assert simulate_coder_drift(true_labels=["A"] * 5, drift_probability=1.0) == ["A"] * 5


def test_drift_rejects_invalid_input():
    with pytest.raises(ValueError):
        simulate_coder_drift(true_labels=["A"], drift_probability=1.5)
    with pytest.raises(ValueError):
        simulate_coder_drift(true_labels=[], drift_probability=0.1)
