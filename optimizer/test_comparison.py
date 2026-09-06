"""Fair-work comparisons and low-priority max-min boundary robustness."""

import copy
import sys
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparison
from comparison import compare_plans
from optimizer import optimize_schedule, minutes_to_datetime
from candidate_windows import OperationalAllowances, generate_candidate_windows
from compatibility import CompatibilityPolicy
from feasibility import FeasibilityContext
from resources import ResourceContext, PowerWindow
from robustness import add_boundary_slack
from possessions import solve_priorities
from metrics import compare_service

ORIGIN = "2026-09-01T00:00:00"
ZERO = OperationalAllowances(0, 0, 0, 0)


def stamp(minutes):
    return minutes_to_datetime(minutes, ORIGIN)


def task(name, duration=60, section="SEC03", **extra):
    return dict(task_id=name, section_id=section, duration_minutes=duration, **extra)


def data(tasks, occupancies=()):
    return dict(maintenance_tasks=tasks, train_occupancy=list(occupancies))


def train(start, end, section="SEC03"):
    return dict(train_id=f"TR{start}", section_id=section, entry_time=stamp(start), exit_time=stamp(end))


def same_work_demo():
    tasks = [task("ENG", 120, department="ENGINEERING", compatibility_group="A", criticality=9),
             task("SNT", 60, department="S&T", compatibility_group="A", criticality=8),
             task("TRD", 30, section="SEC04", department="TRD", criticality=7)]
    return compare_plans(data(tasks), ORIGIN, stamp(300))


def different_work_demo():
    tasks = [task("ENG", 120, department="ENGINEERING", compatibility_group="A", criticality=9),
             task("SNT", 60, department="S&T", compatibility_group="A", criticality=8)]
    return compare_plans(data(tasks), ORIGIN, stamp(150))


def test_same_work_savings_efficiency_and_coordination():
    result = same_work_demo()
    baseline, optimized, compared = result["baseline"], result["optimized"], result["comparison"]
    assert baseline["scheduled_tasks"] == optimized["scheduled_tasks"] == ["ENG", "SNT", "TRD"]
    assert baseline["productive_minutes"] == optimized["productive_minutes"] == 210
    assert (baseline["possession_minutes"], optimized["possession_minutes"]) == (255, 180)
    assert baseline["integrated_blocks"] == 0 and optimized["integrated_blocks"] == 1
    assert baseline["block_count"] == 3 and optimized["block_count"] == 2
    assert compared["same_task_set"]
    assert compared["closure_saved_minutes"] == baseline["possession_minutes"] - optimized["possession_minutes"]
    assert compared["closure_reduction_percent"] == pytest.approx(compared["closure_saved_minutes"] / baseline["possession_minutes"] * 100)
    assert compared["maintenance_delivery_efficiency_baseline"] == 210 / 255
    assert compared["maintenance_delivery_efficiency_optimized"] == 210 / 180
    assert compared["coordination_gain_minutes"] == 75
    assert all(len(b["tasks"]) == 1 for b in baseline["plan"]["blocks"])


def test_different_work_suppresses_headline_savings():
    result = different_work_demo()
    assert result["baseline"]["scheduled_tasks"] == ["ENG"]
    assert result["optimized"]["scheduled_tasks"] == ["ENG", "SNT"]
    assert result["baseline"]["criticality_served"] == 9
    assert result["optimized"]["criticality_served"] == 17
    assert not result["comparison"]["same_task_set"]
    assert result["comparison"]["closure_saved_minutes"] is None
    assert result["comparison"]["closure_reduction_percent"] is None
    # Also protect against the reverse: fewer delivered tasks and less closure.
    reverse = compare_service(result["optimized"], result["baseline"])
    assert reverse["closure_saved_minutes"] is None


