"""Focused tests for manifest discovery and canonical data adapters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data.adapters import load_json_list
from data.territories import (
    CANONICAL_FIELDS,
    PLACEHOLDER,
    TerritoryNotPopulatedError,
    UnknownTerritoryError,
    get_territory_manifest,
    load_territory,
    registered_territory_ids,
)
from optimizer.optimizer import optimize_schedule
from optimizer.comparison import compare_plans


def test_multiple_territories_are_registered() -> None:
    assert set(registered_territory_ids()) == {
        "delhi_agra",
        "eastern_hdn",
        "eastern_hdn_test_fixture",
        "saktigarh_memari_public_demo",
        "western_hdn",
    }


def test_delhi_agra_loads_public_planning_corridor() -> None:
    territory = load_territory("delhi_agra")

    assert len(territory.stations) == 8
    assert len(territory.sections) == 7
    assert len(territory.train_occupancy) == 56
    assert len(territory.train_services) == 8
    assert len(territory.maintenance_tasks) == 12
    assert territory.resource_context is not None
    assert set(territory.stations[0]) == {"station_id", "station_name", "order"}
    assert {"section_id", "from_station", "to_station", "capacity_resources"} <= set(territory.sections[0])
    assert {"train_id", "section_id", "entry_time", "exit_time", "direction"} <= set(territory.train_occupancy[0])


def test_unknown_territory_fails_clearly() -> None:
    with pytest.raises(UnknownTerritoryError, match="Unknown territory_id.*missing"):
        load_territory("missing")


def test_adapter_enforces_canonical_record_fields(tmp_path: Path) -> None:
    snapshot = tmp_path / "occupancy.json"
    snapshot.write_text(
        json.dumps(
            [
                {
                    "train_id": "TR1",
                    "section_id": "SEC1",
                    "entry_time": "2026-09-01T00:00:00",
                    "exit_time": "2026-09-01T00:10:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    records = load_json_list(
        snapshot,
        dataset_name="train_occupancy",
        required_fields={"train_id", "section_id", "entry_time", "exit_time"},
    )
    assert set(records[0]) == {"train_id", "section_id", "entry_time", "exit_time"}

    snapshot.write_text('[{"train_id": "TR1"}]', encoding="utf-8")
    with pytest.raises(ValueError, match="missing: entry_time, exit_time, section_id"):
        load_json_list(
            snapshot,
            dataset_name="train_occupancy",
            required_fields={"train_id", "section_id", "entry_time", "exit_time"},
        )


def test_manifest_metadata_is_excluded_and_does_not_change_optimizer_semantics() -> None:
    data = load_territory("delhi_agra").as_optimizer_input()
    assert "territory_id" not in data
    assert "provenance" not in data

    result = optimize_schedule(data, horizon_end="2026-09-01T07:00:00")
    with_ignored_metadata = {**data, "territory_metadata": {"display_name": "changed"}}
    assert optimize_schedule(
        with_ignored_metadata, horizon_end="2026-09-01T07:00:00"
    ) == result
    assert result["status"] == "success"


@pytest.mark.parametrize("territory_id", ["eastern_hdn"])
def test_future_hdn_placeholder_cannot_load(territory_id: str) -> None:
    manifest = get_territory_manifest(territory_id)
    assert manifest.status == PLACEHOLDER
    assert manifest.available_datasets == ()
    assert manifest.scenario_references == ()

    with pytest.raises(TerritoryNotPopulatedError, match="placeholder"):
        load_territory(territory_id)


def test_eastern_fixture_manifest_is_explicitly_synthetic() -> None:
    manifest = get_territory_manifest("eastern_hdn_test_fixture")
    assert manifest.status == "POPULATED"
    assert set(manifest.available_datasets) == set(CANONICAL_FIELDS) - {"train_services"}
    assert manifest.scenario_references == ("eastern_hdn_synthetic_demo_v1",)
    assert {item["label"] for item in manifest.provenance} == {"TEST_FIXTURE"}
    assert set(manifest.provenance[0]["datasets"]) == set(CANONICAL_FIELDS) - {"train_services"}
    assert manifest.planning_horizon == {
        "start_time": "2026-09-01T00:00:00",
        "end_time": "2026-09-01T06:00:00",
    }


def test_eastern_fixture_loads_canonical_corridor_and_scenario() -> None:
    territory = load_territory("eastern_hdn_test_fixture")
    assert len(territory.stations) == 10
    assert len(territory.sections) == 9
    assert len(territory.train_occupancy) == 49
    assert len(territory.maintenance_tasks) == 9
    assert territory.resource_context is not None
    assert territory.resource_provenance == "TEST_FIXTURE"
    assert territory.resource_context.crew_capacities == {
        "TRACK_CREW": 1,
        "SIGNAL_CREW": 1,
        "OHE_CREW": 1,
    }
    assert territory.resource_context.power_windows["EHDN_SEC06"] == ()
    assert {task["department"] for task in territory.maintenance_tasks} == {
        "ENGINEERING",
        "S&T",
        "TRD",
    }
    assert all(
        CANONICAL_FIELDS[name] <= set(record)
        for name, records in (
            ("stations", territory.stations),
            ("sections", territory.sections),
            ("train_occupancy", territory.train_occupancy),
            ("maintenance_tasks", territory.maintenance_tasks),
        )
        for record in records
    )


def test_eastern_fixture_runs_through_existing_optimizer() -> None:
    territory = load_territory("eastern_hdn_test_fixture")
    result = optimize_schedule(
        territory.as_optimizer_input(),
        territory.manifest.planning_horizon["start_time"],
        territory.manifest.planning_horizon["end_time"],
        resource_context=territory.resource_context,
    )
    assert result["status"] == "success"
    assert "EHDN_ENG003" not in result["unscheduled_tasks"]
    assert result["unscheduled_tasks"] == ["EHDN_TRD003"]
    assert result["metrics"]["integrated_blocks"] == 2
    assert all(block["affected_trains"] == [] for block in result["blocks"])


def test_eastern_fixture_uses_existing_fair_comparison_pipeline() -> None:
    territory = load_territory("eastern_hdn_test_fixture")
    comparison = compare_plans(
        territory.as_optimizer_input(),
        territory.manifest.planning_horizon["start_time"],
        territory.manifest.planning_horizon["end_time"],
        resource_context=territory.resource_context,
    )
    assert comparison["both_proven_optimal"] is True
    assert comparison["comparison"]["same_task_set"] is True
    assert comparison["comparison"]["closure_saved_minutes"] == 105
    assert comparison["baseline"]["scheduled_tasks"] == comparison["optimized"][
        "scheduled_tasks"
    ]


def test_public_timetable_demo_loads_canonical_historical_data() -> None:
    territory = load_territory("saktigarh_memari_public_demo")
    assert len(territory.stations) == 5
    assert len(territory.sections) == 4
    assert len(territory.train_occupancy) == 20
    assert len(territory.maintenance_tasks) == 6
    assert territory.stations[0] == {
        "station_id": "SKG", "station_name": "Saktigarh", "order": 1
    }
    assert territory.stations[-1]["station_id"] == "MYM"
    assert {item["label"] for item in territory.manifest.provenance} == {
        "PUBLIC_TIMETABLE_DERIVED", "SYNTHETIC_PROTOTYPE"
    }
    public_record = next(
        item for item in territory.manifest.provenance
        if item["label"] == "PUBLIC_TIMETABLE_DERIVED"
    )
    assert set(public_record["datasets"]) == {
        "stations", "sections", "train_occupancy", "train_services"
    }
    assert len(territory.train_services) == 5
    assert territory.resource_provenance == "SYNTHETIC_PROTOTYPE"


@pytest.mark.parametrize("territory_id", ["western_hdn", "delhi_agra"])
def test_additional_public_territories_are_planning_ready(territory_id: str) -> None:
    territory = load_territory(territory_id)
    assert territory.manifest.status == "POPULATED"
    assert len(territory.train_services) >= 8
    assert len(territory.maintenance_tasks) >= 10
    assert territory.resource_provenance == "SYNTHETIC_PROTOTYPE"
    assert any(len(task.get("section_ids", [])) > 1 for task in territory.maintenance_tasks)


def test_public_timetable_demo_runs_unchanged_optimizer_and_fair_comparison() -> None:
    territory = load_territory("saktigarh_memari_public_demo")
    comparison = compare_plans(
        territory.as_optimizer_input(),
        territory.manifest.planning_horizon["start_time"],
        territory.manifest.planning_horizon["end_time"],
        resource_context=territory.resource_context,
    )
    plan = comparison["optimized"]["plan"]
    assert comparison["comparison_proof_state"] == "FULLY_OPTIMAL"
    assert comparison["comparison"]["same_task_set"] is True
    assert comparison["comparison"]["closure_saved_minutes"] == 50
    assert plan["status"] == "success"
    assert plan["unscheduled_tasks"] == []
    assert plan["metrics"]["integrated_blocks"] == 2
    assert all(block["affected_trains"] == [] for block in plan["blocks"])
