"""Solver-level synchronized possessions and exact lexicographic objectives."""

from itertools import combinations
from time import perf_counter

from ortools.sat.python import cp_model

try:
    from .compatibility import evaluate_compatibility
    from .feasibility import task_requirements
    from .runtime import (
        LexicographicSolveResult,
        OBJECTIVE_STAGE_NAMES,
        PlanProofState,
    )
except ImportError:
    from compatibility import evaluate_compatibility
    from feasibility import task_requirements
    from runtime import LexicographicSolveResult, OBJECTIVE_STAGE_NAMES, PlanProofState


def build_possessions(model, tasks, variables, horizon, allowances, policy, facts, resources):
    """One potential block per anchor task, avoiding enumeration of all subsets.

    The lowest-index member anchors a block. Every task can still own a separate
    block; assigning the same candidate window does not force concurrency.
    """
    eligible = {}
    for i, j in combinations(range(len(tasks)), 2):
        decision = evaluate_compatibility(tasks[i], tasks[j], policy)
        eligible[i, j] = decision.eligible
        reasons = [decision.reason]
        if resources:
            for field, pools, reason in (
                ("crew_type", resources.crew_capacities, "CREW_CAPACITY_CONFLICT"),
                ("machine_type", resources.machine_capacities, "MACHINE_CAPACITY_CONFLICT"),
            ):
                pool = tasks[i].get(field)
                if pool and pool == tasks[j].get(field) and pool in pools and pools[pool] < 2:
                    reasons.append(reason)
        facts.append(dict(tasks=[tasks[i]["task_id"], tasks[j]["task_id"]],
                          status=decision.status.value, reasons=reasons))
    assignments = {i: [] for i in range(len(tasks))}
    blocks = []
    capacity_intervals = {}
    for anchor, task in enumerate(tasks):
        start = model.NewIntVar(0, horizon, f"block_{anchor}_start")
        end = model.NewIntVar(0, horizon, f"block_{anchor}_end")
        size = model.NewIntVar(0, horizon, f"block_{anchor}_size")
        present = model.NewBoolVar(f"block_{anchor}_present")
        members = {}
        for i in range(anchor, len(tasks)):
            if i != anchor and not eligible[anchor, i]:
                continue
            member = model.NewBoolVar(f"block_{anchor}_task_{i}")
            members[i] = member
            assignments[i].append(member)
            model.AddImplication(member, present)
            model.Add(variables[tasks[i]["task_id"]]["start"] == start).OnlyEnforceIf(member)
        model.Add(members[anchor] == present)
        for i, j in combinations(members, 2):
            if not eligible[i, j]:
                model.Add(members[i] + members[j] <= 1)
        model.AddMaxEquality(size, [task_requirements(tasks[i], allowances).required_minutes * member
                                    for i, member in members.items()])
        model.Add(end == start + size)
        model.Add(start == 0).OnlyEnforceIf(present.Not())
        interval = model.NewOptionalIntervalVar(start, size, end, present, f"block_{anchor}_interval")
        capacity_resources = tuple(task.get("_capacity_resource_ids", (task["section_id"],)))
        section_ids = tuple(task.get("_section_ids", (task["section_id"],)))
        for capacity_resource_id in capacity_resources:
            capacity_intervals.setdefault(capacity_resource_id, []).append(interval)
        blocks.append(dict(start=start, end=end, size=size, present=present,
                           section_id=task["section_id"], section_ids=section_ids,
                           capacity_resource_ids=capacity_resources,
                           footprint_id=task.get("_footprint_id", task["section_id"]),
                           members=members))
    for i, task in enumerate(tasks):
        model.Add(sum(assignments[i]) == variables[task["task_id"]]["scheduled"])
    for intervals in capacity_intervals.values():
        model.AddNoOverlap(intervals)
    return blocks


def _make_stage_solver(template, remaining_seconds, solver_factory):
    if solver_factory is not None:
        return solver_factory(template, remaining_seconds)
    stage_solver = cp_model.CpSolver()
    stage_solver.parameters.copy_from(template.parameters)
    if remaining_seconds is not None:
        stage_solver.parameters.max_time_in_seconds = max(remaining_seconds, 1e-9)
    return stage_solver


