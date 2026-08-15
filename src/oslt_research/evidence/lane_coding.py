from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

from oslt_research.domain.enums import EvidenceLane
from oslt_research.domain.models import EvidenceObject


@dataclass(frozen=True)
class LaneAssignment:
    evidence_id: str
    lane: EvidenceLane
    confidence: float
    matched_signals: list[str] = field(default_factory=list)
    requires_human_adjudication: bool = True
    rationale: str = ""


#: Lane cues, ordered by precedence. A retraction outranks everything: a retracted paper
#: is a correction record regardless of what it originally claimed.
LANE_SIGNALS: tuple[tuple[EvidenceLane, tuple[str, ...]], ...] = (
    (
        EvidenceLane.CORRECTION_RETRACTION,
        (
            r"\bretract(ed|ion|ions)\b",
            r"\berrat(um|a)\b",
            r"\bcorrigend(um|a)\b",
            r"\bexpression of concern\b",
            r"\bwithdrawn\b",
            r"\bnotice of correction\b",
        ),
    ),
    (
        EvidenceLane.REPLICATION,
        (
            r"\breplicat(e|ed|ion|ions)\b",
            r"\breproduc(e|ed|ibility|tion)\b",
            r"\bindependent (cohort|sample|validation)\b",
            r"\bexternal validation\b",
        ),
    ),
    (
        EvidenceLane.BIAS_CRITIQUE,
        (
            r"\brisk of bias\b",
            r"\bselection bias\b",
            r"\bascertainment bias\b",
            r"\bmethodological (limitation|concern|critique|flaw)",
            r"\bcritique\b",
            r"\bcommentary on\b",
            r"\bre-?analysis\b",
            r"\bconfounding\b",
        ),
    ),
    (
        EvidenceLane.NULL,
        (
            r"\bno (statistically )?significant\b",
            r"\bno (evidence|association|difference|effect|relationship)\b",
            r"\bnull (result|finding|hypothesis was not rejected)\b",
            r"\bdid not differ\b",
            r"\bfailed to (find|detect|show)\b",
            r"\bnon-?significant\b",
        ),
    ),
    (
        EvidenceLane.RIVAL,
        (
            r"\balternative explanation\b",
            r"\bcompeting (model|hypothes[ei]s|explanation)\b",
            r"\brival (model|hypothes[ei]s|explanation)\b",
            r"\breverse causation\b",
            r"\bcommon cause\b",
        ),
    ),
)

_COMPILED = tuple(
    (lane, tuple(re.compile(pattern, re.I) for pattern in patterns))
    for lane, patterns in LANE_SIGNALS
)

#: Below this, the classifier declines to assign and defers to a human coder.
CONFIDENCE_FLOOR = 0.55


class LaneClassifier:
    """First-pass automated lane coder.

    Deliberately transparent rather than learned: every assignment names the cues that
    produced it, so a human adjudicator can see why and disagree. It is UNCALIBRATED
    until scored against a human-coded validation sample, and its output must not be
    treated as coded evidence before that.

    SUPPORT and CONTRADICT are never assigned. Those lanes are relative to a specific
    proposition - the same result supports one model family and contradicts another - so
    they cannot be read off a text in isolation. Anything that looks directional is
    routed to human adjudication instead of being guessed.
    """

    def __init__(self, *, confidence_floor: float = CONFIDENCE_FLOOR):
        if not 0 < confidence_floor <= 1:
            raise ValueError("confidence_floor must be in (0,1]")
        self.confidence_floor = confidence_floor

    @staticmethod
    def _text(item: EvidenceObject) -> str:
        return f"{item.title}\n{item.content}"

    def classify(self, item: EvidenceObject) -> LaneAssignment:
        text = self._text(item)
        for lane, patterns in _COMPILED:
            hits = [pattern.pattern for pattern in patterns if pattern.search(text)]
            if not hits:
                continue
            # Confidence rises with corroborating cues but is capped well below
            # certainty: these are surface features, not comprehension.
            confidence = min(0.9, 0.5 + 0.15 * len(hits))
            below_floor = confidence < self.confidence_floor
            return LaneAssignment(
                evidence_id=item.evidence_id,
                lane=EvidenceLane.UNCLASSIFIED if below_floor else lane,
                confidence=confidence,
                matched_signals=hits,
                requires_human_adjudication=True,
                rationale=(
                    f"{len(hits)} surface cue(s) for {lane.value}. Automated coding is a "
                    "screening pass and every assignment remains open to adjudication."
                ),
            )

        return LaneAssignment(
            evidence_id=item.evidence_id,
            lane=EvidenceLane.UNCLASSIFIED,
            confidence=0.0,
            matched_signals=[],
            requires_human_adjudication=True,
            rationale=(
                "No lane cue matched. SUPPORT and CONTRADICT are proposition-relative and "
                "are never assigned automatically, so this record needs a human coder."
            ),
        )

    def classify_all(self, evidence: Iterable[EvidenceObject]) -> list[LaneAssignment]:
        return [self.classify(item) for item in evidence]

    @staticmethod
    def coverage(assignments: Sequence[LaneAssignment]) -> dict[str, float | int]:
        counts = Counter(assignment.lane.value for assignment in assignments)
        total = len(assignments)
        assigned = total - counts.get(EvidenceLane.UNCLASSIFIED.value, 0)
        return {
            "total": total,
            "assigned": assigned,
            "unclassified": counts.get(EvidenceLane.UNCLASSIFIED.value, 0),
            "assigned_fraction": (assigned / total) if total else 0.0,
            **{f"lane_{name}": value for name, value in counts.items()},
        }


