from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Sequence

import numpy as np

from oslt_research.domain.enums import ClaimTier, EpistemicStatus, FindingDirection

from .simulation import SIMULATION_DISCLOSURE


#: What this module can and cannot conclude, carried on every result.
#:
#: Free-running simulation of participants answers nothing: the dependence between
#: exposure and outcome has to be assumed to generate the data, and that dependence is
#: what the proposition asks about. Calibrated simulation is different in one specific
#: way - the acceptance criterion is a REAL observed series. A mechanism that cannot
#: reproduce reality under any plausible parameter has been tested against something.
#:
#: The asymmetry is the whole point and must not be blurred. Failure to reproduce is
#: evidence against a mechanism. Success is not evidence for it, because other mechanisms
#: may reproduce the same series equally well.
CALIBRATION_DISCLOSURE = (
    SIMULATION_DISCLOSURE
    + " This result is calibrated against an observed series, so a mechanism that cannot "
    "reproduce that series under any admitted parameter is genuinely disfavoured. The "
    "converse does not hold: reproducing the series is compatibility, not confirmation, "
    "because rival mechanisms may reproduce it equally well. Every result also carries a "
    "severity, computed from the test itself, so that surviving a test which could not "
    "have failed is distinguishable from surviving one which most parameterisations would "
    "have failed. Corroboration is always reported AT a severity and never as support."
)


@dataclass(frozen=True)
class ObservedSeries:
    """A real aggregate series the simulation must reproduce.

    Aggregate published statistics are open data. Using them as the acceptance criterion
    is what separates this from inventing a dataset.
    """

    name: str
    source_id: str
    values: tuple[float, ...]
    periods: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.values) < 3:
            raise ValueError("an observed series needs at least three points to constrain anything")
        if self.periods and len(self.periods) != len(self.values):
            raise ValueError("periods and values must be the same length")


class SeverityBand(StrEnum):
    """How hard a calibration test would have been to survive.

    Severity is a property of the TEST, not of the mechanism. It answers Popper's
    question - "could this have killed the hypothesis?" - before any question about what
    the hypothesis did. A test that no admitted parameterisation could have failed is not
    evidence about anything, however cleanly it passed.
    """

    #: The test could barely have failed: survival carries no information at all.
    NEGLIGIBLE = "NEGLIGIBLE"
    #: A weak constraint. Survival is compatibility and nothing more.
    LOW = "LOW"
    #: A real but partial constraint. Still short of corroboration.
    MODERATE = "MODERATE"
    #: Most admitted parameterisations would have failed, on a tight tolerance, against
    #: a series with many independent periods. Survival here is hard-won.
    HIGH = "HIGH"


class Corroboration(StrEnum):
    """The third outcome the v1 vocabulary lacked.

    ``FindingDirection`` is the project-wide CLAIM vocabulary and deliberately has no
    value meaning "survived a severe test". Promoting survival into ``SUPPORTS`` there
    would be exactly the confirmationism the calibration disclosure forbids, because
    reproducing one aggregate series is a weak constraint many mechanisms satisfy. So the
    positive channel is opened here, in a simulation-only vocabulary, alongside an
    unchanged ``finding_direction``: survival can now be distinguished from silence
    without ever being reported as support for the proposition being true.
    """

    #: The mechanism was refuted; corroboration does not arise.
    NOT_APPLICABLE_REFUTED = "NOT_APPLICABLE_REFUTED"
    #: The mechanism survived a test it could hardly have failed. This is silence.
    NO_CORROBORATION_TEST_NOT_SEVERE = "NO_CORROBORATION_TEST_NOT_SEVERE"
    #: The mechanism survived a real but partial constraint. Compatibility, not more.
    COMPATIBLE_ONLY = "COMPATIBLE_ONLY"
    #: The mechanism survived a test most parameterisations would have failed. This is
    #: corroboration AT A STATED SEVERITY - never a statement that the mechanism is true.
    CORROBORATED_AT_HIGH_SEVERITY = "CORROBORATED_AT_HIGH_SEVERITY"


