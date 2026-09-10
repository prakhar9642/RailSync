"""Deterministic tests for one-budget lexicographic runtime control."""

import sys
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimizer as optimizer_module
if hasattr(optimizer_module, "__path__"):
    from optimizer import optimizer as optimizer_module
from comparison import compare_plans
from optimizer import optimize_schedule
from possessions import solve_priorities
from resources import PowerWindow, ResourceContext
from runtime import DEMO_SOLVE_LIMIT_SECONDS, PlanProofState


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class ScriptedSolver:
    def __init__(self, status, value, clock, duration=0.0, constraint_counts=None):
        self.status = status
        self.value = value
        self.clock = clock
        self.duration = duration
        self.constraint_counts = constraint_counts

    def Solve(self, model):
        if self.constraint_counts is not None:
            self.constraint_counts.append(len(model.Proto().constraints))
        self.clock.now += self.duration
        return self.status

    def StatusName(self, status):
        return {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.UNKNOWN: "UNKNOWN",
            cp_model.INFEASIBLE: "INFEASIBLE",
        }[status]

    def Value(self, expression):
        return self.value


def controller(statuses, durations, *, deadline=None):
    clock = Clock()
    constraints = []
    remaining_seen = []
    scripted = [
        ScriptedSolver(status, index + 1, clock, duration, constraints)
        for index, (status, duration) in enumerate(zip(statuses, durations))
    ]

    def factory(template, remaining):
        remaining_seen.append(remaining)
        return scripted.pop(0)

    model = cp_model.CpModel()
    facts = []
    result = solve_priorities(
        model,
        object(),
        [],
        {},
        [],
        facts,
        (0, 0),
        deadline=deadline,
        clock=clock,
        solver_factory=factory,
    )
    return result, facts, constraints, remaining_seen


def test_uncapped_and_finite_real_solves_preserve_plan():
    data = {
        "maintenance_tasks": [
            {"task_id": "A", "section_id": "SEC01", "duration_minutes": 30}
        ],
        "train_occupancy": [],
    }
    uncapped_facts = {}
    bounded_facts = {}
    uncapped = optimize_schedule(data, diagnostics=uncapped_facts)
    bounded = optimize_schedule(
        data, time_limit_seconds=DEMO_SOLVE_LIMIT_SECONDS, diagnostics=bounded_facts
    )
    assert bounded == uncapped
    assert uncapped_facts["proof_state"] == "FULLY_OPTIMAL"
    assert bounded_facts["proof_state"] == "FULLY_OPTIMAL"
    assert bounded_facts["time_limit_seconds"] == DEMO_SOLVE_LIMIT_SECONDS


def test_total_budget_is_shared_and_proven_stage_is_fixed():
    result, facts, constraints, remaining = controller(
        [cp_model.OPTIMAL, cp_model.FEASIBLE], [2.0, 3.0], deadline=10.0
    )
    assert remaining == [10.0, 8.0]
    assert constraints == [0, 1]
    assert result.solver_status == cp_model.FEASIBLE
    assert result.proof_state == PlanProofState.FEASIBLE_BOUNDED
    assert result.solver.value == 2
    assert facts[0]["objective_value"] == 1 and facts[0]["optimum"] == 1
    assert facts[1]["objective_value"] == 2 and "optimum" not in facts[1]
    assert facts[1]["termination_reason"] == "TIME_LIMIT"
    assert all(stage["status"] == "NOT_RUN" for stage in facts[2:])


def test_expired_total_budget_skips_remaining_stages():
    result, facts, constraints, remaining = controller(
        [cp_model.OPTIMAL], [5.0], deadline=5.0
    )
    assert remaining == [5.0]
    assert result.solver.value == 1
    assert result.proof_state == PlanProofState.FEASIBLE_BOUNDED
    assert facts[0]["status"] == "OPTIMAL"
    assert len(facts) == 9
    assert all(stage["status"] == "NOT_RUN" for stage in facts[1:])
    assert facts[1]["termination_reason"] == "TIME_LIMIT"


def test_previous_proven_solution_survives_later_unknown():
    result, facts, constraints, _ = controller(
        [cp_model.OPTIMAL, cp_model.UNKNOWN], [1.0, 9.0], deadline=10.0
    )
    assert result.solver.value == 1
    assert result.solver_status == cp_model.OPTIMAL
    assert result.proof_state == PlanProofState.FEASIBLE_BOUNDED
    assert facts[1]["status"] == "UNKNOWN"
    assert facts[1]["objective_value"] is None
    assert facts[2]["status"] == "NOT_RUN"


def test_first_feasible_incumbent_survives_timeout():
    result, facts, _, _ = controller([cp_model.FEASIBLE], [10.0], deadline=10.0)
    assert result.solver.value == 1
    assert result.proof_state == PlanProofState.FEASIBLE_BOUNDED
    assert facts[0]["status"] == "FEASIBLE"
    assert facts[0]["termination_reason"] == "TIME_LIMIT"


def test_no_solution_and_infeasible_are_distinct():
    unknown, unknown_facts, _, _ = controller(
        [cp_model.UNKNOWN], [1.0], deadline=1.0
    )
    infeasible, infeasible_facts, _, _ = controller(
        [cp_model.INFEASIBLE], [0.0]
    )
    assert unknown.solver is None and unknown.proof_state == PlanProofState.NO_SOLUTION
    assert infeasible.solver is None and infeasible.proof_state == PlanProofState.INFEASIBLE
    assert unknown_facts[0]["termination_reason"] == "TIME_LIMIT"
    assert infeasible_facts[0]["status"] == "INFEASIBLE"


