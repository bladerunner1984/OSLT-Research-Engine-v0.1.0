from __future__ import annotations

from dataclasses import dataclass, field
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
    "because rival mechanisms may reproduce it equally well."
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
    narrative: str = ""
    epistemic_status: EpistemicStatus = field(default=EpistemicStatus.SIMULATION, init=False)
    claim_tier: ClaimTier = field(default=ClaimTier.SIMULATION_ONLY, init=False)
    disclosure: str = field(default=CALIBRATION_DISCLOSURE, init=False)

    @property
    def acceptance_rate(self) -> float:
        return self.accepted / self.grid_size if self.grid_size else 0.0

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

    if not accepted:
        direction = FindingDirection.WEAKENS
        narrative = (
            f"No parameterisation in the declared grid ({len(points)} points) reproduced "
            f"{observed.name} within a tolerance of {tolerance:.0%} of its range; the closest "
            f"managed {best_distance:.0%}. On this series and this grid the mechanism is "
            "disfavoured. Widening the grid after the fact would convert this into a fitting "
            "exercise and is not a rebuttal."
        )
    else:
        direction = FindingDirection.INCONCLUSIVE
        narrative = (
            f"{len(accepted)} of {len(points)} parameterisations reproduced {observed.name} "
            f"within {tolerance:.0%}. The mechanism is COMPATIBLE with the observed series. "
            "This is not support: compatibility is cheap, and rival mechanisms must be run "
            "against the same series before any comparative statement is possible."
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

    return {
        "observed_series": observed.name,
        "observed_source": observed.source_id,
        "tolerance": tolerance,
        "refuted": refuted,
        "compatible": survivors,
        "results": results,
        "interpretation_bound": (
            "Refuted mechanisms failed to reproduce a real observed series and are "
            "genuinely disfavoured. Compatible mechanisms are NOT ranked against each "
            "other: reproducing one aggregate series is a weak constraint that many "
            "mechanisms satisfy. No compatible mechanism may be reported as supported."
        ),
        "claim_tier": ClaimTier.SIMULATION_ONLY.value,
    }
