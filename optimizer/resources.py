"""Explicit synthetic resource pools and section power windows; no default roster."""

from dataclasses import dataclass, field
from typing import Mapping

try:
    from .time_utils import datetime_to_minutes
except ImportError:
    from time_utils import datetime_to_minutes


@dataclass(frozen=True)
class PowerWindow:
    start_time: str
    end_time: str


@dataclass(frozen=True)
class ResourceContext:
    # Pools are shared globally across sections. Each task consumes one unit for
    # its entire setup/work/release reservation; no inferred travel or roster.
    crew_capacities: Mapping[str, int] = field(default_factory=dict)
    machine_capacities: Mapping[str, int] = field(default_factory=dict)
    # Absent section = unknown; present empty sequence = explicitly unavailable.
    power_windows: Mapping[str, tuple[PowerWindow, ...]] = field(default_factory=dict)

    def __post_init__(self):
        for pools in (self.crew_capacities, self.machine_capacities):
            for name, capacity in pools.items():
                if not isinstance(name, str) or not name:
                    raise ValueError("Resource pool names must be non-empty strings.")
                if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
                    raise ValueError("Resource capacities must be non-negative integers.")

    def validate_times(self, origin):
        for section in self.power_windows:
            power_intervals(self, section, origin)


def power_intervals(context, section, origin):
    """Union touching/overlapping availability before testing full reservations."""
    merged = []
    intervals = []
    for window in context.power_windows.get(section, ()):
        start = datetime_to_minutes(window.start_time, origin)
        end = datetime_to_minutes(window.end_time, origin)
        if start >= end:
            raise ValueError("Power window must start before it ends.")
        intervals.append((start, end))
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def power_start_ranges(task, duration, earliest, latest, origin, context):
    """Inclusive legal start ranges, relative to origin; all overhead needs power."""
    if earliest > latest:
        return []
    required = task.get("requires_power_block", False) or task.get("requires_power_isolation", False)
    if not required or context is None or task["section_id"] not in context.power_windows:
        return [(earliest, latest)]
    return [
        (max(earliest, start), min(latest, end - duration))
        for start, end in power_intervals(context, task["section_id"], origin)
        if max(earliest, start) <= min(latest, end - duration)
    ]


def add_capacity_constraints(model, tasks, variables, context):
    if context is None:
        return
    for field_name, pools in (("crew_type", context.crew_capacities), ("machine_type", context.machine_capacities)):
        for pool, capacity in pools.items():
            intervals = [variables[t["task_id"]]["interval"] for t in tasks if t.get(field_name) == pool]
            if intervals:
                model.AddCumulative(intervals, [1] * len(intervals), capacity)


def validate_capacities(reservations, context):
    """Independent sweep: end events precede starts at equal timestamps."""
    if context is None:
        return
    for field_name, pools in (("crew_type", context.crew_capacities), ("machine_type", context.machine_capacities)):
        for pool, capacity in pools.items():
            events = []
            for task, start, end in reservations:
                if task.get(field_name) == pool:
                    events.extend(((start, 1), (end, -1)))
            used = 0
            for _, change in sorted(events):
                used += change
                if used > capacity:
                    raise ValueError(f"{field_name} capacity exceeded: {pool}")
