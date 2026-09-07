"""CP-SAT maintenance planning over feasible section/window assignments."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from itertools import combinations
from time import perf_counter
from typing import Any

from ortools.sat.python import cp_model

try:
    from .time_utils import parse_datetime, datetime_to_minutes, minutes_to_datetime
    from .candidate_windows import CandidateWindow, OperationalAllowances, generate_candidate_windows
    from .feasibility import FeasibilityContext, evaluate_task_in_window, task_requirements
    from .compatibility import CompatibilityPolicy, evaluate_compatibility
    from .resources import ResourceContext, add_capacity_constraints, validate_capacities
    from .possessions import build_possessions, solve_priorities
    from .robustness import add_boundary_slack
    from .metrics import summarize_plan
    from .runtime import PlanProofState, validate_time_limit
except ImportError:  # Preserve direct-script and existing test imports.
    from time_utils import parse_datetime, datetime_to_minutes, minutes_to_datetime
    from candidate_windows import CandidateWindow, OperationalAllowances, generate_candidate_windows
    from feasibility import FeasibilityContext, evaluate_task_in_window, task_requirements
    from compatibility import CompatibilityPolicy, evaluate_compatibility
    from resources import ResourceContext, add_capacity_constraints, validate_capacities
    from possessions import build_possessions, solve_priorities
    from robustness import add_boundary_slack
    from metrics import summarize_plan
    from runtime import PlanProofState, validate_time_limit


DEFAULT_HORIZON_START = "2026-09-01T00:00:00"
DEFAULT_HORIZON_END = "2026-09-01T06:00:00"
DEFAULT_DATA_PATH = Path(__file__).resolve().parents[1] / "backend" / "mock-data.json"


def load_mock_data(path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    """Load RailSync JSON input from the repository's backend directory."""
    data_path = Path(path)
    with data_path.open("r", encoding="utf-8") as data_file:
        data = json.load(data_file)

    if not isinstance(data, dict):
        raise ValueError("Mock data must contain a JSON object at the top level.")
    return data


