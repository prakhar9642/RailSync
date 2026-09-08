"""Adapter for explicit synthetic optimizer resource contexts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from optimizer.resources import PowerWindow, ResourceContext

SYNTHETIC_PROVENANCE = {"SYNTHETIC_PROTOTYPE", "TEST_FIXTURE"}


def load_resource_context(path: Path) -> tuple[ResourceContext, str]:
    """Load capacities and power windows without inventing defaults."""
    try:
        with path.open(encoding="utf-8") as handle:
            raw: Any = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load resource context from {path}: {error}") from error

    if not isinstance(raw, dict):
        raise ValueError("Resource context must contain a JSON object.")
    required = {"provenance", "crew_capacities", "machine_capacities", "power_windows"}
    missing = sorted(required - raw.keys())
    if missing:
        raise ValueError(f"Resource context is missing: {', '.join(missing)}.")
    provenance = raw["provenance"]
    if provenance not in SYNTHETIC_PROVENANCE:
        raise ValueError("Resource context provenance must be explicitly synthetic.")

    for field_name in ("crew_capacities", "machine_capacities", "power_windows"):
        if not isinstance(raw[field_name], dict):
            raise ValueError(f"Resource context {field_name} must be an object.")

    power_windows: dict[str, tuple[PowerWindow, ...]] = {}
    for section_id, windows in raw["power_windows"].items():
        if not isinstance(section_id, str) or not section_id or not isinstance(windows, list):
            raise ValueError("Power windows must map section IDs to lists.")
        parsed = []
        for window in windows:
            if not isinstance(window, dict) or not all(
                isinstance(window.get(field), str) and window[field]
                for field in ("start_time", "end_time")
            ):
                raise ValueError(f"Invalid power window for section {section_id!r}.")
            parsed.append(PowerWindow(window["start_time"], window["end_time"]))
        power_windows[section_id] = tuple(parsed)

    return (
        ResourceContext(
            crew_capacities=raw["crew_capacities"],
            machine_capacities=raw["machine_capacities"],
            power_windows=power_windows,
        ),
        provenance,
    )
