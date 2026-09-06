"""CP-SAT maintenance planning over feasible section/window assignments."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model

try:
    from .time_utils import parse_datetime, datetime_to_minutes, minutes_to_datetime
    from .candidate_windows import CandidateWindow, OperationalAllowances, generate_candidate_windows
    from .feasibility import FeasibilityContext, evaluate_task_in_window, task_requirements
except ImportError:  # Preserve direct-script and existing test imports.
    from time_utils import parse_datetime, datetime_to_minutes, minutes_to_datetime
    from candidate_windows import CandidateWindow, OperationalAllowances, generate_candidate_windows
    from feasibility import FeasibilityContext, evaluate_task_in_window, task_requirements


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
        if not isinstance(block_tasks, list) or len(block_tasks) != 1:
            raise ValueError(f"{block_id} must contain exactly one task on Day 1.")

        task_id = block_tasks[0]
        if task_id not in task_by_id:
            raise ValueError(f"{block_id} references unknown task {task_id!r}.")
        if task_id in scheduled_task_ids:
            raise ValueError(f"Task {task_id!r} is scheduled more than once.")
        scheduled_task_ids.add(task_id)

        task = task_by_id[task_id]
        start_time = parse_datetime(block["start_time"])
        end_time = parse_datetime(block["end_time"])
        if not start_time < end_time:
            raise ValueError(f"{block_id} must start before it ends.")
        if start_time < horizon_start_dt or end_time > horizon_end_dt:
            raise ValueError(f"{block_id} lies outside the planning horizon.")

        actual_duration = (end_time - start_time).total_seconds() / 60
        if actual_duration != task_requirements(task, allowances).required_minutes:
            raise ValueError(
                f"{block_id} duration does not match task {task_id!r}."
            )
        if block["section_id"] != task["section_id"]:
            raise ValueError(
                f"{block_id} section does not match task {task_id!r}."
            )

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
) -> dict[str, Any]:
    """Reserve setup/work/release in feasible windows; return full possession blocks."""
    maintenance_tasks, train_occupancy = _validate_input_data(data)
    horizon_start_dt = parse_datetime(horizon_start)
    horizon_end_dt = parse_datetime(horizon_end)
    horizon_minutes = datetime_to_minutes(horizon_end_dt, horizon_start_dt)
    if horizon_minutes <= 0:
        raise ValueError("horizon_end must be later than horizon_start.")

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
    intervals_by_section: dict[str, list[Any]] = {}

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
        intervals_by_section.setdefault(task["section_id"], []).append(interval)
        task_variables[task_id] = {
            "scheduled": scheduled,
            "start": start,
            "end": end,
        }

        choices = []
        for window in windows_by_section.get(task["section_id"], []):
            feasibility = evaluate_task_in_window(
                task, window, window_contexts.get(window.window_id), allowances,
            )
            if not feasibility.feasible:
                continue
            chosen = model.NewBoolVar(f"task_{task_index}_{window.window_id}")
            choices.append(chosen)
            earliest = datetime_to_minutes(window.usable_start, horizon_start_dt)
            latest = datetime_to_minutes(
                feasibility.latest_reservation_start, horizon_start_dt
            )
            window_end = datetime_to_minutes(window.usable_end, horizon_start_dt)
            model.Add(start >= earliest).OnlyEnforceIf(chosen)
            model.Add(start <= latest).OnlyEnforceIf(chosen)
            model.Add(end <= window_end).OnlyEnforceIf(chosen)
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

    for section_intervals in intervals_by_section.values():
        if len(section_intervals) > 1:
            model.AddNoOverlap(section_intervals)

    scheduled_variables = [
        variables["scheduled"] for variables in task_variables.values()
    ]
    start_variables = [variables["start"] for variables in task_variables.values()]
    primary_weight = len(maintenance_tasks) * horizon_minutes + 1
    model.Maximize(
        primary_weight * sum(scheduled_variables) - sum(start_variables)
    )

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver_status = solver.Solve(model)

    if solver_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
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

    scheduled_results: list[tuple[int, str, dict[str, Any]]] = []
    unscheduled_tasks: list[str] = []
    for task in maintenance_tasks:
        variables = task_variables[task["task_id"]]
        if solver.Value(variables["scheduled"]):
            scheduled_results.append(
                (solver.Value(variables["start"]), task["task_id"], task)
            )
        else:
            unscheduled_tasks.append(task["task_id"])

    scheduled_results.sort(key=lambda item: (item[0], item[2]["section_id"], item[1]))
    blocks: list[dict[str, Any]] = []
    for block_index, (start_minute, task_id, task) in enumerate(
        scheduled_results, start=1
    ):
        end_minute = start_minute + task_requirements(task, allowances).required_minutes
        start_time = parse_datetime(minutes_to_datetime(start_minute, horizon_start_dt))
        end_time = parse_datetime(minutes_to_datetime(end_minute, horizon_start_dt))
        blocks.append(
            {
                "block_id": f"BLK{block_index:03d}",
                "section_id": task["section_id"],
                "start_time": start_time.isoformat(timespec="seconds"),
                "end_time": end_time.isoformat(timespec="seconds"),
                "tasks": [task_id],
                "integrated": False,
                "affected_trains": _affected_train_ids(
                    task["section_id"], start_time, end_time, train_occupancy
                ),
                "explanation": [
                    "Scheduled outside protected train occupancy"
                ],
            }
        )

    # Independently check the chosen actual reservation, not just earliest fit.
    reservations: dict[str, list[tuple[int, int]]] = {}
    task_by_id = {task["task_id"]: task for task in maintenance_tasks}
    for block in blocks:
        task = task_by_id[block["tasks"][0]]
        requirement = task_requirements(task, allowances)
        start = datetime_to_minutes(block["start_time"], horizon_start_dt)
        end = start + requirement.required_minutes
        reservation_start = minutes_to_datetime(start, horizon_start_dt)
        legal = any(
            evaluate_task_in_window(
                task, window, window_contexts.get(window.window_id), allowances,
                reservation_start=reservation_start,
            ).feasible
            for window in windows_by_section.get(task["section_id"], [])
        )
        if not legal:
            raise ValueError(f"Infeasible reservation for {task['task_id']}.")
        for other_start, other_end in reservations.get(task["section_id"], []):
            if start < other_end and other_start < end:
                raise ValueError("Maintenance setup/work/release reservations overlap.")
        reservations.setdefault(task["section_id"], []).append((start, end))

    validate_solution(
        blocks,
        maintenance_tasks,
        train_occupancy,
        horizon_start_dt,
        horizon_end_dt,
        allowances=allowances,
    )
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
