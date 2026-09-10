"""Plan validation and time-aware stability-first disruption recovery."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
try:
    from .optimizer import optimize_schedule, validate_solution
    from .candidate_windows import generate_footprint_windows, OperationalAllowances
    from .capacity import normalize_tasks
    from .feasibility import evaluate_task_in_window, task_requirements
    from .resources import validate_capacities
    from .time_utils import parse_datetime, datetime_to_minutes
except ImportError:
    from optimizer import optimize_schedule, validate_solution
    from candidate_windows import generate_footprint_windows, OperationalAllowances
    from capacity import normalize_tasks
    from feasibility import evaluate_task_in_window, task_requirements
    from resources import validate_capacities
    from time_utils import parse_datetime, datetime_to_minutes


def apply_train_delay(data, train_id, delay_minutes, effective_time=None):
    if isinstance(delay_minutes, bool) or not isinstance(delay_minutes, int) or not 0 <= delay_minutes <= 1440:
        raise ValueError("delay_minutes must be an integer between 0 and 1440")
    changed = deepcopy(data)
    affected = [r for r in changed["train_occupancy"] if r["train_id"] == train_id]
    if not affected:
        raise ValueError(f"Unknown train ID: {train_id}")
    for row in affected:
        if effective_time and parse_datetime(row["exit_time"]) <= parse_datetime(effective_time):
            continue
        for key in ("entry_time", "exit_time"):
            row[key] = (parse_datetime(row[key]) + timedelta(minutes=delay_minutes)).isoformat()
    return changed


def validate_current_plan(data, blocks, start, end, resources=None, allowances=OperationalAllowances()):
    ids = [b["block_id"] for b in blocks]
    if len(ids) != len(set(ids)):
        raise ValueError("Current plan has duplicate block IDs")
    tasks = data["maintenance_tasks"]
    sections = data.get("sections", [])
    normalized = normalize_tasks(tasks, sections)
    validate_solution(blocks, normalized, data["train_occupancy"], start, end, allowances=allowances, sections=sections)
    windows = generate_footprint_windows(
        data["train_occupancy"],
        ({"section_id": t["section_id"], "section_ids": t["_section_ids"], "capacity_resource_ids": t["_capacity_resource_ids"]} for t in normalized),
        sections, start, end, allowances,
    )
    by_id = {t["task_id"]:t for t in normalized}
    reservations = []
    for block in blocks:
        for task_id in block["tasks"]:
            task = by_id[task_id]
            if not any(evaluate_task_in_window(task, window, allowances=allowances,
                reservation_start=block["start_time"], resource_context=resources).feasible
                for window in windows if window.footprint_id == task["_footprint_id"]):
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


def apply_disruption(data, resource_context, disruption, start, end):
    """Apply one validated scenario to a copy; return inputs and affected sections."""
    changed = deepcopy(data)
    context = resource_context
    kind = disruption.get("type")
    effective = disruption.get("effective_time") or start
    affected_sections = set()
    if kind in {"TRAIN_DELAY", "TRAIN_DELAYS"}:
        delays = [disruption] if kind == "TRAIN_DELAY" else disruption.get("delays", [])
        if not delays:
            raise ValueError("TRAIN_DELAYS requires at least one delay.")
        for item in delays:
            original = changed
            changed = apply_train_delay(
                original, item["train_id"], item["delay_minutes"], effective
            )
            affected_sections.update(
                row["section_id"] for row in original["train_occupancy"]
                if row["train_id"] == item["train_id"]
            )
    elif kind == "CREW_UNAVAILABLE":
        if context is None or disruption["crew_type"] not in context.crew_capacities:
            raise ValueError(f"Unknown crew pool: {disruption['crew_type']}")
        capacities = dict(context.crew_capacities)
        capacities[disruption["crew_type"]] = 0
        context = replace(context, crew_capacities=capacities)
    elif kind == "MACHINE_UNAVAILABLE":
        if context is None or disruption["machine_type"] not in context.machine_capacities:
            raise ValueError(f"Unknown machine pool: {disruption['machine_type']}")
        capacities = dict(context.machine_capacities)
        capacities[disruption["machine_type"]] = 0
        context = replace(context, machine_capacities=capacities)
    elif kind == "POWER_ISOLATION_CANCELLED":
        section_ids = disruption["section_ids"]
        if context is None or any(item not in context.power_windows for item in section_ids):
            raise ValueError("Power cancellation references an unknown section.")
        power = dict(context.power_windows)
        for section_id in section_ids:
            power[section_id] = ()
        context = replace(context, power_windows=power)
        affected_sections.update(section_ids)
    elif kind == "SECTION_UNAVAILABLE":
        section_id = disruption["section_id"]
        if section_id not in {row["section_id"] for row in changed.get("sections", [])}:
            raise ValueError(f"Unknown section ID: {section_id}")
        row = {
            "train_id": f"SECTION_CLOSURE_{section_id}",
            "section_id": section_id,
            "entry_time": disruption.get("start_time", effective),
            "exit_time": disruption.get("end_time", end),
            "traffic_type": "SYNTHETIC_DISRUPTION",
        }
        if disruption.get("capacity_resource_ids"):
            row["capacity_resource_ids"] = disruption["capacity_resource_ids"]
        changed["train_occupancy"].append(row)
        affected_sections.add(section_id)
    elif kind == "EMERGENCY_WORK":
        task = deepcopy(disruption["task"])
        if task["task_id"] in {row["task_id"] for row in changed["maintenance_tasks"]}:
            raise ValueError(f"Duplicate emergency task ID: {task['task_id']}")
        changed["maintenance_tasks"].append(task)
        affected_sections.update(task.get("section_ids") or [task["section_id"]])
    elif kind == "WEATHER_RESTRICTION":
        delay = disruption["delay_minutes"]
        train_ids = disruption.get("train_ids") or sorted({r["train_id"] for r in changed["train_occupancy"]})
        for train_id in train_ids:
            original = changed
            changed = apply_train_delay(changed, train_id, delay, effective)
            affected_sections.update(r["section_id"] for r in original["train_occupancy"] if r["train_id"] == train_id)
    else:
        raise ValueError(f"Unsupported disruption type: {kind}")
    return changed, context, sorted(affected_sections)


def recover_schedule(data, current_blocks, disruption, start, end, *, resource_context=None,
                     allowances=OperationalAllowances(), time_limit_seconds=None, risk_penalties=None):
    validate_current_plan(data, current_blocks, start, end, resource_context, allowances)
    changed, changed_resources, affected_sections = apply_disruption(
        data, resource_context, disruption, start, end
    )
    effective = parse_datetime(disruption.get("effective_time") or start)
    fixed_task_starts = {
        task_id: block["start_time"]
        for block in current_blocks
        if block.get("status") in {"COMPLETED", "IN_PROGRESS", "FROZEN"}
        or parse_datetime(block["start_time"]) < effective
        for task_id in block["tasks"]
    }
    invalidated = []
    for block in current_blocks:
        try:
            validate_current_plan(changed, [block], start, end, changed_resources, allowances)
        except ValueError as error:
            invalidated.append(dict(block_id=block["block_id"], task_ids=block["tasks"],
                                    reason_code="DISRUPTED_TRAIN_PROTECTION", detail=str(error)))
    facts = {}
    plan = optimize_schedule(changed, start, end, resource_context=changed_resources,
                             allowances=allowances, time_limit_seconds=time_limit_seconds,
                             previous_blocks=current_blocks, fixed_task_starts=fixed_task_starts,
                             risk_penalties=risk_penalties, diagnostics=facts)
    if plan["status"] != "success":
        raise RuntimeError(f"Recovery has no usable incumbent: {plan['status']}")
    changes = plan_changes(current_blocks, plan["blocks"])
    changes["metrics"]["unscheduled_tasks_after_disruption"] = len(plan["unscheduled_tasks"])
    return dict(plan=plan, diagnostics=facts, changes=changes, invalidated_blocks=invalidated,
                train_occupancy=changed["train_occupancy"],
                maintenance_tasks=changed["maintenance_tasks"],
                affected_sections=affected_sections,
                immutable_task_ids=sorted(fixed_task_starts),
                escalation_required=any(item["block_id"] in {
                    block["block_id"] for block in current_blocks
                    if any(task in fixed_task_starts for task in block["tasks"])
                } for item in invalidated))