def test_identical_feasibility_inputs_and_same_quality(monkeypatch):
    original = comparison.optimize_schedule
    calls = []
    def capture(*args, **kwargs):
        calls.append((args, kwargs.copy()))
        return original(*args, **kwargs)
    monkeypatch.setattr(comparison, "optimize_schedule", capture)
    inputs = data([task("A")], [train(0, 10)])
    saved = copy.deepcopy(inputs)
    contexts = {"WIN_SEC03_001": FeasibilityContext()}
    resources = ResourceContext(crew_capacities={"TRACK": 1})
    result = compare_plans(inputs, ORIGIN, stamp(180), window_contexts=contexts, resource_context=resources)
    assert calls[0][0] == calls[1][0]
    assert calls[0][0][0] is inputs and inputs == saved
    for key in ("allowances", "window_contexts", "resource_context", "compatibility_policy", "stage_time_limit_seconds"):
        assert calls[0][1][key] is calls[1][1][key]
    assert calls[0][1]["allow_integration"] is False
    assert calls[1][1]["allow_integration"] is True
    for mode in ("baseline", "optimized"):
        assert len(result[mode]["priority_stages"]) == 9
        assert all(s["status"] == "OPTIMAL" for s in result[mode]["priority_stages"])
    assert result["both_proven_optimal"]


@pytest.mark.parametrize("resource_field", ["crew_capacities", "machine_capacities"])
def test_identical_capacities_and_power_and_train_safety(resource_field):
    field = "crew_type" if resource_field == "crew_capacities" else "machine_type"
    tasks = [task("A", criticality=9, requires_power_block=True, **{field: "POOL"}),
             task("B", criticality=1, requires_power_block=True, **{field: "POOL"})]
    resources = ResourceContext(**{resource_field: {"POOL": 1}},
                                power_windows={"SEC03": (PowerWindow(stamp(40), stamp(115)),)})
    result = compare_plans(data(tasks, [train(0, 20), train(140, 180)]),
                           ORIGIN, stamp(180), resource_context=resources)
    for mode in ("baseline", "optimized"):
        assert result[mode]["scheduled_tasks"] == ["A"]
        block, = result[mode]["plan"]["blocks"]
        assert (block["start_time"], block["end_time"]) == (stamp(40), stamp(115))
        assert block["affected_trains"] == []


def test_same_deadlines_and_same_department_sharing_disabled():
    tasks = [task("A", deadline=stamp(75), department="ENGINEERING", compatibility_group="A"),
             task("B", deadline=stamp(75), department="ENGINEERING", compatibility_group="A")]
    result = compare_plans(data(tasks), ORIGIN, stamp(180))
    assert result["baseline"]["scheduled_task_count"] == 1
    assert result["optimized"]["scheduled_task_count"] == 2
    assert result["optimized"]["integrated_blocks"] == 0  # Same-department sharing.
    for mode in ("baseline", "optimized"):
        assert result[mode]["plan"]["blocks"][0]["end_time"] == stamp(75)


@pytest.mark.parametrize("tasks", [[], [task("TOO_LONG", 500)]])
def test_empty_plan_safe_metrics(tasks):
    result = compare_plans(data(tasks), ORIGIN, stamp(60))
    for mode in ("baseline", "optimized"):
        assert result[mode]["possession_minutes"] == 0
        assert result[mode]["maintenance_delivery_efficiency"] is None
        assert result[mode]["minimum_boundary_slack_minutes"] == 0
        assert result[mode]["total_boundary_slack_minutes"] == 0
    assert result["comparison"]["closure_saved_minutes"] == 0
    assert result["comparison"]["closure_reduction_percent"] is None


def robustness_demo():
    # Equal service, possession, block count; second gap permits much more margin.
    return compare_plans(data([task("A", 60)], [train(70, 100)]),
                         ORIGIN, stamp(240), allowances=ZERO)


