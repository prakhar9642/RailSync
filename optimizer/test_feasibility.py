"""Deterministic boundary, eligibility, and CP-SAT integration regressions."""

import sys
from dataclasses import asdict
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_windows import OperationalAllowances, generate_candidate_windows
from feasibility import FeasibilityContext, ReasonCode, evaluate_task_in_window
from optimizer import optimize_schedule, minutes_to_datetime, datetime_to_minutes

ORIGIN = "2026-09-01T00:00:00"


def stamp(minutes):
    return minutes_to_datetime(minutes, ORIGIN)


def train(start, end, section="SEC03"):
    return dict(train_id=f"TR{start}", section_id=section, entry_time=stamp(start), exit_time=stamp(end))


def task(duration=60, **extra):
    return dict(task_id="ENG001", section_id="SEC03", duration_minutes=duration, **extra)


def windows(rows=None, horizon=240, allowances=OperationalAllowances()):
    return generate_candidate_windows(
        [train(0, 40), train(180, 240)] if rows is None else rows,
        ["SEC03"], ORIGIN, stamp(horizon), allowances,
    )


def test_gap_and_critical_nominal_fit_demonstration():
    window, = windows()
    assert (window.nominal_start, window.nominal_end) == (stamp(40), stamp(180))
    assert (window.usable_start, window.usable_end) == (stamp(55), stamp(165))
    assert (window.nominal_minutes, window.usable_minutes) == (140, 110)
    assert window.margin_before_minutes == window.margin_after_minutes == 15
    result = evaluate_task_in_window(task(120), window)
    assert 120 <= window.nominal_minutes
    assert not result.feasible
    assert result.required_minutes == 135
    assert result.reasons == (ReasonCode.INSUFFICIENT_USABLE_DURATION,)


def test_horizon_start_and_end():
    first, last = windows([train(60, 90)])
    assert (first.nominal_start, first.usable_start, first.usable_end) == (stamp(0), stamp(0), stamp(45))
    assert (last.nominal_end, last.usable_start, last.usable_end) == (stamp(240), stamp(105), stamp(240))


@pytest.mark.parametrize("rows", [
    [train(40, 90), train(60, 110)],
    [train(40, 90), train(90, 110)],
    [train(40, 110), train(50, 60), train(40, 110)],
])
def test_overlapping_adjacent_nested_and_duplicate_occupancies(rows):
    result = windows(rows)
    assert len(result) == 2
    assert result[0].nominal_end == stamp(40)
    assert result[1].nominal_start == stamp(110)
    assert result == windows(list(reversed(rows)))


def test_empty_section_and_full_coverage():
    window, = windows([])
    assert window.usable_minutes == 240
    assert windows([train(-30, 300)]) == []


def test_outside_horizon_safety_and_clipping():
    window, = windows([train(-30, -5), train(245, 260)])
    assert (window.usable_start, window.usable_end) == (stamp(10), stamp(230))
    window, = windows([train(-30, 20), train(220, 260)])
    assert (window.nominal_start, window.nominal_end) == (stamp(20), stamp(220))


def test_exhausted_gap_retained_with_no_negative_duration():
    window, = windows([train(0, 40), train(50, 240)])
    assert window.usable_minutes == 0
    assert window.usable_start == window.usable_end
    assert not evaluate_task_in_window(task(1), window).feasible


@pytest.mark.parametrize("changes,context,reason", [
    ({}, None, None),
    ({"section_id": "SEC04"}, None, ReasonCode.WRONG_SECTION),
    ({"duration_minutes": 96}, None, ReasonCode.INSUFFICIENT_USABLE_DURATION),
    ({"deadline": stamp(130)}, None, None),
    ({"deadline": stamp(129)}, None, ReasonCode.DEADLINE_VIOLATION),
    ({"requires_power_block": True}, FeasibilityContext(power_available=False), ReasonCode.POWER_BLOCK_UNAVAILABLE),
    ({"requires_power_block": True}, FeasibilityContext(power_available=True), None),
    ({"requires_power_isolation": True}, FeasibilityContext(power_available=False), ReasonCode.POWER_BLOCK_UNAVAILABLE),
    ({"requires_power_block": True, "crew_type": "TRACK", "machine_type": "TAMPER"}, None, None),
    ({"crew_type": "TRACK"}, FeasibilityContext(crew_availability={"TRACK": False}), ReasonCode.CREW_UNAVAILABLE),
    ({"crew_type": "TRACK"}, FeasibilityContext(crew_availability={"TRACK": True}), None),
    ({"machine_type": "TAMPER"}, FeasibilityContext(machine_availability={"TAMPER": False}), ReasonCode.MACHINE_UNAVAILABLE),
    ({"machine_type": "TAMPER"}, FeasibilityContext(machine_availability={"TAMPER": True}), None),
])
def test_feasibility_rules(changes, context, reason):
    work = task()
    work.update(changes)
    result = evaluate_task_in_window(work, windows()[0], context)
    assert result.feasible == (reason is None)
    assert result.reasons == (() if reason is None else (reason,))


