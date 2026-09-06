"""Pure task/window feasibility facts, with no fabricated resource calendars."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

try:
    from .candidate_windows import CandidateWindow, OperationalAllowances
    from .time_utils import datetime_to_minutes, minutes_to_datetime
except ImportError:
    from candidate_windows import CandidateWindow, OperationalAllowances
    from time_utils import datetime_to_minutes, minutes_to_datetime


class ReasonCode(str, Enum):
    WRONG_SECTION = "WRONG_SECTION"
    INSUFFICIENT_USABLE_DURATION = "INSUFFICIENT_USABLE_DURATION"
    DEADLINE_VIOLATION = "DEADLINE_VIOLATION"
    POWER_BLOCK_UNAVAILABLE = "POWER_BLOCK_UNAVAILABLE"
    CREW_UNAVAILABLE = "CREW_UNAVAILABLE"
    MACHINE_UNAVAILABLE = "MACHINE_UNAVAILABLE"


class ResourceCheckStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_EVALUATED = "NOT_EVALUATED"


def _resource_check(required: bool, available: bool | None) -> ResourceCheckStatus:
    if not required:
        return ResourceCheckStatus.NOT_EVALUATED
    if available is True:
        return ResourceCheckStatus.PASSED
    if available is False:
        return ResourceCheckStatus.FAILED
    return ResourceCheckStatus.UNKNOWN


@dataclass(frozen=True)
class FeasibilityContext:
    """Availability applies throughout ONE window; absent keys mean unknown.

    These booleans are eligibility checks, not shared resource capacity/rosters.
    """

    power_available: bool | None = None
    crew_availability: Mapping[str, bool] = field(default_factory=dict)
    machine_availability: Mapping[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskRequirements:
    duration_minutes: int
    setup_minutes: int
    release_minutes: int
    requires_power_isolation: bool
    crew_type: str | None
    machine_type: str | None
    preferred_window: str | None = None
    splittable: bool = False

    @property
    def required_minutes(self) -> int:
        return self.setup_minutes + self.duration_minutes + self.release_minutes


def task_requirements(
    task: Mapping[str, Any],
    allowances: OperationalAllowances = OperationalAllowances(),
) -> TaskRequirements:
    """Optional task overhead OVERRIDES defaults; duration is productive work.

    Preference and splitting metadata are retained but not acted on this phase.
    """
    minutes = {}
    for name, default in (
        ("duration_minutes", None),
        ("setup_minutes", allowances.setup_minutes),
        ("release_minutes", allowances.release_minutes),
    ):
        value = task.get(name, default)
        minimum = 1 if name == "duration_minutes" else 0
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"Invalid {name}: expected integer minutes >= {minimum}.")
        minutes[name] = value
    return TaskRequirements(
        **minutes,
        requires_power_isolation=bool(task.get("requires_power_block", False) or task.get("requires_power_isolation", False)),
        crew_type=task.get("crew_type"), machine_type=task.get("machine_type"),
        preferred_window=task.get("preferred_window"), splittable=task.get("splittable", False),
    )


@dataclass(frozen=True)
class FeasibilityResult:
    feasible: bool
    required_minutes: int
    usable_minutes: int
    slack_minutes: int
    reasons: tuple[ReasonCode, ...]
    latest_reservation_start: str
    resource_checks: dict[str, ResourceCheckStatus]


def evaluate_task_in_window(
    task: Mapping[str, Any],
    window: CandidateWindow,
    context: FeasibilityContext | None = None,
    allowances: OperationalAllowances = OperationalAllowances(),
    *,
    reservation_start: str | None = None,
) -> FeasibilityResult:
    """Check earliest execution or an actual reservation, including release deadline.

    latest_reservation_start must also constrain CP-SAT: a feasible earliest
    placement does not mean all later placements meet the deadline.
    """
    requirement = task_requirements(task, allowances)
    context = context or FeasibilityContext()
    required = requirement.required_minutes
    start = 0 if reservation_start is None else datetime_to_minutes(reservation_start, window.usable_start)
    latest = window.usable_minutes - required
    reasons = []
    if task["section_id"] != window.section_id:
        reasons.append(ReasonCode.WRONG_SECTION)
    if start < 0 or start + required > window.usable_minutes:
        reasons.append(ReasonCode.INSUFFICIENT_USABLE_DURATION)
    if task.get("deadline"):
        deadline_latest = datetime_to_minutes(task["deadline"], window.usable_start) - required
        latest = min(latest, deadline_latest)
        if start > deadline_latest:
            reasons.append(ReasonCode.DEADLINE_VIOLATION)
    resource_checks = {
        "power": _resource_check(requirement.requires_power_isolation, context.power_available),
        "crew": _resource_check(bool(requirement.crew_type), context.crew_availability.get(requirement.crew_type)),
        "machine": _resource_check(bool(requirement.machine_type), context.machine_availability.get(requirement.machine_type)),
    }
    for resource, reason in (
        ("power", ReasonCode.POWER_BLOCK_UNAVAILABLE),
        ("crew", ReasonCode.CREW_UNAVAILABLE),
        ("machine", ReasonCode.MACHINE_UNAVAILABLE),
    ):
        if resource_checks[resource] == ResourceCheckStatus.FAILED:
            reasons.append(reason)
    return FeasibilityResult(
        feasible=not reasons, required_minutes=required,
        usable_minutes=window.usable_minutes,
        slack_minutes=window.usable_minutes - required,
        reasons=tuple(reasons),
        latest_reservation_start=minutes_to_datetime(latest, window.usable_start),
        resource_checks=resource_checks,
    )
