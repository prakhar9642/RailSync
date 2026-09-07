"""Adapter for frozen JSON-list snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Collection


def load_json_list(
    path: Path,
    *,
    dataset_name: str,
    required_fields: Collection[str],
) -> list[dict[str, Any]]:
    """Load a JSON list and enforce the canonical record boundary."""
    try:
        with path.open(encoding="utf-8") as handle:
            records = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load {dataset_name!r} from {path}: {error}") from error

    if not isinstance(records, list):
        raise ValueError(f"Dataset {dataset_name!r} must contain a JSON list.")

    required = set(required_fields)
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(
                f"Dataset {dataset_name!r} record {index} must be a JSON object."
            )
        missing = sorted(required - record.keys())
        if missing:
            raise ValueError(
                f"Dataset {dataset_name!r} record {index} is missing: "
                f"{', '.join(missing)}."
            )
    return records
