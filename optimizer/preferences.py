"""Optional preferences only: no relaxation or replacement of hard constraints."""
import math
try:
    from .time_utils import datetime_to_minutes, parse_datetime
except ImportError:
    from time_utils import datetime_to_minutes, parse_datetime


def _and(model, literals, name):
    flag = model.NewBoolVar(name)
    model.AddBoolAnd(literals).OnlyEnforceIf(flag)
    model.AddBoolOr([literal.Not() for literal in literals]).OnlyEnforceIf(flag.Not())
    return flag


def stability_objectives(model, tasks, variables, possessions, previous_blocks, origin, horizon):
    if previous_blocks is None:
        return []
    indexes = {task["task_id"]: i for i,task in enumerate(tasks)}
    old_tasks = {task_id: block for block in previous_blocks for task_id in block["tasks"]}
    if set(old_tasks) - indexes.keys():
        raise ValueError("Previous plan has unknown tasks")
    intact, unchanged, same_starts, shifts = [], [], [], []
    for number, old in enumerate(previous_blocks):
        members = {indexes[t] for t in old["tasks"]}
        anchor = possessions[min(members)]
        if not members.issubset(anchor["members"]):
            continue
        match = _and(model, [v if i in members else v.Not() for i,v in anchor["members"].items()], f"old_{number}_membership")
        intact.append(match)
        start = datetime_to_minutes(old["start_time"], origin)
        equal = model.NewBoolVar(f"old_{number}_same_time")
        model.Add(anchor["start"] == start).OnlyEnforceIf(equal)
        model.Add(anchor["start"] != start).OnlyEnforceIf(equal.Not())
        unchanged.append(_and(model, [match, equal], f"old_{number}_unchanged"))
    for task_id, old in old_tasks.items():
        var = variables[task_id]
        old_start = datetime_to_minutes(old["start_time"], origin)
        if not 0 <= old_start <= horizon:
            raise ValueError("Previous plan is outside the horizon")
        equal = model.NewBoolVar(f"same_start_{task_id}")
        model.Add(var["start"] == old_start).OnlyEnforceIf(equal)
        model.Add(var["start"] != old_start).OnlyEnforceIf(equal.Not())
        same_starts.append(_and(model, [var["scheduled"], equal], f"retained_{task_id}"))
        absolute = model.NewIntVar(0, horizon, f"absolute_shift_{task_id}")
        model.AddAbsEquality(absolute, var["start"] - old_start)
        displacement = model.NewIntVar(0, horizon, f"shift_{task_id}")
        model.Add(displacement == absolute).OnlyEnforceIf(var["scheduled"])
        model.Add(displacement == 0).OnlyEnforceIf(var["scheduled"].Not())
        shifts.append(displacement)
    return [("previous_tasks_scheduled", True, sum(variables[t]["scheduled"] for t in old_tasks)),
            ("intact_previous_possessions", True, sum(intact)),
            ("unchanged_previous_possessions", True, sum(unchanged)),
            ("unchanged_task_starts", True, sum(same_starts)),
            ("task_displacement_minutes", False, sum(shifts))]


def risk_objectives(model, blocks, windows_by_section, occupancy, penalties, horizon):
    if not penalties:
        return []
    pairs = {(r["train_id"],r["section_id"]) for r in occupancy}
    for key, value in penalties.items():
        if key not in pairs or isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value) or value < 0 or value > 10080:
            raise ValueError("Risk requires known train/section and finite nonnegative delay <= 10080 minutes")
    maximum = math.ceil(max(penalties.values()))
    effective, reserves = [], []
    for index, block in enumerate(blocks):
        before = model.NewIntVar(-maximum, horizon, f"risk_before_{index}")
        after = model.NewIntVar(-maximum, horizon, f"risk_after_{index}")
        for window, chosen in block["slack_choices"]:
            previous = max((math.ceil(penalties.get((r["train_id"],r["section_id"]),0)) for r in occupancy
                            if r["section_id"] == window.section_id and window.margin_before_minutes > 0
                            and parse_datetime(r["exit_time"]) == parse_datetime(window.nominal_start)), default=0)
            following = max((math.ceil(penalties.get((r["train_id"],r["section_id"]),0)) for r in occupancy
                             if r["section_id"] == window.section_id and window.margin_after_minutes > 0
                             and parse_datetime(r["entry_time"]) == parse_datetime(window.nominal_end)), default=0)
            model.Add(before == block["before_slack"] - previous).OnlyEnforceIf(chosen)
            model.Add(after == block["after_slack"] - following).OnlyEnforceIf(chosen)
        model.Add(before == 0).OnlyEnforceIf(block["present"].Not())
        model.Add(after == 0).OnlyEnforceIf(block["present"].Not())
        reserve = model.NewIntVar(-maximum, horizon, f"risk_reserve_{index}")
        model.AddMinEquality(reserve, [before, after])
        reserves.append(reserve)
        item = model.NewIntVar(-maximum, horizon, f"risk_effective_{index}")
        model.Add(item == reserve).OnlyEnforceIf(block["present"])
        model.Add(item == horizon).OnlyEnforceIf(block["present"].Not())
        effective.append(item)
    if not effective:
        return []
    active = model.NewBoolVar("risk_has_blocks")
    model.AddMaxEquality(active, [b["present"] for b in blocks])
    raw = model.NewIntVar(-maximum, horizon, "risk_raw_min")
    model.AddMinEquality(raw, effective)
    minimum = model.NewIntVar(-maximum, horizon, "risk_min")
    model.Add(minimum == raw).OnlyEnforceIf(active)
    model.Add(minimum == 0).OnlyEnforceIf(active.Not())
    return [("minimum_risk_adjusted_reserve", True, minimum), ("total_risk_adjusted_reserve", True, sum(reserves))]
