"""Deterministic nominal gaps and safety-adjusted windows (allowance model B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

try:
    from .time_utils import datetime_to_minutes, minutes_to_datetime, parse_datetime
except ImportError:  # Direct script / existing test imports.
    from time_utils import datetime_to_minutes, minutes_to_datetime, parse_datetime


@dataclass(frozen=True)
class OperationalAllowances:
    """Prototype minutes, NOT official railway rules; task overhead is separate."""

    safety_after_minutes: int = 15
    safety_before_minutes: int = 15
    setup_minutes: int = 10
    release_minutes: int = 5

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")


@dataclass(frozen=True)
class CandidateWindow:
    window_id: str
    section_id: str
    nominal_start: str
    nominal_end: str
    usable_start: str
    usable_end: str
    nominal_minutes: int
    usable_minutes: int
    margin_before_minutes: int
    margin_after_minutes: int


def generate_candidate_windows(
    train_occupancy: list[dict[str, Any]],
    section_ids: Iterable[str],
    horizon_start: str | datetime,
    horizon_end: str | datetime,
    allowances: OperationalAllowances = OperationalAllowances(),
) -> list[CandidateWindow]:
    """Merge overlapping/touching occupancies and shrink their complement.

    Include outside-horizon trains when their safety margins reach the horizon.
    Empty usable windows are retained for diagnostics, with equal endpoints.
    Setup/release are NOT subtracted here; feasibility reserves them per task.
    """
    origin = parse_datetime(horizon_start)
    horizon = datetime_to_minutes(horizon_end, origin)
    if horizon <= 0:
        raise ValueError("horizon_end must be later than horizon_start.")
    sections = sorted(set(section_ids))
    by_section: dict[str, list[tuple[int, int]]] = {s: [] for s in sections}
    for row in train_occupancy:
        entry = datetime_to_minutes(row["entry_time"], origin)
        exit_time = datetime_to_minutes(row["exit_time"], origin)
        if entry >= exit_time:
            raise ValueError("Train occupancy must enter before it exits.")
        if row["section_id"] in by_section:
            by_section[row["section_id"]].append((entry, exit_time))

    result = []
    for section in sections:
        merged: list[tuple[int, int]] = []
        for start, end in sorted(by_section[section]):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        # Unbounded outer gaps are clipped only after train safety is applied.
        boundaries = [(None, merged[0][0])] if merged else [(None, None)]
        boundaries += [(a[1], b[0]) for a, b in zip(merged, merged[1:])]
        if merged:
            boundaries.append((merged[-1][1], None))
        count = 0
        for previous_exit, next_entry in boundaries:
            nominal_start = max(0, previous_exit) if previous_exit is not None else 0
            nominal_end = min(horizon, next_entry) if next_entry is not None else horizon
            if nominal_start >= nominal_end:
                continue
            safe_start = nominal_start
            safe_end = nominal_end
            if previous_exit is not None:
                safe_start = max(safe_start, previous_exit + allowances.safety_after_minutes)
            if next_entry is not None:
                safe_end = min(safe_end, next_entry - allowances.safety_before_minutes)
            usable_start = min(nominal_end, safe_start)
            usable_end = max(usable_start, safe_end)
            count += 1
            result.append(CandidateWindow(
                window_id=f"WIN_{section}_{count:03d}", section_id=section,
                nominal_start=minutes_to_datetime(nominal_start, origin),
                nominal_end=minutes_to_datetime(nominal_end, origin),
                usable_start=minutes_to_datetime(usable_start, origin),
                usable_end=minutes_to_datetime(usable_end, origin),
                nominal_minutes=nominal_end - nominal_start,
                usable_minutes=usable_end - usable_start,
                margin_before_minutes=usable_start - nominal_start,
                margin_after_minutes=nominal_end - usable_end,
            ))
    return result
