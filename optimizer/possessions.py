"""Solver-level synchronized possessions and exact lexicographic objectives."""

from itertools import combinations

from ortools.sat.python import cp_model

try:
    from .compatibility import evaluate_compatibility
    from .feasibility import task_requirements
except ImportError:
    from compatibility import evaluate_compatibility
    from feasibility import task_requirements


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
    section_intervals = {}
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
        section_intervals.setdefault(task["section_id"], []).append(interval)
        blocks.append(dict(start=start, end=end, size=size, present=present,
                           section_id=task["section_id"], members=members))
    for i, task in enumerate(tasks):
        model.Add(sum(assignments[i]) == variables[task["task_id"]]["scheduled"])
    for intervals in section_intervals.values():
        model.AddNoOverlap(intervals)
    return blocks


def solve_priorities(model, solver, tasks, variables, blocks, facts):
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
        ("possession_minutes", False, sum(b["size"] for b in blocks)),
        ("block_count", False, sum(b["present"] for b in blocks)),
        ("start_minutes", False, sum(v["start"] for v in variables.values())),
    ]
    for name, maximize, expression in stages:
        if maximize:
            model.Maximize(expression)
        else:
            model.Minimize(expression)
        status = solver.Solve(model)
        facts.append(dict(objective=name, status=solver.StatusName(status)))
        # Never fix an unproven incumbent as an optimum or proceed to lower stages.
        if status != cp_model.OPTIMAL:
            return status
        optimum = solver.Value(expression)
        facts[-1]["optimum"] = optimum
        model.Add(expression == optimum)
    return status
