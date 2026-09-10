from datetime import datetime

from optimizer.candidate_windows import OperationalAllowances, generate_footprint_windows
from optimizer.capacity import movement_capacity_resources, normalize_tasks, section_index
from optimizer.compatibility import CompatibilityStatus, evaluate_compatibility
from optimizer.optimizer import optimize_schedule
from optimizer.resources import PowerWindow, ResourceContext


ZERO_ALLOWANCES = OperationalAllowances(
    safety_after_minutes=0,
    safety_before_minutes=0,
    setup_minutes=0,
    release_minutes=0,
)


def _task(task_id="TASK", **extra):
    return {
        "task_id": task_id,
        "department": "ENGINEERING",
        "section_id": "S1",
        "task_type": "Inspection",
        "duration_minutes": 20,
        "criticality": 9,
        "urgency": 9,
        "overdue_days": 1,
        "deadline": "2026-09-01T02:00:00",
        "requires_power_block": False,
        "crew_type": "TRACK_CREW",
        "compatibility_group": "GROUP",
        **extra,
    }


def test_multi_section_windows_are_intersection_of_capacity_availability():
    sections = [
        {"section_id": "S1", "from_station": "A", "to_station": "B"},
        {"section_id": "S2", "from_station": "B", "to_station": "C"},
    ]
    task = normalize_tasks([_task(section_ids=["S1", "S2"])], sections)[0]
    occupancy = [
        {"train_id": "T1", "section_id": "S1", "entry_time": "2026-09-01T00:30:00", "exit_time": "2026-09-01T00:50:00"},
        {"train_id": "T2", "section_id": "S2", "entry_time": "2026-09-01T01:10:00", "exit_time": "2026-09-01T01:30:00"},
    ]
    windows = generate_footprint_windows(
        occupancy,
        [{"section_id": "S1", "section_ids": task["_section_ids"], "capacity_resource_ids": task["_capacity_resource_ids"]}],
        sections,
        "2026-09-01T00:00:00",
        "2026-09-01T02:00:00",
        ZERO_ALLOWANCES,
    )
    assert [(window.usable_start[11:16], window.usable_end[11:16]) for window in windows] == [
        ("00:00", "00:30"), ("00:50", "01:10"), ("01:30", "02:00")
    ]


def test_explicit_direction_mapping_allows_independent_track_capacity():
    section = {
        "section_id": "S1", "from_station": "A", "to_station": "B",
        "capacity_resources": [
            {"capacity_resource_id": "S1_UP", "track_id": "UP"},
            {"capacity_resource_id": "S1_DOWN", "track_id": "DOWN"},
        ],
        "direction_capacity_mapping": {"UP": "S1_UP", "DOWN": "S1_DOWN"},
    }
    occupancy = [{"train_id": "T1", "section_id": "S1", "entry_time": "2026-09-01T00:00:00", "exit_time": "2026-09-01T02:00:00", "direction": "UP"}]
    task = _task(capacity_resource_ids=["S1_DOWN"])
    result = optimize_schedule(
        {"sections": [section], "maintenance_tasks": [task], "train_occupancy": occupancy},
        "2026-09-01T00:00:00", "2026-09-01T02:00:00", allowances=ZERO_ALLOWANCES,
    )
    assert result["unscheduled_tasks"] == []
    assert result["blocks"][0]["capacity_resource_ids"] == ["S1_DOWN"]


def test_direction_without_explicit_mapping_never_implies_a_track():
    section = {
        "section_id": "S1", "from_station": "A", "to_station": "B",
        "capacity_resources": ["S1_UP", "S1_DOWN"],
    }
    movement = {"train_id": "T1", "section_id": "S1", "direction": "UP"}
    assert movement_capacity_resources(movement, section_index([section])) == ("S1_UP", "S1_DOWN")


def test_different_capacity_footprints_are_not_grouped():
    sections = [{"section_id": "S1", "from_station": "A", "to_station": "B", "capacity_resources": ["UP", "DOWN"]}]
    first, second = normalize_tasks([
        _task("UP_TASK", capacity_resource_ids=["UP"]),
        _task("DOWN_TASK", capacity_resource_ids=["DOWN"]),
    ], sections)
    result = evaluate_compatibility(first, second)
    assert result.eligible is False
    assert result.status == CompatibilityStatus.INCOMPATIBLE
    assert result.reason == "DIFFERENT_POSSESSION_FOOTPRINT"


def test_roster_calendar_is_a_hard_reservation_constraint():
    context = ResourceContext(
        crew_capacities={"TRACK_CREW": 1},
        crew_windows={"TRACK_CREW": (PowerWindow("2026-09-01T00:00:00", "2026-09-01T00:10:00"),)},
    )
    result = optimize_schedule(
        {"sections": [{"section_id": "S1", "from_station": "A", "to_station": "B"}], "maintenance_tasks": [_task()], "train_occupancy": []},
        "2026-09-01T00:00:00", "2026-09-01T02:00:00",
        allowances=ZERO_ALLOWANCES, resource_context=context,
    )
    assert result["unscheduled_tasks"] == ["TASK"]