def test_exact_fit_and_task_overrides_do_not_double_count():
    result = evaluate_task_in_window(task(95), windows()[0])
    assert result.feasible and result.slack_minutes == 0
    result = evaluate_task_in_window(task(110, setup_minutes=0, release_minutes=0), windows()[0])
    assert result.feasible and result.required_minutes == 110
    assert not evaluate_task_in_window(task(95, setup_minutes=11), windows()[0]).feasible


def test_actual_execution_must_meet_deadline_and_bounds():
    work = task(deadline=stamp(130))
    window = windows()[0]
    assert evaluate_task_in_window(work, window).latest_reservation_start == stamp(55)
    assert ReasonCode.DEADLINE_VIOLATION in evaluate_task_in_window(work, window, reservation_start=stamp(56)).reasons
    assert not evaluate_task_in_window(task(), window, reservation_start=stamp(54)).feasible


@pytest.mark.parametrize("field", ["safety_after_minutes", "safety_before_minutes", "setup_minutes", "release_minutes"])
@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_invalid_allowances(field, value):
    with pytest.raises(ValueError):
        OperationalAllowances(**{field: value})


@pytest.mark.parametrize("value", [-1, 0.5, True])
def test_invalid_task_overhead(value):
    with pytest.raises(ValueError):
        evaluate_task_in_window(task(setup_minutes=value), windows()[0])


def test_datetime_rules():
    assert datetime_to_minutes("2026-09-01T01:00:00+01:00", "2026-09-01T00:00:00Z") == 0
    with pytest.raises(ValueError, match="timezone"):
        generate_candidate_windows([], ["SEC03"], ORIGIN, "2026-09-01T04:00:00Z")
    with pytest.raises(ValueError, match="whole minute"):
        generate_candidate_windows([], ["SEC03"], ORIGIN, "2026-09-01T04:00:01")
    with pytest.raises(ValueError):
        windows([train(20, 10)])
    with pytest.raises(ValueError):
        windows([], horizon=0)


def demonstration():
    rows = [train(0, 40), train(180, 240)]
    feasible_task = task()
    rejected_task = task(120)
    rejected_task["task_id"] = "ENG002"
    window, = windows(rows)
    data = dict(maintenance_tasks=[feasible_task, rejected_task], train_occupancy=rows)
    result = optimize_schedule(data, ORIGIN, stamp(240))
    return dict(
        candidate=asdict(window),
        feasible_pair=asdict(evaluate_task_in_window(feasible_task, window)),
        rejected_pair=asdict(evaluate_task_in_window(rejected_task, window)),
        response=result,
    )


def test_solver_contract_and_actual_assignments():
    example = demonstration()
    result = example["response"]
    assert set(result) == {"status", "blocks", "unscheduled_tasks", "metrics"}
    assert result["unscheduled_tasks"] == ["ENG002"]
    assert len(result["blocks"]) == 1
    block = result["blocks"][0]
    assert set(block) == {"block_id", "section_id", "start_time", "end_time", "tasks", "integrated", "affected_trains", "explanation"}
    assert (block["start_time"], block["end_time"]) == (stamp(55), stamp(130))
    assert block["affected_trains"] == []
    assert result["metrics"]["optimized_affected_trains"] == 0
    assert result["metrics"]["optimized_block_hours"] == 1.25
    assert result["metrics"]["baseline_block_hours"] == 0
    assert evaluate_task_in_window(task(), windows()[0], reservation_start=stamp(55)).feasible
    assert demonstration() == example


