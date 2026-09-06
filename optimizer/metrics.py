"""Internal service/possession measures; public contract fields stay unchanged."""

try:
    from .candidate_windows import OperationalAllowances
    from .feasibility import task_requirements
    from .time_utils import datetime_to_minutes
    from .robustness import measure_boundary_slack
except ImportError:
    from candidate_windows import OperationalAllowances
    from feasibility import task_requirements
    from time_utils import datetime_to_minutes
    from robustness import measure_boundary_slack


def summarize_plan(tasks, blocks, windows, allowances=OperationalAllowances()):
    """Input blocks must be validated, disjoint possessions per section."""
    by_id = {t["task_id"]: t for t in tasks}
    scheduled = {task_id for b in blocks for task_id in b["tasks"]}
    productive = sum(by_id[t]["duration_minutes"] for t in scheduled)
    possession = sum(datetime_to_minutes(b["end_time"], b["start_time"]) for b in blocks)
    slacks = [measure_boundary_slack(b, windows) for b in blocks]
    # Sum once per shared possession; same-department sharing is included and
    # remains distinct from the cross-department integrated_blocks count.
    coordination_gain = sum(
        sum(task_requirements(by_id[t], allowances).required_minutes for t in b["tasks"])
        - datetime_to_minutes(b["end_time"], b["start_time"])
        for b in blocks if len(b["tasks"]) > 1
    )
    return dict(
        scheduled_tasks=sorted(scheduled), unscheduled_tasks=sorted(set(by_id) - scheduled),
        scheduled_task_count=len(scheduled), productive_minutes=productive,
        criticality_served=sum(by_id[t].get("criticality", 0) for t in scheduled),
        urgency_served=sum(by_id[t].get("urgency", 0) for t in scheduled),
        overdue_days_served=sum(by_id[t].get("overdue_days", 0) for t in scheduled),
        possession_minutes=possession, block_count=len(blocks),
        integrated_blocks=sum(bool(b["integrated"]) for b in blocks),
        maintenance_delivery_efficiency=productive / possession if possession else None,
        coordination_gain_minutes=coordination_gain, boundary_slacks=slacks,
        minimum_boundary_slack_minutes=min((s["boundary_slack_minutes"] for s in slacks), default=0),
        total_boundary_slack_minutes=sum(s["boundary_slack_minutes"] for s in slacks),
    )


def compare_service(baseline, optimized):
    same = set(baseline["scheduled_tasks"]) == set(optimized["scheduled_tasks"])
    saved = baseline["possession_minutes"] - optimized["possession_minutes"] if same else None
    return dict(
        same_task_set=same, closure_saved_minutes=saved,
        closure_reduction_percent=(saved / baseline["possession_minutes"] * 100
                                   if same and baseline["possession_minutes"] > 0 else None),
        maintenance_delivery_efficiency_baseline=baseline["maintenance_delivery_efficiency"],
        maintenance_delivery_efficiency_optimized=optimized["maintenance_delivery_efficiency"],
        coordination_gain_minutes=optimized["coordination_gain_minutes"],
    )