# ------------------------------------------------------------ inter-rater reliability


@dataclass(frozen=True)
class AgreementReport:
    n: int
    observed_agreement: float
    expected_agreement: float
    kappa: float
    interpretation: str
    per_label_disagreement: dict[str, int] = field(default_factory=dict)


def cohens_kappa(first: Sequence[str], second: Sequence[str]) -> AgreementReport:
    """Cohen's kappa between two coders over the same items.

    Raw percentage agreement flatters any coding scheme with a dominant category, which
    this one has: most records match no cue. Kappa corrects for agreement by chance.
    """

    if len(first) != len(second):
        raise ValueError("coder sequences must be the same length")
    if not first:
        raise ValueError("cannot compute agreement over zero items")

    n = len(first)
    labels = sorted(set(first) | set(second))
    observed = sum(1 for a, b in zip(first, second) if a == b) / n

    first_counts = Counter(first)
    second_counts = Counter(second)
    expected = sum(
        (first_counts[label] / n) * (second_counts[label] / n) for label in labels
    )

    kappa = 1.0 if expected >= 1.0 else (observed - expected) / (1 - expected)

    if kappa < 0.20:
        reading = "POOR: coding scheme is not usable as it stands."
    elif kappa < 0.40:
        reading = "FAIR: substantial revision of the codebook needed."
    elif kappa < 0.60:
        reading = "MODERATE: usable only with adjudication of every disagreement."
    elif kappa < 0.80:
        reading = "SUBSTANTIAL: acceptable for research use with adjudication."
    else:
        reading = "ALMOST PERFECT: scheme is reliable between these coders."

    disagreement: Counter[str] = Counter()
    for a, b in zip(first, second):
        if a != b:
            disagreement[f"{a}->{b}"] += 1

    return AgreementReport(
        n=n,
        observed_agreement=observed,
        expected_agreement=expected,
        kappa=kappa,
        interpretation=reading,
        per_label_disagreement=dict(disagreement),
    )


def simulate_coder_drift(
    *,
    true_labels: Sequence[str],
    drift_probability: float,
    label_pool: Sequence[str] | None = None,
    seed: int = 20260815,
) -> list[str]:
    """Perturb a label sequence to emulate a drifting or careless second coder.

    This is a harness-validation tool, not a data source. It exists so the kappa
    machinery and the adjudication queue can be exercised end to end before any human
    coder spends time on the corpus, and so the study can state in advance what level of
    coder drift would push kappa below an acceptable threshold.

    It never produces evidence: the labels it emits are known-synthetic and must not be
    persisted as codes for real records.
    """

    if not 0 <= drift_probability <= 1:
        raise ValueError("drift_probability must be in [0,1]")
    if not true_labels:
        raise ValueError("true_labels must not be empty")

    pool = list(label_pool or sorted(set(true_labels)))
    if len(pool) < 2:
        return list(true_labels)

    rng = np.random.default_rng(seed)
    drifted: list[str] = []
    for label in true_labels:
        if rng.random() < drift_probability:
            alternatives = [option for option in pool if option != label]
            drifted.append(str(rng.choice(alternatives)))
        else:
            drifted.append(label)
    return drifted
