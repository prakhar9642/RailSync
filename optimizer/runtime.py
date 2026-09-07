"""Runtime controls and proof states for lexicographic CP-SAT planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any


DEMO_SOLVE_LIMIT_SECONDS = 5.0

OBJECTIVE_STAGE_NAMES = (
    "criticality",
    "urgency",
    "overdue_days",
    "task_count",
    "possession_minutes",
    "block_count",
    "minimum_boundary_slack_minutes",
    "total_boundary_slack_minutes",
    "start_minutes",
)


class PlanProofState(str, Enum):
    FULLY_OPTIMAL = "FULLY_OPTIMAL"
    FEASIBLE_BOUNDED = "FEASIBLE_BOUNDED"
    INFEASIBLE = "INFEASIBLE"
    NO_SOLUTION = "NO_SOLUTION"


@dataclass(frozen=True)
class LexicographicSolveResult:
    """Final usable solver may come from an earlier proven stage."""

    solver_status: int
    solver: Any | None
    proof_state: PlanProofState
    last_stage_reached: str | None
    solution_stage: str | None


def validate_time_limit(value: float | None, name: str = "time_limit_seconds") -> None:
    if value is None:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be finite and positive.")