#: Lower bounds on the severity index for each band. Declared here rather than tuned per
#: run: a threshold chosen after seeing which side of it a result fell is not a threshold.
SEVERITY_BANDS: tuple[tuple[float, SeverityBand], ...] = (
    (0.60, SeverityBand.HIGH),
    (0.35, SeverityBand.MODERATE),
    (0.15, SeverityBand.LOW),
    (0.00, SeverityBand.NEGLIGIBLE),
)


@dataclass(frozen=True)
class TestSeverity:
    """A measured, reproducible answer to "could this test have failed?".

    Three factors, each in [0,1], combined as a geometric mean so that any one of them
    being zero drives severity to zero. That is the intended behaviour: a test whose grid
    could never have been rejected, or whose tolerance is wider than the series' own
    variation, or which constrains almost no independent periods, is uninformative no
    matter how well the other two factors score. An arithmetic mean would let two strong
    factors launder one fatal weakness into a respectable-looking number.
    """

    #: Fraction of the declared grid the test actually rejected. This is the direct
    #: answer to "what could have been killed here".
    rejection_fraction: float
    #: How tight the tolerance is relative to the observed series' own dispersion. At
    #: zero, a flat line through the mean would have passed.
    tolerance_tightness: float
    #: How many independent periods the series constrains. Three points constrain almost
    #: nothing; eighty-four constrain a great deal.
    series_constraint: float
    index: float
    band: SeverityBand
    periods: int

    def explain(self) -> str:
        return (
            f"severity {self.index:.2f} ({self.band.value}): the test rejected "
            f"{self.rejection_fraction:.0%} of the declared grid, its tolerance is "
            f"{self.tolerance_tightness:.0%} tight against the series' own dispersion, "
            f"and the series constrains {self.periods} periods"
        )


def _band_for(index: float) -> SeverityBand:
    for threshold, band in SEVERITY_BANDS:
        if index >= threshold:
            return band
    return SeverityBand.NEGLIGIBLE


def assess_severity(
    *,
    grid_size: int,
    accepted: int,
    tolerance: float,
    observed: ObservedSeries,
) -> TestSeverity:
    """Compute how severe a calibration test was, from the test itself.

    Everything here is read off the run: the grid that was declared, the tolerance that
    was declared, and the series that was used. Nothing is asserted by the analyst, which
    is the point - a severity anyone can recompute cannot be talked up after the fact.
    """

    rejection_fraction = (grid_size - accepted) / grid_size if grid_size else 0.0

    values = np.asarray(observed.values, dtype=float)
    spread = float(values.max() - values.min())
    if spread <= 0:
        spread = float(abs(values.mean())) or 1.0
    # Dispersion is expressed in the SAME units as normalised_rmse, so the comparison
    # with the tolerance is like-for-like: a tolerance at or above the dispersion would
    # admit a flat line at the series mean, which is no test at all.
    dispersion = float(values.std()) / spread
    tolerance_tightness = 0.0 if dispersion <= 0 else max(0.0, 1.0 - tolerance / dispersion)

    periods = len(observed.values)
    # Two points fix a level and a slope; only what is left over constrains a shape.
    series_constraint = max(0.0, (periods - 2) / periods)

    index = float(
        (rejection_fraction * tolerance_tightness * series_constraint) ** (1.0 / 3.0)
    )
    return TestSeverity(
        rejection_fraction=rejection_fraction,
        tolerance_tightness=tolerance_tightness,
        series_constraint=series_constraint,
        index=index,
        band=_band_for(index),
        periods=periods,
    )


@dataclass(frozen=True)
class MechanismCandidate:
    """A named mechanism and the parameter grid considered plausible for it.

    The grid is a declared prior. Widening it after seeing the result converts a
    falsification into a fitting exercise, so it belongs in the preregistration.
    """

    mechanism_id: str
    description: str
    simulate: Callable[[dict[str, float], int], Sequence[float]]
    parameter_grid: dict[str, tuple[float, ...]]

    def grid_points(self) -> list[dict[str, float]]:
        names = sorted(self.parameter_grid)
        points: list[dict[str, float]] = [{}]
        for name in names:
            points = [
                {**point, name: value} for point in points for value in self.parameter_grid[name]
            ]
        return points