def test_real_infeasible_model_remains_infeasible():
    model = cp_model.CpModel()
    value = model.NewBoolVar("contradiction")
    model.Add(value == 0)
    model.Add(value == 1)
    facts = []
    result = solve_priorities(
        model, cp_model.CpSolver(), [], {}, [], facts, (0, 0)
    )
    assert result.solver is None
    assert result.proof_state == PlanProofState.INFEASIBLE
    assert facts[0]["status"] == "INFEASIBLE"
    assert all(stage["status"] == "NOT_RUN" for stage in facts[1:])


def test_full_stage_order_and_proof_state():
    result, facts, constraints, _ = controller(
        [cp_model.OPTIMAL] * 9, [0.0] * 9
    )
    assert result.proof_state == PlanProofState.FULLY_OPTIMAL
    assert [stage["stage"] for stage in facts] == [
        "criticality",
        "urgency",
        "overdue_days",
        "task_count",
        "possession_minutes",
        "block_count",
        "minimum_boundary_slack_minutes",
        "total_boundary_slack_minutes",
        "start_minutes",
    ]
    assert constraints == list(range(9))
    assert all(stage["termination_reason"] == "PROVEN_OPTIMAL" for stage in facts)


def test_comparison_passes_same_total_budget_and_labels_proof():
    data = {
        "maintenance_tasks": [
            {"task_id": "A", "section_id": "SEC01", "duration_minutes": 30}
        ],
        "train_occupancy": [],
    }
    compared = compare_plans(data, time_limit_seconds=DEMO_SOLVE_LIMIT_SECONDS)
    assert compared["baseline"]["time_limit_seconds"] == DEMO_SOLVE_LIMIT_SECONDS
    assert compared["optimized"]["time_limit_seconds"] == DEMO_SOLVE_LIMIT_SECONDS
    assert compared["both_proven_optimal"]
    assert compared["comparison_proof_state"] == "FULLY_OPTIMAL"
    assert compared["comparison"]["same_task_set"]


def test_bounded_comparison_returns_valid_constraint_safe_plans(monkeypatch):
    """Force the deadline between stages without depending on millisecond timing."""

    class StepClock:
        def __init__(self):
            self.calls = 0

        def __call__(self):
            self.calls += 1
            return 0.0 if self.calls <= 3 else 1.0

    original_controller = optimizer_module.solve_priorities

    def stop_after_first_stage(*args, **kwargs):
        kwargs["deadline"] = 0.5
        kwargs["clock"] = StepClock()
        return original_controller(*args, **kwargs)

    monkeypatch.setattr(optimizer_module, "solve_priorities", stop_after_first_stage)
    planning_data = {
        "maintenance_tasks": [
            {
                "task_id": "ENG",
                "section_id": "SEC03",
                "department": "ENGINEERING",
                "duration_minutes": 30,
                "criticality": 10,
                "compatibility_group": "A",
                "crew_type": "POOL",
            },
            {
                "task_id": "SNT",
                "section_id": "SEC03",
                "department": "S&T",
                "duration_minutes": 30,
                "criticality": 9,
                "compatibility_group": "A",
                "crew_type": "POOL",
                "requires_power_block": True,
            },
        ],
        "train_occupancy": [
            {
                "train_id": "TR1",
                "section_id": "SEC03",
                "entry_time": "2026-09-01T00:00:00",
                "exit_time": "2026-09-01T00:10:00",
            },
            {
                "train_id": "TR2",
                "section_id": "SEC03",
                "entry_time": "2026-09-01T02:30:00",
                "exit_time": "2026-09-01T03:00:00",
            },
        ],
    }
    resources = ResourceContext(
        crew_capacities={"POOL": 1},
        power_windows={
            "SEC03": (
                PowerWindow("2026-09-01T00:25:00", "2026-09-01T02:15:00"),
            )
        },
    )
    compared = compare_plans(
        planning_data,
        "2026-09-01T00:00:00",
        "2026-09-01T03:00:00",
        resource_context=resources,
        time_limit_seconds=DEMO_SOLVE_LIMIT_SECONDS,
    )
    assert compared["comparison_proof_state"] == "FEASIBLE_BOUNDED"
    assert compared["comparison"]["same_task_set"]
    for mode in ("baseline", "optimized"):
        plan = compared[mode]["plan"]
        assert compared[mode]["proof_state"] == "FEASIBLE_BOUNDED"
        assert compared[mode]["scheduled_task_count"] == 2
        assert compared[mode]["possession_minutes"] == 90
        assert len(plan["blocks"]) == 2  # Exclusive crew prevents sharing.
        assert all(not block["affected_trains"] for block in plan["blocks"])
        assert compared[mode]["priority_stages"][0]["status"] == "OPTIMAL"
        assert all(
            stage["status"] == "NOT_RUN"
            for stage in compared[mode]["priority_stages"][1:]
        )


@pytest.mark.parametrize("limit", [0, -1, float("inf"), float("nan"), True])
def test_invalid_total_budget_rejected(limit):
    with pytest.raises(ValueError, match="finite and positive"):
        optimize_schedule(
            {"maintenance_tasks": [], "train_occupancy": []},
            time_limit_seconds=limit,
        )


def test_two_limit_names_cannot_be_combined():
    with pytest.raises(ValueError, match="only one"):
        optimize_schedule(
            {"maintenance_tasks": [], "train_occupancy": []},
            time_limit_seconds=1,
            stage_time_limit_seconds=1,
        )


def test_legacy_limit_keyword_remains_accepted_as_total_budget():
    facts = {}
    plan = optimize_schedule(
        {"maintenance_tasks": [], "train_occupancy": []},
        stage_time_limit_seconds=DEMO_SOLVE_LIMIT_SECONDS,
        diagnostics=facts,
    )
    assert plan["status"] == "success"
    assert facts["time_limit_seconds"] == DEMO_SOLVE_LIMIT_SECONDS
