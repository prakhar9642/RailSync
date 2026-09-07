"""Validate every populated RailSync territory."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent
PROJECT_ROOT = DATA_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.territories import PLACEHOLDER, list_territories, load_territory  # noqa: E402


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def validate_records(
    stations: list[dict],
    sections: list[dict],
    occupancy: list[dict],
    territory_id: str,
) -> list[str]:
    errors: list[str] = []
    prefix = f"{territory_id}: "

    station_ids = {station["station_id"] for station in stations}
    section_ids = {section["section_id"] for section in sections}
    section_endpoints = {
        section["section_id"]: (section["from_station"], section["to_station"])
        for section in sections
    }

    orders = [station["order"] for station in stations]
    if len(orders) != len(set(orders)):
        errors.append(f"{prefix}stations: duplicate order values found")

    for section in sections:
        if section["from_station"] not in station_ids:
            errors.append(
                f"{prefix}sections: {section['section_id']} references unknown "
                f"from_station {section['from_station']}"
            )
        if section["to_station"] not in station_ids:
            errors.append(
                f"{prefix}sections: {section['section_id']} references unknown "
                f"to_station {section['to_station']}"
            )

    for record in occupancy:
        section_id = record.get("section_id")
        if section_id not in section_ids:
            errors.append(
                f"{prefix}train_occupancy: unknown section_id {section_id} "
                f"for train {record.get('train_id')}"
            )

        entry_time = parse_time(record["entry_time"])
        exit_time = parse_time(record["exit_time"])
        if entry_time >= exit_time:
            errors.append(
                f"{prefix}train_occupancy: {record.get('train_id')} on {section_id} "
                f"has entry_time >= exit_time"
            )

    by_train: dict[str, list[dict]] = {}
    for record in occupancy:
        by_train.setdefault(record["train_id"], []).append(record)

    for train_id, records in by_train.items():
        records.sort(key=lambda row: row["entry_time"])
        for previous, current in zip(records, records[1:]):
            prev_exit = parse_time(previous["exit_time"])
            curr_entry = parse_time(current["entry_time"])
            if curr_entry < prev_exit:
                errors.append(
                    f"{prefix}train_occupancy: {train_id} time ordering breaks "
                    f"between {previous['section_id']} and {current['section_id']}"
                )

            prev_section = previous["section_id"]
            curr_section = current["section_id"]
            if prev_section in section_endpoints and curr_section in section_endpoints:
                _, prev_to = section_endpoints[prev_section]
                curr_from, _ = section_endpoints[curr_section]
                if prev_to != curr_from:
                    errors.append(
                        f"{prefix}train_occupancy: {train_id} jumps from "
                        f"{prev_section} to non-adjacent {curr_section}"
                    )

    return errors


def validate() -> list[str]:
    errors: list[str] = []
    try:
        manifests = list_territories()
    except ValueError as error:
        return [str(error)]

    for manifest in manifests:
        if manifest.status == PLACEHOLDER:
            continue
        try:
            territory = load_territory(manifest.territory_id)
            errors.extend(
                validate_records(
                    territory.stations,
                    territory.sections,
                    territory.train_occupancy,
                    manifest.territory_id,
                )
            )
        except ValueError as error:
            errors.append(f"{manifest.territory_id}: {error}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