def _not_run(stage, reason, elapsed):
    return dict(
        stage=stage,
        objective=stage,
        status="NOT_RUN",
        solver_status=None,
        termination_reason=reason,
        elapsed_seconds=0.0,
        runtime_seconds=0.0,
        cumulative_elapsed_seconds=elapsed,
        remaining_seconds_before_stage=None,
        objective_value=None,
    )


def solve_priorities(
    model,
    solver,
    tasks,
    variables,
    blocks,
    facts,
    slack_objectives,
    *,
    deadline=None,
    clock=perf_counter,
    solver_factory=None,
    stability_stages=(),
    risk_stages=(),
):
    """Solve stages within one deadline and retain the last usable incumbent."""
    stages = []
    for field in ("criticality", "urgency", "overdue_days"):
        weights = []
        for task in tasks:
            value = task.get(field, 0)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer.")
            weights.append(value * variables[task["task_id"]]["scheduled"])
        stages.append((field, True, sum(weights)))
    stages += [
        ("task_count", True, sum(v["scheduled"] for v in variables.values())),
        *stability_stages,
        ("possession_minutes", False, sum(b["size"] for b in blocks)),
        ("block_count", False, sum(b["present"] for b in blocks)),
        *risk_stages,
        ("minimum_boundary_slack_minutes", True, slack_objectives[0]),
        ("total_boundary_slack_minutes", True, slack_objectives[1]),
        ("start_minutes", False, sum(v["start"] for v in variables.values())),
    ]
    run_started = clock()
    last_solver = None
    last_status = cp_model.UNKNOWN
    solution_stage = None
    last_stage_reached = None
    for index, (name, maximize, expression) in enumerate(stages):
        now = clock()
        remaining = None if deadline is None else deadline - now
        if remaining is not None and remaining <= 0:
            elapsed = now - run_started
            facts.extend(
                _not_run(stage, "TIME_LIMIT", elapsed)
                for stage, _, _ in stages[index:]
            )
            return LexicographicSolveResult(
                last_status,
                last_solver,
                PlanProofState.FEASIBLE_BOUNDED if last_solver else PlanProofState.NO_SOLUTION,
                last_stage_reached,
                solution_stage,
            )
        if maximize:
            model.Maximize(expression)
        else:
            model.Minimize(expression)
        stage_solver = _make_stage_solver(solver, remaining, solver_factory)
        last_stage_reached = name
        started = clock()
        status = stage_solver.Solve(model)
        finished = clock()
        status_name = stage_solver.StatusName(status)
        has_solution = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        objective_value = stage_solver.Value(expression) if has_solution else None
        termination = (
            "PROVEN_OPTIMAL"
            if status == cp_model.OPTIMAL
            else "TIME_LIMIT"
            if deadline is not None and status in (cp_model.FEASIBLE, cp_model.UNKNOWN)
            else status_name
        )
        diagnostic = dict(
            stage=name,
            objective=name,  # Compatibility with existing internal diagnostics.
            status=status_name,
            solver_status=status_name,
            termination_reason=termination,
            elapsed_seconds=finished - started,
            runtime_seconds=finished - started,
            cumulative_elapsed_seconds=finished - run_started,
            remaining_seconds_before_stage=remaining,
            objective_value=objective_value,
        )
        facts.append(diagnostic)
        if has_solution:
            last_solver = stage_solver
            last_status = status
            solution_stage = name
        if status == cp_model.OPTIMAL:
            diagnostic["optimum"] = objective_value
            model.Add(expression == objective_value)
            continue

        # Never fix an unproven value or run a lower-priority objective.
        facts.extend(
            _not_run(stage, "HIGHER_STAGE_UNPROVEN", finished - run_started)
            for stage, _, _ in stages[index + 1 :]
        )
        if last_solver is not None:
            return LexicographicSolveResult(
                last_status,
                last_solver,
                PlanProofState.FEASIBLE_BOUNDED,
                last_stage_reached,
                solution_stage,
            )
        return LexicographicSolveResult(
            status,
            None,
            PlanProofState.INFEASIBLE
            if status == cp_model.INFEASIBLE
            else PlanProofState.NO_SOLUTION,
            name,
            None,
        )
    return LexicographicSolveResult(
        cp_model.OPTIMAL,
        last_solver,
        PlanProofState.FULLY_OPTIMAL,
        last_stage_reached,
        solution_stage,
    )
