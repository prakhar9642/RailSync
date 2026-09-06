"""Deterministic priority, shared-possession, and explicit-resource regressions."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from optimizer import optimize_schedule, minutes_to_datetime, datetime_to_minutes, validate_solution
from candidate_windows import OperationalAllowances, generate_candidate_windows
from compatibility import CompatibilityPolicy, evaluate_compatibility
from feasibility import evaluate_task_in_window, task_requirements
from resources import ResourceContext, PowerWindow

ORIGIN = "2026-09-01T00:00:00"
ZERO = OperationalAllowances(0, 0, 0, 0)


def stamp(minutes):
    return minutes_to_datetime(minutes, ORIGIN)


def task(task_id, duration=60, **fields):
    return dict(task_id=task_id, section_id="SEC03", duration_minutes=duration, **fields)


def run(tasks, horizon=180, **kwargs):
    return optimize_schedule(dict(maintenance_tasks=tasks, train_occupancy=[]),
                             ORIGIN, stamp(horizon), **kwargs)


def selected(result):
    return {t for b in result["blocks"] for t in b["tasks"]}


def pair(**extra):
    return [task("ENG", 120, department="ENGINEERING", compatibility_group="A", **extra),
            task("SNT", 60, department="S&T", compatibility_group="A", **extra)]


@pytest.mark.parametrize("field", ["criticality", "urgency", "overdue_days"])
def test_priority_tiers(field):
    tasks = [task("LOW", **{field: 1}), task("HIGH", **{field: 2})]
    assert selected(run(tasks, 60, allowances=ZERO)) == {"HIGH"}


def test_higher_tier_cannot_be_traded_for_lower_tier():
    tasks = [task("CRITICAL", criticality=2),
             task("URGENT", criticality=1, urgency=1000, overdue_days=1000)]
    assert selected(run(tasks, 60, allowances=ZERO)) == {"CRITICAL"}
    tasks = [task("URGENT", criticality=1, urgency=2),
             task("OVERDUE", criticality=1, urgency=1, overdue_days=1000)]
    assert selected(run(tasks, 60, allowances=ZERO)) == {"URGENT"}


def test_task_count_only_after_priority_then_closure():
    tasks = [task("LONG", 90, criticality=10),
             task("SHORT1", 30, criticality=3), task("SHORT2", 30, criticality=3)]
    assert selected(run(tasks, 90, allowances=ZERO)) == {"LONG"}
    tasks[0]["criticality"] = 6
    assert selected(run(tasks, 90, allowances=ZERO)) == {"SHORT1", "SHORT2"}
    # Once priority and count tie, prefer the shorter closure.
    assert selected(run([task("LONG", 90), task("SHORT", 60)], 90, allowances=ZERO)) == {"SHORT"}


def test_lexicographic_optima_recorded_in_order():
    facts = {}
    result = run(pair(), diagnostics=facts)
    assert [f["objective"] for f in facts["priority_stages"]] == [
        "criticality", "urgency", "overdue_days", "task_count",
        "possession_minutes", "block_count", "minimum_boundary_slack_minutes",
        "total_boundary_slack_minutes", "start_minutes",
    ]
    assert all(f["status"] == "OPTIMAL" for f in facts["priority_stages"])
    assert [f["optimum"] for f in facts["priority_stages"]] == [0, 0, 0, 2, 135, 1, 22, 22, 44]
    assert result["metrics"]["optimized_block_hours"] == 2.25


def test_integrated_union_and_contract():
    result = run(pair())
    assert set(result) == {"status", "blocks", "unscheduled_tasks", "metrics"}
    block, = result["blocks"]
    assert block["tasks"] == ["ENG", "SNT"] and block["integrated"] is True
    assert (block["start_time"], block["end_time"]) == (stamp(22), stamp(157))
    assert set(block) == {"block_id", "section_id", "start_time", "end_time", "tasks",
                          "integrated", "affected_trains", "explanation"}
    assert result["metrics"] == dict(baseline_block_hours=0, optimized_block_hours=2.25,
                                    baseline_affected_trains=0, optimized_affected_trains=0,
                                    integrated_blocks=1)


@pytest.mark.parametrize("group", ["B", None, "", "   "])
def test_incompatible_or_unknown_tasks_still_schedule_separately(group):
    tasks = pair()
    tasks[1]["compatibility_group"] = group
    result = run(tasks, 210)
    assert selected(result) == {"ENG", "SNT"}
    assert len(result["blocks"]) == 2
    assert all(not b["integrated"] for b in result["blocks"])
    assert result["metrics"]["optimized_block_hours"] == 3.5


def test_configurable_compatibility_and_same_department_flag():
    tasks = pair()
    assert evaluate_compatibility(*tasks).status == "CONDITIONAL"
    assert not evaluate_compatibility(*tasks, CompatibilityPolicy(False)).eligible
    assert not evaluate_compatibility(*tasks, CompatibilityPolicy(disabled_groups=frozenset({"A"}))).eligible
    assert len(run(tasks, 210, compatibility_policy=CompatibilityPolicy(False))["blocks"]) == 2
    tasks[1]["department"] = "ENGINEERING"
    result = run(tasks)
    assert len(result["blocks"]) == 1
    assert not result["blocks"][0]["integrated"]


@pytest.mark.parametrize("field,pool_field,reason", [
    ("crew_type", "crew_capacities", "CREW_CAPACITY_CONFLICT"),
    ("machine_type", "machine_capacities", "MACHINE_CAPACITY_CONFLICT"),
])
def test_exclusive_resource_prevents_integration_but_allows_sequential(field, pool_field, reason):
    tasks = pair(**{field: "EXCLUSIVE"})
    facts = {}
    result = run(tasks, 210, resource_context=ResourceContext(**{pool_field: {"EXCLUSIVE": 1}}), diagnostics=facts)
    assert len(result["blocks"]) == 2 and not result["unscheduled_tasks"]
    assert reason in facts["pair_checks"][0]["reasons"]
    assert result["metrics"]["optimized_block_hours"] == 3.5


def test_distinct_crews_and_capacity_two_allow_integration():
    tasks = pair()
    tasks[0]["crew_type"], tasks[1]["crew_type"] = "TRACK", "SIGNAL"
    assert len(run(tasks, resource_context=ResourceContext(crew_capacities={"TRACK": 1, "SIGNAL": 1}))["blocks"]) == 1
    assert len(run(pair(crew_type="POOL"), resource_context=ResourceContext(crew_capacities={"POOL": 2}))["blocks"]) == 1


def test_three_way_capacity_and_global_cross_section_pool():
    tasks = [task(str(i), 60, compatibility_group="A", crew_type="POOL") for i in range(3)]
    result = run(tasks, 150, resource_context=ResourceContext(crew_capacities={"POOL": 2}))
    assert len(result["blocks"]) == 2 and len(selected(result)) == 3
    tasks[1]["section_id"] = "SEC04"
    result = run(tasks[:2], 75, resource_context=ResourceContext(crew_capacities={"POOL": 1}))
    assert len(selected(result)) == 1


@pytest.mark.parametrize("intervals,expected_start", [
    ((PowerWindow(stamp(30), stamp(105)),), 30),
    ((), None),
    ((PowerWindow(stamp(30), stamp(104)),), None),
    ((PowerWindow(stamp(10), stamp(30)), PowerWindow(stamp(60), stamp(135))), 60),
    ((PowerWindow(stamp(30), stamp(70)), PowerWindow(stamp(70), stamp(105))), 30),
])
def test_power_windows_cover_full_reservation(intervals, expected_start):
    result = run([task("TRD", requires_power_block=True)],
                 resource_context=ResourceContext(power_windows={"SEC03": intervals}))
    if expected_start is None:
        assert result["unscheduled_tasks"] == ["TRD"]
    else:
        block, = result["blocks"]
        assert block["start_time"] == stamp(expected_start)
        assert block["end_time"] == stamp(expected_start + 75)


def test_power_and_deadline_intersection_and_actual_start_validation():
    context = ResourceContext(power_windows={"SEC03": (PowerWindow(stamp(60), stamp(150)),)})
    work = task("TRD", requires_power_isolation=True, deadline=stamp(134))
    assert run([work], resource_context=context)["blocks"] == []
    work["deadline"] = stamp(135)
    result = run([work], resource_context=context)
    assert result["blocks"][0]["end_time"] == stamp(135)
    window, = generate_candidate_windows([], ["SEC03"], ORIGIN, stamp(180))
    assert not evaluate_task_in_window(work, window, reservation_start=stamp(59), resource_context=context).feasible


def test_resource_unknown_and_existing_window_false_are_preserved():
    from feasibility import FeasibilityContext
    work = task("ALL", requires_power_block=True, crew_type="TRACK", machine_type="TAMPER")
    window, = generate_candidate_windows([], ["SEC03"], ORIGIN, stamp(180))
    assert set(evaluate_task_in_window(work, window).resource_checks.values()) == {"UNKNOWN"}
    context = ResourceContext(crew_capacities={"TRACK": 1}, machine_capacities={"TAMPER": 1},
                              power_windows={"SEC03": (PowerWindow(stamp(0), stamp(180)),)})
    check = evaluate_task_in_window(work, window, FeasibilityContext(power_available=False), resource_context=context)
    assert not check.feasible and check.resource_checks["power"] == "FAILED"
    assert run([work], resource_context=ResourceContext(crew_capacities={"TRACK": 0}))["blocks"] == []


@pytest.mark.parametrize("capacity", [-1, True, 1.5])
def test_invalid_capacity_rejected(capacity):
    with pytest.raises(ValueError):
        ResourceContext(crew_capacities={"TRACK": capacity})


def demonstration():
    tasks = [
        task("ENG017", 120, department="ENGINEERING", compatibility_group="A", crew_type="TRACK", criticality=9),
        task("SNT008", 60, department="S&T", compatibility_group="A", crew_type="SIGNAL", criticality=8),
        task("TRD004", 45, department="TRD", compatibility_group="A", requires_power_block=True, criticality=10),
        task("ENG_LOW", 60, department="ENGINEERING", compatibility_group="B", criticality=1),
    ]
    trains = [dict(train_id="TR1", section_id="SEC03", entry_time=stamp(0), exit_time=stamp(15)),
              dict(train_id="TR2", section_id="SEC03", entry_time=stamp(210), exit_time=stamp(240))]
    facts = {}
    result = optimize_schedule(dict(maintenance_tasks=tasks, train_occupancy=trains), ORIGIN, stamp(240),
                               resource_context=ResourceContext(crew_capacities={"TRACK": 1, "SIGNAL": 1},
                                                                power_windows={"SEC03": ()}), diagnostics=facts)
    return dict(reservation_minutes={t["task_id"]: task_requirements(t).required_minutes for t in tasks},
                result=result, diagnostics=facts)


def test_three_department_demo_safety_and_explanations():
    demo = demonstration()
    result, facts = demo["result"], demo["diagnostics"]
    assert selected(result) == {"ENG017", "SNT008"}
    block, = result["blocks"]
    assert (block["start_time"], block["end_time"]) == (stamp(45), stamp(180))
    assert block["affected_trains"] == [] and block["integrated"]
    assert result["metrics"]["optimized_block_hours"] == 2.25
    assert result["metrics"]["baseline_block_hours"] == 0
    assert facts["outcomes"]["ENG_LOW"] == "LOWER_PRIORITY_THAN_SELECTED_WORK"
    assert facts["outcomes"]["TRD004"] == "NO_FEASIBLE_TASK_WINDOW"
    assert any("POWER_WINDOW_UNAVAILABLE" in f["reasons"] for f in facts["task_windows"] if f["task_id"] == "TRD004")
    repeated = demonstration()
    for output in (demo, repeated):
        for stage in output["diagnostics"]["priority_stages"]:
            stage.pop("runtime_seconds")
    assert repeated == demo


if __name__ == "__main__":
    print(json.dumps(demonstration(), indent=2))
