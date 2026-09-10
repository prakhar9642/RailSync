"""Public package surface for the RailSync CP-SAT optimizer."""

from .optimizer import (
    DEFAULT_HORIZON_END,
    DEFAULT_HORIZON_START,
    calculate_metrics,
    load_mock_data,
    optimize_schedule,
    validate_solution,
)
from .feasibility import task_requirements
from .time_utils import datetime_to_minutes, minutes_to_datetime

__all__ = [
    "DEFAULT_HORIZON_END",
    "DEFAULT_HORIZON_START",
    "calculate_metrics",
    "datetime_to_minutes",
    "load_mock_data",
    "minutes_to_datetime",
    "optimize_schedule",
    "task_requirements",
    "validate_solution",
]
