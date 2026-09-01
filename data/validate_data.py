"""Validate RailSync corridor data files."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent


def load_json(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def validate() -> list[str]:
    errors: list[str] = []

    stations = load_json("stations.json")
    sections = load_json("sections.json")
    occupancy = load_json("train_occupancy.json")

    station_ids = {station["station_id"] for station in stations}
    section_ids = {section["section_id"] for section in sections}
    section_endpoints = {
        section["section_id"]: (section["from_station"], section["to_station"])
        for section in sections
    }

    orders = [station["order"] for station in stations]
    if len(orders) != len(set(orders)):
        errors.append("stations.json: duplicate order values found")

    for section in sections:
        if section["from_station"] not in station_ids:
            errors.append(
                f"sections.json: {section['section_id']} references unknown "
                f"from_station {section['from_station']}"
            )
        if section["to_station"] not in station_ids:
            errors.append(
                f"sections.json: {section['section_id']} references unknown "
                f"to_station {section['to_station']}"
            )

    for record in occupancy:
        section_id = record.get("section_id")
        if section_id not in section_ids:
            errors.append(
                f"train_occupancy.json: unknown section_id {section_id} "
                f"for train {record.get('train_id')}"
            )

        entry_time = parse_time(record["entry_time"])
        exit_time = parse_time(record["exit_time"])
        if entry_time >= exit_time:
            errors.append(
                f"train_occupancy.json: {record.get('train_id')} on {section_id} "
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
                    f"train_occupancy.json: {train_id} time ordering breaks "
                    f"between {previous['section_id']} and {current['section_id']}"
                )

            prev_section = previous["section_id"]
            curr_section = current["section_id"]
            if prev_section in section_endpoints and curr_section in section_endpoints:
                _, prev_to = section_endpoints[prev_section]
                curr_from, _ = section_endpoints[curr_section]
                if prev_to != curr_from:
                    errors.append(
                        f"train_occupancy.json: {train_id} jumps from "
                        f"{prev_section} to non-adjacent {curr_section}"
                    )

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