def test_larger_boundary_margin_beats_earliest_execution():
    result = robustness_demo()
    for mode in ("baseline", "optimized"):
        block, = result[mode]["plan"]["blocks"]
        assert (block["start_time"], block["end_time"]) == (stamp(140), stamp(200))
        assert result[mode]["minimum_boundary_slack_minutes"] == 40
        assert result[mode]["boundary_slacks"][0]["before_boundary_slack_minutes"] == 40
        assert result[mode]["boundary_slacks"][0]["after_boundary_slack_minutes"] == 40


def test_max_min_protects_weakest_possession_before_total():
    # Coupled synthetic placement alternatives, with real boundary-slack model.
    # A has [40,35,1] (total 76); B has [20,20,20] (total 60).
    model = cp_model.CpModel()
    choose_b = model.NewBoolVar("alternative_b")
    tasks, variables, blocks, windows = [], {}, [], {}
    for i, a_start in enumerate((40, 35, 1)):
        t = task(str(i), 20, section=f"S{i}")
        tasks.append(t)
        present = model.NewBoolVar(f"present_{i}")
        model.Add(present == 1)
        start = model.NewIntVar(0, 180, f"start_{i}")
        model.Add(start == 20).OnlyEnforceIf(choose_b)
        model.Add(start == a_start).OnlyEnforceIf(choose_b.Not())
        variables[t["task_id"]] = dict(start=start, scheduled=present)
        blocks.append(dict(start=start, end=start + 20, size=20, present=present, section_id=f"S{i}"))
        windows[f"S{i}"] = generate_candidate_windows([], [f"S{i}"], ORIGIN, stamp(200), ZERO)
    slacks = add_boundary_slack(model, blocks, windows, ORIGIN, 200)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    facts = []
    assert solve_priorities(model, solver, tasks, variables, blocks, facts, slacks) == cp_model.OPTIMAL
    assert solver.Value(choose_b) == 1
    assert (solver.Value(slacks[0]), solver.Value(slacks[1])) == (20, 60)


def test_robustness_cannot_override_priority_or_possession():
    # A long critical task has zero slack; a short task would have more.
    tasks = [task("CRITICAL", 100, criticality=10), task("SHORT", 40, criticality=1)]
    result = compare_plans(data(tasks), ORIGIN, stamp(100), allowances=ZERO)
    assert result["optimized"]["scheduled_tasks"] == ["CRITICAL"]
    assert result["optimized"]["minimum_boundary_slack_minutes"] == 0
    assert same_work_demo()["optimized"]["possession_minutes"] == 180


def test_failed_plan_not_misreported_as_empty_success(monkeypatch):
    monkeypatch.setattr(comparison, "optimize_schedule", lambda *a, **k: {"status": "unknown"})
    with pytest.raises(RuntimeError, match="baseline planning failed"):
        compare_plans(data([]))


def test_unproven_stage_does_not_fix_incumbent_or_continue():
    class UnprovenSolver:
        def Solve(self, model):
            return cp_model.FEASIBLE
        def StatusName(self, status):
            return "FEASIBLE"
        def Value(self, expression):
            raise AssertionError("An unproven objective must not be fixed")
    model = cp_model.CpModel()
    facts = []
    assert solve_priorities(model, UnprovenSolver(), [], {}, [], facts, (0, 0)) == cp_model.FEASIBLE
    assert len(facts) == 1 and "optimum" not in facts[0]
    assert len(model.Proto().constraints) == 0


@pytest.mark.parametrize("limit", [0, -1, float("inf"), float("nan"), True])
def test_invalid_solver_budget_rejected(limit):
    with pytest.raises(ValueError, match="finite and positive"):
        optimize_schedule(data([]), stage_time_limit_seconds=limit)


if __name__ == "__main__":
    import json
    for name, demo in (("same_work", same_work_demo), ("different_work", different_work_demo), ("robustness", robustness_demo)):
        result = demo()
        print(json.dumps(dict(scenario=name, comparison=result["comparison"],
                              baseline={k: v for k, v in result["baseline"].items() if k not in ("plan", "priority_stages")},
                              optimized={k: v for k, v in result["optimized"].items() if k not in ("plan", "priority_stages")}), indent=2))