@dataclass(frozen=True)
class CalibrationResult:
    mechanism_id: str
    observed: str
    grid_size: int
    accepted: int
    tolerance: float
    best_distance: float
    best_parameters: dict[str, float] = field(default_factory=dict)
    finding_direction: FindingDirection = FindingDirection.INCONCLUSIVE
    corroboration: Corroboration = Corroboration.NOT_APPLICABLE_REFUTED
    severity: TestSeverity | None = None
    narrative: str = ""
    epistemic_status: EpistemicStatus = field(default=EpistemicStatus.SIMULATION, init=False)
    claim_tier: ClaimTier = field(default=ClaimTier.SIMULATION_ONLY, init=False)
    disclosure: str = field(default=CALIBRATION_DISCLOSURE, init=False)

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.grid_size if self.grid_size else 0.0

    @property
    def severity_band(self) -> SeverityBand:
        return self.severity.band if self.severity else SeverityBand.NEGLIGIBLE

    @property
    def severity_index(self) -> float:
        return self.severity.index if self.severity else 0.0

    @property
    def corroborated(self) -> bool:
        """Survived a test most admitted parameterisations would have failed.

        Read this as "corroborated at severity X", never as "supported". The distinction
        is the whole reason the value lives in its own vocabulary.
        """

        return self.corroboration is Corroboration.CORROBORATED_AT_HIGH_SEVERITY

    @property
    def refuted(self) -> bool:
        """No admitted parameter reproduced the observed series."""

        return self.accepted == 0


def normalised_rmse(simulated: Sequence[float], observed: Sequence[float]) -> float:
    """Root mean squared error scaled by the observed range.

    Scaling makes the tolerance comparable across series measured on different units,
    which matters because the tolerance is declared in advance rather than tuned.
    """

    if len(simulated) != len(observed):
        raise ValueError("simulated and observed series must be the same length")
    sim = np.asarray(simulated, dtype=float)
    obs = np.asarray(observed, dtype=float)
    spread = float(obs.max() - obs.min())
    if spread <= 0:
        spread = float(abs(obs.mean())) or 1.0
    return float(np.sqrt(np.mean((sim - obs) ** 2)) / spread)