@pytest.mark.parametrize("available,expected", [(None, "UNKNOWN"), (True, "PASSED"), (False, "FAILED")])
def test_resource_check_states(available, expected):
    work = task(requires_power_block=True, crew_type="TRACK", machine_type="TAMPER")
    context = FeasibilityContext(
        power_available=available,
        crew_availability={} if available is None else {"TRACK": available},
        machine_availability={} if available is None else {"TAMPER": available},
    )
    result = evaluate_task_in_window(work, windows()[0], context)
    assert result.resource_checks == dict.fromkeys(("power", "crew", "machine"), expected)
    assert result.feasible == (available is not False)
    assert evaluate_task_in_window(task(), windows()[0], context).resource_checks == dict.fromkeys(
        ("power", "crew", "machine"), "NOT_EVALUATED"
    )
    assert evaluate_task_in_window(work, windows()[0]).resource_checks == dict.fromkeys(
        ("power", "crew", "machine"), "UNKNOWN"
    )


def test_unscheduled_work_does_not_create_baseline_or_savings():
    rows = [train(0, 40), train(180, 240)]
    single = optimize_schedule(dict(maintenance_tasks=[task()], train_occupancy=rows), ORIGIN, stamp(240))
    assert single["metrics"] == demonstration()["response"]["metrics"]
    empty = optimize_schedule(dict(maintenance_tasks=[task(120)], train_occupancy=rows), ORIGIN, stamp(240))
    assert empty["unscheduled_tasks"] == ["ENG001"]
    assert empty["metrics"]["baseline_block_hours"] == empty["metrics"]["optimized_block_hours"] == 0


@pytest.mark.parametrize("setup,release", [(10, 5), (0, 0), (20, 10)])
def test_public_possession_with_configured_overhead_and_train_protection(setup, release):
    config = OperationalAllowances(setup_minutes=setup, release_minutes=release)
    rows = [train(0, 40), train(180, 240)]
    result = optimize_schedule(dict(maintenance_tasks=[task()], train_occupancy=rows), ORIGIN, stamp(240), allowances=config)
    block, = result["blocks"]
    start = datetime_to_minutes(block["start_time"], ORIGIN)
    end = datetime_to_minutes(block["end_time"], ORIGIN)
    assert (start, end) == (55, 55 + setup + 60 + release)
    assert result["metrics"]["optimized_block_hours"] == round((setup + 60 + release) / 60, 3)
    for row in rows:
        assert end <= datetime_to_minutes(row["entry_time"], ORIGIN) or start >= datetime_to_minutes(row["exit_time"], ORIGIN)


def test_solver_enforces_deadline_after_competing_tasks_shift_start():
    tasks = [task(deadline=stamp(75)), task(deadline=stamp(75))]
    tasks[1]["task_id"] = "ENG002"
    result = optimize_schedule(dict(maintenance_tasks=tasks, train_occupancy=[]), ORIGIN, stamp(240))
    assert len(result["blocks"]) == len(result["unscheduled_tasks"]) == 1
    assert result["blocks"][0]["end_time"] == stamp(75)


def test_solver_reserves_overhead_between_tasks():
    tasks = [task(), task()]
    tasks[1]["task_id"] = "ENG002"
    result = optimize_schedule(dict(maintenance_tasks=tasks, train_occupancy=[]), ORIGIN, stamp(150))
    assert len(result["blocks"]) == 2
    first, second = result["blocks"]
    assert datetime_to_minutes(second["start_time"], first["end_time"]) == 0


@pytest.mark.parametrize("context", [
    FeasibilityContext(power_available=False),
    FeasibilityContext(crew_availability={"TRACK": False}),
    FeasibilityContext(machine_availability={"TAMPER": False}),
])
def test_solver_excludes_unavailable_pairs(context):
    work = task(requires_power_block=True, crew_type="TRACK", machine_type="TAMPER")
    result = optimize_schedule(
        dict(maintenance_tasks=[work], train_occupancy=[train(0, 40), train(180, 240)]),
        ORIGIN, stamp(240), window_contexts={"WIN_SEC03_001": context},
    )
    assert result["blocks"] == []
    assert result["unscheduled_tasks"] == ["ENG001"]


if __name__ == "__main__":
    import json
    print(json.dumps(demonstration(), indent=2))
