"""Plan validation, deterministic train disruption, stability-aware recovery."""
from copy import deepcopy
from datetime import timedelta
try:
    from .optimizer import optimize_schedule, validate_solution
    from .candidate_windows import generate_candidate_windows, OperationalAllowances
    from .feasibility import evaluate_task_in_window, task_requirements
    from .resources import validate_capacities
    from .time_utils import parse_datetime, datetime_to_minutes
except ImportError:
    from optimizer import optimize_schedule, validate_solution
    from candidate_windows import generate_candidate_windows, OperationalAllowances
    from feasibility import evaluate_task_in_window, task_requirements
    from resources import validate_capacities
    from time_utils import parse_datetime, datetime_to_minutes


def apply_train_delay(data, train_id, delay_minutes):
    if isinstance(delay_minutes, bool) or not isinstance(delay_minutes, int) or not 0 <= delay_minutes <= 1440:
        raise ValueError("delay_minutes must be an integer between 0 and 1440")
    changed = deepcopy(data)
    affected = [r for r in changed["train_occupancy"] if r["train_id"] == train_id]
    if not affected:
        raise ValueError(f"Unknown train ID: {train_id}")
    for row in affected:
        for key in ("entry_time", "exit_time"):
            row[key] = (parse_datetime(row[key]) + timedelta(minutes=delay_minutes)).isoformat()
    return changed


def validate_current_plan(data, blocks, start, end, resources=None, allowances=OperationalAllowances()):
    ids = [b["block_id"] for b in blocks]
    if len(ids) != len(set(ids)):
        raise ValueError("Current plan has duplicate block IDs")
    tasks = data["maintenance_tasks"]
    validate_solution(blocks, tasks, data["train_occupancy"], start, end, allowances=allowances)
    windows = generate_candidate_windows(data["train_occupancy"], {t["section_id"] for t in tasks}, start, end, allowances)
    by_id = {t["task_id"]:t for t in tasks}
    reservations = []
    for block in blocks:
        for task_id in block["tasks"]:
            task = by_id[task_id]
            if not any(evaluate_task_in_window(task, window, allowances=allowances,
                reservation_start=block["start_time"], resource_context=resources).feasible for window in windows if window.section_id == block["section_id"]):
                raise ValueError(f"Current plan reservation fails hard feasibility: {task_id}")
            minutes = datetime_to_minutes(block["start_time"], start)
            reservations.append((task, minutes, minutes+task_requirements(task, allowances).required_minutes))
    validate_capacities(reservations, resources)


def plan_changes(before, after):
    def key(block):
        return (block["section_id"], tuple(sorted(block["tasks"])))
    old = {key(b):b for b in before}
    new = {key(b):b for b in after}
    block_changes = []
    for signature in sorted(old.keys() | new.keys()):
        a, b = old.get(signature), new.get(signature)
        shift = abs(datetime_to_minutes(b["start_time"], a["start_time"])) if a and b else None
        state = "NEW" if a is None else "CANCELLED" if b is None else "RETAINED" if shift == 0 and datetime_to_minutes(b["end_time"], a["end_time"]) == 0 else "SHIFTED"
        block_changes.append(dict(state=state, section_id=signature[0], task_ids=list(signature[1]),
                                  before_block_id=a["block_id"] if a else None,
                                  after_block_id=b["block_id"] if b else None, shift_minutes=shift))
    old_tasks = {t:b for b in before for t in b["tasks"]}
    new_tasks = {t:b for b in after for t in b["tasks"]}
    task_changes = []
    for task_id in sorted(old_tasks.keys() | new_tasks.keys()):
        a, b = old_tasks.get(task_id), new_tasks.get(task_id)
        shift = abs(datetime_to_minutes(b["start_time"],a["start_time"])) if a and b else None
        state = "NEW" if a is None else "UNSCHEDULED" if b is None else "RETAINED" if shift == 0 else "SHIFTED"
        task_changes.append(dict(task_id=task_id, state=state, shift_minutes=shift,
                                 regrouped=bool(a and b and key(a) != key(b))))
    metrics = {f"{name.lower()}_blocks":sum(c["state"] == name for c in block_changes) for name in ("RETAINED","SHIFTED","CANCELLED","NEW")}
    metrics.update({f"{name.lower()}_tasks":sum(c["state"] == name for c in task_changes) for name in ("RETAINED","SHIFTED","NEW")})
    metrics["total_shift_minutes"] = sum(c["shift_minutes"] or 0 for c in task_changes)
    metrics["total_block_shift_minutes"] = sum(c["shift_minutes"] or 0 for c in block_changes)
    return dict(metrics=metrics, block_changes=block_changes, task_changes=task_changes,
                newly_unscheduled_task_ids=sorted(old_tasks.keys()-new_tasks.keys()))


def recover_schedule(data, current_blocks, disruption, start, end, *, resource_context=None,
                     allowances=OperationalAllowances(), time_limit_seconds=None, risk_penalties=None):
    validate_current_plan(data, current_blocks, start, end, resource_context, allowances)
    if disruption.get("type") != "TRAIN_DELAY":
        raise ValueError("Only TRAIN_DELAY is supported")
    changed = apply_train_delay(data, disruption["train_id"], disruption["delay_minutes"])
    invalidated = []
    for block in current_blocks:
        try:
            validate_current_plan(changed, [block], start, end, resource_context, allowances)
        except ValueError as error:
            invalidated.append(dict(block_id=block["block_id"], task_ids=block["tasks"],
                                    reason_code="DISRUPTED_TRAIN_PROTECTION", detail=str(error)))
    facts = {}
    plan = optimize_schedule(changed, start, end, resource_context=resource_context,
                             allowances=allowances, time_limit_seconds=time_limit_seconds,
                             previous_blocks=current_blocks, risk_penalties=risk_penalties, diagnostics=facts)
    if plan["status"] != "success":
        raise RuntimeError(f"Recovery has no usable incumbent: {plan['status']}")
    changes = plan_changes(current_blocks, plan["blocks"])
    changes["metrics"]["unscheduled_tasks_after_disruption"] = len(plan["unscheduled_tasks"])
    return dict(plan=plan, diagnostics=facts, changes=changes, invalidated_blocks=invalidated,
                train_occupancy=changed["train_occupancy"],
                affected_sections=sorted({r["section_id"] for r in data["train_occupancy"] if r["train_id"] == disruption["train_id"]}))