def calibrate_mechanism(
    candidate: MechanismCandidate,
    observed: ObservedSeries,
    *,
    tolerance: float = 0.15,
) -> CalibrationResult:
    """Reject every parameterisation that fails to reproduce the observed series.

    Rejection sampling over a declared grid. The tolerance and the grid are both stated in
    advance; loosening either after seeing the outcome turns a test into a fit, which is
    why both belong in the frozen specification.
    """

    if not 0 < tolerance < 1:
        raise ValueError("tolerance must be a fraction of the observed range in (0,1)")

    points = candidate.grid_points()
    if not points:
        raise ValueError("mechanism has an empty parameter grid")

    accepted: list[dict[str, float]] = []
    best_distance = float("inf")
    best_parameters: dict[str, float] = {}

    for point in points:
        simulated = candidate.simulate(point, len(observed.values))
        distance = normalised_rmse(simulated, observed.values)
        if distance < best_distance:
            best_distance, best_parameters = distance, point
        if distance <= tolerance:
            accepted.append(point)

    severity = assess_severity(
        grid_size=len(points),
        accepted=len(accepted),
        tolerance=tolerance,
        observed=observed,
    )

    if not accepted:
        direction = FindingDirection.WEAKENS
        corroboration = Corroboration.NOT_APPLICABLE_REFUTED
        narrative = (
            f"No parameterisation in the declared grid ({len(points)} points) reproduced "
            f"{observed.name} within a tolerance of {tolerance:.0%} of its range; the closest "
            f"managed {best_distance:.0%}. On this series and this grid the mechanism is "
            "disfavoured. Widening the grid after the fact would convert this into a fitting "
            "exercise and is not a rebuttal. " + severity.explain() + "."
        )
    else:
        # The claim vocabulary does not move. Survival is recorded in `corroboration`,
        # which is the only field allowed to register it, and only at HIGH severity.
        direction = FindingDirection.INCONCLUSIVE
        if severity.band is SeverityBand.HIGH:
            corroboration = Corroboration.CORROBORATED_AT_HIGH_SEVERITY
            verdict = (
                f"The mechanism is CORROBORATED AT SEVERITY {severity.index:.2f} "
                f"({severity.band.value}): most admitted parameterisations would have "
                "failed and this one did not. Corroboration-at-severity is a statement "
                "about how hard the test was to survive, NOT a statement that the "
                "mechanism is true or that the proposition is supported."
            )
        elif severity.band is SeverityBand.NEGLIGIBLE:
            corroboration = Corroboration.NO_CORROBORATION_TEST_NOT_SEVERE
            verdict = (
                "The test was not severe enough to have failed, so survival carries no "
                "information: this is silence, not a result."
            )
        else:
            corroboration = Corroboration.COMPATIBLE_ONLY
            verdict = (
                f"Severity is {severity.band.value}, below the bar for corroboration. "
                "The mechanism is COMPATIBLE with the observed series and no more."
            )
        narrative = (
            f"{len(accepted)} of {len(points)} parameterisations reproduced {observed.name} "
            f"within {tolerance:.0%}. {verdict} "
            "This is not support: compatibility is cheap, and rival mechanisms must be run "
            "against the same series before any comparative statement is possible. "
            + severity.explain()
            + "."
        )

    return CalibrationResult(
        mechanism_id=candidate.mechanism_id,
        observed=observed.name,
        grid_size=len(points),
        accepted=len(accepted),
        tolerance=tolerance,
        best_distance=best_distance,
        best_parameters=best_parameters,
        finding_direction=direction,
        corroboration=corroboration,
        severity=severity,
        narrative=narrative,
    )


def compare_mechanisms(
    candidates: Sequence[MechanismCandidate],
    observed: ObservedSeries,
    *,
    tolerance: float = 0.15,
) -> dict[str, object]:
    """Run rival mechanisms against the same series.

    The only comparative statement this licenses is elimination: which mechanisms could
    not reproduce reality. Among survivors it stays silent, because equal compatibility
    with one aggregate series does not rank explanations - that is what individual-level
    designs are for, and no amount of simulation substitutes for them.
    """

    results = [calibrate_mechanism(item, observed, tolerance=tolerance) for item in candidates]
    refuted = [item.mechanism_id for item in results if item.refuted]
    survivors = [item.mechanism_id for item in results if not item.refuted]
    corroborated = [item.mechanism_id for item in results if item.corroborated]

    return {
        "observed_series": observed.name,
        "observed_source": observed.source_id,
        "tolerance": tolerance,
        "refuted": refuted,
        "compatible": survivors,
        "corroborated_at_high_severity": corroborated,
        "severity": {
            item.mechanism_id: {
                "index": item.severity_index,
                "band": item.severity_band.value,
                "corroboration": item.corroboration.value,
            }
            for item in results
        },
        "results": results,
        "interpretation_bound": (
            "Refuted mechanisms failed to reproduce a real observed series and are "
            "genuinely disfavoured. Compatible mechanisms are NOT ranked against each "
            "other: reproducing one aggregate series is a weak constraint that many "
            "mechanisms satisfy. No compatible mechanism may be reported as supported. "
            "Where a survivor is listed under corroborated_at_high_severity, that records "
            "only that the test it survived was one most admitted parameterisations would "
            "have failed; it is corroboration at a stated severity and still may not be "
            "reported as support for the proposition being true."
        ),
        "claim_tier": ClaimTier.SIMULATION_ONLY.value,
    }
