"""Shared ISO timestamp / exact whole-minute conventions."""

from datetime import datetime, timedelta


def parse_datetime(value: str | datetime) -> datetime:
    """Parse an ISO 8601 timestamp, accepting both ``Z`` and offset notation."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Expected an ISO timestamp string, got {type(value).__name__}.")

    normalized_value = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise ValueError(f"Invalid ISO timestamp: {value!r}") from error


def datetime_to_minutes(
    value: str | datetime, horizon_start: str | datetime
) -> int:
    """Convert a timestamp to exact whole minutes relative to horizon start."""
    timestamp = parse_datetime(value)
    start = parse_datetime(horizon_start)
    try:
        total_seconds = (timestamp - start).total_seconds()
    except TypeError as error:
        raise ValueError(
            "Timestamps must use compatible timezone information."
        ) from error

    if not total_seconds.is_integer() or int(total_seconds) % 60 != 0:
        raise ValueError(
            f"Timestamp {timestamp.isoformat()} is not aligned to a whole minute."
        )
    return int(total_seconds) // 60


def minutes_to_datetime(
    minutes: int, horizon_start: str | datetime
) -> str:
    """Convert relative integer minutes back to an ISO 8601 timestamp."""
    if not isinstance(minutes, int):
        raise TypeError("Minutes must be an integer.")
    timestamp = parse_datetime(horizon_start) + timedelta(minutes=minutes)
    return timestamp.isoformat(timespec="seconds")