def _validate_input_data(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate the Day 1 fields needed to build the CP-SAT model."""
    if not isinstance(data, dict):
        raise TypeError("Optimizer input data must be a dictionary.")

    maintenance_tasks = data.get("maintenance_tasks")
    train_occupancy = data.get("train_occupancy")
    if not isinstance(maintenance_tasks, list):
        raise ValueError("Input field 'maintenance_tasks' must be a list.")
    if not isinstance(train_occupancy, list):
        raise ValueError("Input field 'train_occupancy' must be a list.")

    task_ids: set[str] = set()
    for task in maintenance_tasks:
        if not isinstance(task, dict):
            raise ValueError("Every maintenance task must be a JSON object.")
        for field in ("task_id", "section_id", "duration_minutes"):
            if field not in task:
                raise ValueError(f"Maintenance task is missing required field {field!r}.")

        task_id = task["task_id"]
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("Every task_id must be a non-empty string.")
        if task_id in task_ids:
            raise ValueError(f"Duplicate maintenance task_id: {task_id!r}.")
        task_ids.add(task_id)

        if not isinstance(task["section_id"], str) or not task["section_id"]:
            raise ValueError(f"Task {task_id!r} must have a non-empty section_id.")
        duration = task["duration_minutes"]
        if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
            raise ValueError(
                f"Task {task_id!r} must have a positive integer duration_minutes."
            )

    for occupancy in train_occupancy:
        if not isinstance(occupancy, dict):
            raise ValueError("Every train occupancy must be a JSON object.")
        for field in ("train_id", "section_id", "entry_time", "exit_time"):
            if field not in occupancy:
                raise ValueError(f"Train occupancy is missing required field {field!r}.")

        entry_time = parse_datetime(occupancy["entry_time"])
        exit_time = parse_datetime(occupancy["exit_time"])
        try:
            is_valid_interval = entry_time < exit_time
        except TypeError as error:
            raise ValueError(
                f"Train {occupancy['train_id']!r} has incompatible timestamp timezones."
            ) from error
        if not is_valid_interval:
            raise ValueError(
                f"Train {occupancy['train_id']!r} must enter before it exits."
            )

    return maintenance_tasks, train_occupancy


def _intervals_overlap(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> bool:
    """Return whether two half-open intervals overlap."""
    return first_start < second_end and second_start < first_end


def _affected_train_ids(
    section_id: str,
    start_time: datetime,
    end_time: datetime,
    train_occupancy: list[dict[str, Any]],
) -> list[str]:
    """Calculate train IDs whose occupancy overlaps a block on its section."""
    affected: set[str] = set()
    for occupancy in train_occupancy:
        if occupancy["section_id"] != section_id:
            continue
        if _intervals_overlap(
            start_time,
            end_time,
            parse_datetime(occupancy["entry_time"]),
            parse_datetime(occupancy["exit_time"]),
        ):
            affected.add(occupancy["train_id"])
    return sorted(affected)


def validate_solution(
    blocks: list[dict[str, Any]],
    maintenance_tasks: list[dict[str, Any]],
    train_occupancy: list[dict[str, Any]],
    horizon_start: str | datetime = DEFAULT_HORIZON_START,
    horizon_end: str | datetime = DEFAULT_HORIZON_END,
    *,
    allowances: OperationalAllowances = OperationalAllowances(),
    compatibility_policy: CompatibilityPolicy = CompatibilityPolicy(),
) -> None:
    """Raise a clear error if any generated Day 1 block is invalid."""
    task_by_id = {task["task_id"]: task for task in maintenance_tasks}
    horizon_start_dt = parse_datetime(horizon_start)
    horizon_end_dt = parse_datetime(horizon_end)
    scheduled_task_ids: set[str] = set()
    parsed_blocks: list[tuple[dict[str, Any], datetime, datetime]] = []

    for block in blocks:
        block_id = block.get("block_id", "<unknown block>")
        block_tasks = block.get("tasks")
        if not isinstance(block_tasks, list) or not block_tasks:
            raise ValueError(f"{block_id} must contain tasks.")
        members = []
        for task_id in block_tasks:
            if task_id not in task_by_id or task_id in scheduled_task_ids:
                raise ValueError(f"Unknown or duplicate task: {task_id}")
            scheduled_task_ids.add(task_id)
            members.append(task_by_id[task_id])
        for first, second in combinations(members, 2):
            if not evaluate_compatibility(first, second, compatibility_policy).eligible:
                raise ValueError(f"{block_id} contains incompatible tasks.")
        departments = {task.get("department") for task in members if task.get("department")}
        if block["integrated"] != (len(departments) >= 2):
            raise ValueError(f"{block_id} has an incorrect integrated flag.")
        start_time = parse_datetime(block["start_time"])
        end_time = parse_datetime(block["end_time"])
        if not start_time < end_time:
            raise ValueError(f"{block_id} must start before it ends.")
        if start_time < horizon_start_dt or end_time > horizon_end_dt:
            raise ValueError(f"{block_id} lies outside the planning horizon.")

        actual_duration = (end_time - start_time).total_seconds() / 60
        expected = max(task_requirements(task, allowances).required_minutes for task in members)
        if actual_duration != expected:
            raise ValueError(f"{block_id} duration does not match synchronized possession.")
        if any(block["section_id"] != task["section_id"] for task in members):
            raise ValueError(f"{block_id} has mismatched task sections.")

        affected_trains = _affected_train_ids(
            block["section_id"], start_time, end_time, train_occupancy
        )
        if affected_trains:
            raise ValueError(
                f"{block_id} overlaps train occupancy for {affected_trains}."
            )
        parsed_blocks.append((block, start_time, end_time))

    for index, (block, start_time, end_time) in enumerate(parsed_blocks):
        for other_block, other_start, other_end in parsed_blocks[index + 1 :]:
            if block["section_id"] != other_block["section_id"]:
                continue
            if _intervals_overlap(start_time, end_time, other_start, other_end):
                raise ValueError(
                    f"{block['block_id']} overlaps {other_block['block_id']} "
                    f"on section {block['section_id']!r}."
                )


def calculate_metrics(
    maintenance_tasks: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    train_occupancy: list[dict[str, Any]],
) -> dict[str, int | float]:
    """Sum possession section-hours; baseline zero means unavailable, not savings.

    maintenance_tasks is retained for call compatibility, not baseline estimation.
    """
    optimized_minutes = 0
    affected_train_ids: set[str] = set()

    for block in blocks:
        start_time = parse_datetime(block["start_time"])
        end_time = parse_datetime(block["end_time"])
        optimized_minutes += int((end_time - start_time).total_seconds() // 60)
        affected_train_ids.update(
            _affected_train_ids(
                block["section_id"], start_time, end_time, train_occupancy
            )
        )

    return {
        "baseline_block_hours": 0,
        "optimized_block_hours": round(optimized_minutes / 60, 3),
        # No baseline schedule is supplied, so its affected trains are not measurable.
        "baseline_affected_trains": 0,
        "optimized_affected_trains": len(affected_train_ids),
        "integrated_blocks": sum(bool(block["integrated"]) for block in blocks),
    }


def optimize_schedule(
    data: dict[str, Any],
    horizon_start: str = DEFAULT_HORIZON_START,
    horizon_end: str = DEFAULT_HORIZON_END,
    *,
    allowances: OperationalAllowances = OperationalAllowances(),
    window_contexts: dict[str, FeasibilityContext] | None = None,
    resource_context: ResourceContext | None = None,
    compatibility_policy: CompatibilityPolicy = CompatibilityPolicy(),
    diagnostics: dict[str, Any] | None = None,
    allow_integration: bool = True,
    time_limit_seconds: float | None = None,
    # Backward-compatible internal alias; it now means one total run budget.
    stage_time_limit_seconds: float | None = None,
) -> dict[str, Any]:
    """Reserve setup/work/release in feasible windows; return full possession blocks."""
    planning_started = perf_counter()
    validate_time_limit(time_limit_seconds)
    validate_time_limit(stage_time_limit_seconds, "stage_time_limit_seconds")
    if time_limit_seconds is not None and stage_time_limit_seconds is not None:
        raise ValueError("Specify only one optimization time limit.")
    total_time_limit = (
        time_limit_seconds
        if time_limit_seconds is not None
        else stage_time_limit_seconds
    )
    deadline = (
        planning_started + total_time_limit
        if total_time_limit is not None
        else None
    )
    if not isinstance(allow_integration, bool):
        raise ValueError("allow_integration must be boolean.")
    if not allow_integration:
        compatibility_policy = replace(compatibility_policy, allow_same_group=False)
    maintenance_tasks, train_occupancy = _validate_input_data(data)
    horizon_start_dt = parse_datetime(horizon_start)
    horizon_end_dt = parse_datetime(horizon_end)
    horizon_minutes = datetime_to_minutes(horizon_end_dt, horizon_start_dt)
    if horizon_minutes <= 0:
        raise ValueError("horizon_end must be later than horizon_start.")

    if resource_context is not None:
        resource_context.validate_times(horizon_start_dt)
    facts = diagnostics if diagnostics is not None else {}
    facts.update(pair_checks=[], task_windows=[], priority_stages=[], outcomes={})
    windows = generate_candidate_windows(
        train_occupancy,
        {task["section_id"] for task in maintenance_tasks}
        | {row["section_id"] for row in train_occupancy}
        | {section["section_id"] for section in data.get("sections", [])},
        horizon_start_dt, horizon_end_dt, allowances,
    )
    windows_by_section: dict[str, list[CandidateWindow]] = {}
    for window in windows:
        windows_by_section.setdefault(window.section_id, []).append(window)
    window_contexts = window_contexts or {}
    model = cp_model.CpModel()
    task_variables: dict[str, dict[str, Any]] = {}

    for task_index, task in enumerate(maintenance_tasks):
        task_id = task["task_id"]
        requirement = task_requirements(task, allowances)
        duration = requirement.required_minutes
        scheduled = model.NewBoolVar(f"task_{task_index}_scheduled")
        start = model.NewIntVar(0, horizon_minutes, f"task_{task_index}_start")
        end = model.NewIntVar(0, horizon_minutes, f"task_{task_index}_end")

        model.Add(end == start + duration).OnlyEnforceIf(scheduled)
        model.Add(start == 0).OnlyEnforceIf(scheduled.Not())
        model.Add(end == 0).OnlyEnforceIf(scheduled.Not())
        if duration > horizon_minutes:
            model.Add(scheduled == 0)

        interval = model.NewOptionalIntervalVar(
            start, duration, end, scheduled, f"task_{task_index}_interval"
        )
        task_variables[task_id] = {
            "scheduled": scheduled,
            "start": start,
            "end": end,
            "interval": interval,
        }

        choices = []
        for window in windows_by_section.get(task["section_id"], []):
            feasibility = evaluate_task_in_window(
                task, window, window_contexts.get(window.window_id), allowances,
                resource_context=resource_context,
            )
            facts["task_windows"].append(dict(
                task_id=task_id, window_id=window.window_id, feasible=feasibility.feasible,
                reasons=[reason.value for reason in feasibility.reasons],
                resource_checks={k: v.value for k, v in feasibility.resource_checks.items()},
            ))
            if not feasibility.feasible:
                continue
            for range_index, (range_start, range_end) in enumerate(feasibility.start_ranges):
                chosen = model.NewBoolVar(f"task_{task_index}_{window.window_id}_{range_index}")
                choices.append(chosen)
                earliest = datetime_to_minutes(range_start, horizon_start_dt)
                latest = datetime_to_minutes(range_end, horizon_start_dt)
                model.Add(start >= earliest).OnlyEnforceIf(chosen)
                model.Add(start <= latest).OnlyEnforceIf(chosen)
        model.Add(sum(choices) == scheduled)

        for train_index, occupancy in enumerate(train_occupancy):
            if occupancy["section_id"] != task["section_id"]:
                continue

            train_entry = datetime_to_minutes(
                occupancy["entry_time"], horizon_start_dt
            )
            train_exit = datetime_to_minutes(
                occupancy["exit_time"], horizon_start_dt
            )
            if train_exit <= 0 or train_entry >= horizon_minutes:
                continue

            protected_entry = max(0, train_entry)
            protected_exit = min(horizon_minutes, train_exit)
            before_train = model.NewBoolVar(
                f"task_{task_index}_before_train_{train_index}"
            )
            after_train = model.NewBoolVar(
                f"task_{task_index}_after_train_{train_index}"
            )

            model.Add(end <= protected_entry).OnlyEnforceIf(
                [scheduled, before_train]
            )
            model.Add(start >= protected_exit).OnlyEnforceIf(
                [scheduled, after_train]
            )
            model.AddBoolOr([scheduled.Not(), before_train, after_train])
            model.AddImplication(before_train, scheduled)
            model.AddImplication(after_train, scheduled)

    possession_variables = build_possessions(
        model, maintenance_tasks, task_variables, horizon_minutes, allowances,
        compatibility_policy, facts["pair_checks"], resource_context,
    )
    slack_objectives = add_boundary_slack(
        model, possession_variables, windows_by_section, horizon_start_dt, horizon_minutes,
    )
    add_capacity_constraints(model, maintenance_tasks, task_variables, resource_context)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solve_result = solve_priorities(
        model, solver, maintenance_tasks, task_variables, possession_variables,
        facts["priority_stages"], slack_objectives, deadline=deadline,
    )
    solver_status = solve_result.solver_status
    solver = solve_result.solver
    facts["proof_state"] = solve_result.proof_state.value
    facts["last_stage_reached"] = solve_result.last_stage_reached
    facts["solution_stage"] = solve_result.solution_stage
    facts["time_limit_seconds"] = total_time_limit
    facts["planning_elapsed_seconds"] = perf_counter() - planning_started

    if solver is None:
        status_name = {
            cp_model.INFEASIBLE: "infeasible",
            cp_model.MODEL_INVALID: "model_invalid",
            cp_model.UNKNOWN: "unknown",
        }.get(solver_status, "solver_error")
        empty_blocks: list[dict[str, Any]] = []
        return {
            "status": status_name,
            "blocks": empty_blocks,
            "unscheduled_tasks": [task["task_id"] for task in maintenance_tasks],
            "metrics": calculate_metrics(
                maintenance_tasks, empty_blocks, train_occupancy
            ),
        }

    unscheduled_tasks = [task["task_id"] for task in maintenance_tasks
                         if not solver.Value(task_variables[task["task_id"]]["scheduled"])]
    scheduled_results = []
    for possession in possession_variables:
        if solver.Value(possession["present"]):
            members = [maintenance_tasks[i] for i, member in possession["members"].items()
                       if solver.Value(member)]
            scheduled_results.append((solver.Value(possession["start"]),
                                      solver.Value(possession["end"]), possession["section_id"], members))
    scheduled_results.sort(key=lambda item: (item[0], item[2], sorted(t["task_id"] for t in item[3])))
    blocks = []
    reservations = []
    for index, (start, end, section, members) in enumerate(scheduled_results, 1):
        start_time = minutes_to_datetime(start, horizon_start_dt)
        end_time = minutes_to_datetime(end, horizon_start_dt)
        departments = {t.get("department") for t in members if t.get("department")}
        blocks.append(dict(
            block_id=f"BLK{index:03d}", section_id=section,
            start_time=start_time, end_time=end_time,
            tasks=sorted(t["task_id"] for t in members), integrated=len(departments) >= 2,
            affected_trains=_affected_train_ids(section, parse_datetime(start_time),
                                               parse_datetime(end_time), train_occupancy),
            explanation=["Scheduled outside protected train occupancy"],
        ))
        for task in members:
            legal = any(evaluate_task_in_window(
                task, window, window_contexts.get(window.window_id), allowances,
                reservation_start=start_time, resource_context=resource_context,
            ).feasible for window in windows_by_section[section])
            if not legal:
                raise ValueError(f"Infeasible reservation for {task['task_id']}.")
            reservations.append((task, start, start + task_requirements(task, allowances).required_minutes))
    validate_capacities(reservations, resource_context)
    for task in maintenance_tasks:
        task_id = task["task_id"]
        if task_id not in unscheduled_tasks:
            facts["outcomes"][task_id] = "SELECTED"
        elif any(f["feasible"] for f in facts["task_windows"] if f["task_id"] == task_id):
            facts["outcomes"][task_id] = ("LOWER_PRIORITY_THAN_SELECTED_WORK"
                if solve_result.proof_state == PlanProofState.FULLY_OPTIMAL
                else "NOT_SELECTED_UNPROVEN_OPTIMUM")
        else:
            facts["outcomes"][task_id] = "NO_FEASIBLE_TASK_WINDOW"

    validate_solution(
        blocks,
        maintenance_tasks,
        train_occupancy,
        horizon_start_dt,
        horizon_end_dt,
        allowances=allowances,
        compatibility_policy=compatibility_policy,
    )
    facts["service_metrics"] = summarize_plan(maintenance_tasks, blocks, windows, allowances)
    for key, expression in zip(
        ("minimum_boundary_slack_minutes", "total_boundary_slack_minutes"), slack_objectives
    ):
        if facts["service_metrics"][key] != solver.Value(expression):
            raise ValueError("Solved boundary slack does not match possession timestamps.")
    return {
        "status": "success",
        "blocks": blocks,
        "unscheduled_tasks": unscheduled_tasks,
        "metrics": calculate_metrics(
            maintenance_tasks, blocks, train_occupancy
        ),
    }


if __name__ == "__main__":
    mock_data = load_mock_data()
    result = optimize_schedule(mock_data)
    print(json.dumps(result, indent=2))
