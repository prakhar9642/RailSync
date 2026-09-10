"""Application service boundary for registered-territory planning."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from data import LoadedTerritory, load_territory
from ml.inference import planning_risk
from optimizer.candidate_windows import OperationalAllowances
from optimizer.comparison import compare_plans
from optimizer.feasibility import task_requirements
from optimizer.runtime import DEMO_SOLVE_LIMIT_SECONDS
from .operations_service import register_plan

DEFAULT_TERRITORY_ID = "saktigarh_memari_public_demo"
BASELINE_LABEL = "NON_INTEGRATED_CP_SAT_COMPARISON"
SUPPORTED_PROFILE = "Availability First"
DEMO_ALLOWANCES = OperationalAllowances()


class InvalidPlanningRequest(ValueError):
    """The selected registered data cannot support the requested plan."""


class PlanningExecutionError(RuntimeError):
    """The solver did not return a usable comparison plan."""


def _horizon(territory: LoadedTerritory) -> tuple[str, str, float]:
    horizon = territory.manifest.planning_horizon
    if horizon is None:
        raise InvalidPlanningRequest(
            f"Territory {territory.manifest.territory_id!r} has no configured planning horizon."
        )
    start_time, end_time = horizon["start_time"], horizon["end_time"]
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        duration_hours = (end - start).total_seconds() / 3600
    except (TypeError, ValueError) as error:
        raise InvalidPlanningRequest("Configured planning horizon is invalid.") from error
    if duration_hours <= 0:
        raise InvalidPlanningRequest("Configured planning horizon must have positive duration.")
    return start_time, end_time, duration_hours


def _validate_resource_coverage(territory: LoadedTerritory) -> None:
    context = territory.resource_context
    if context is None:
        raise InvalidPlanningRequest(
            f"Territory {territory.manifest.territory_id!r} has no configured resource context."
        )

    required_crews = {task.get("crew_type") for task in territory.maintenance_tasks}
    required_machines = {task.get("machine_type") for task in territory.maintenance_tasks}
    required_power_sections = {
        section_id
        for task in territory.maintenance_tasks
        if task.get("requires_power_block") or task.get("requires_power_isolation")
        for section_id in task.get("section_ids", [task["section_id"]])
    }
    missing_crews = sorted(
        item for item in required_crews if item and item not in context.crew_capacities
    )
    missing_machines = sorted(
        item for item in required_machines if item and item not in context.machine_capacities
    )
    missing_power = sorted(required_power_sections - context.power_windows.keys())
    missing = missing_crews + missing_machines + missing_power
    if missing:
        raise InvalidPlanningRequest(
            "Configured resource context does not cover required resources: "
            + ", ".join(missing)
            + "."
        )


def load_planning_territory(territory_id: str) -> LoadedTerritory:
    """Load registered data without substituting a mock or fallback territory."""
    return load_territory(territory_id)


def _hours(minutes: int) -> float:
    return round(minutes / 60, 3)


def _duration_minutes(block: dict[str, Any]) -> int:
    start = datetime.fromisoformat(block["start_time"])
    end = datetime.fromisoformat(block["end_time"])
    return int((end - start).total_seconds() // 60)


def _analysis_plan(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "blocks": result["plan"]["blocks"],
        "scheduled_task_ids": result["scheduled_tasks"],
        "unscheduled_task_ids": result["unscheduled_tasks"],
        "proof_state": result["proof_state"],
        "metrics": {
            "scheduled_task_count": result["scheduled_task_count"],
            "unscheduled_task_count": len(result["unscheduled_tasks"]),
            "productive_minutes": result["productive_minutes"],
            "possession_minutes": result["possession_minutes"],
            "block_count": result["block_count"],
            "integrated_blocks": result["integrated_blocks"],
            "criticality_served": result["criticality_served"],
            "urgency_served": result["urgency_served"],
            "overdue_days_served": result["overdue_days_served"],
            "maintenance_delivery_efficiency": result[
                "maintenance_delivery_efficiency"
            ],
            "minimum_boundary_slack_minutes": result[
                "minimum_boundary_slack_minutes"
            ],
            "total_boundary_slack_minutes": result[
                "total_boundary_slack_minutes"
            ],
        },
    }


def _task_summary(
    task: dict[str, Any],
    resource_checks: dict[str, str],
    *,
    scheduled: bool,
) -> dict[str, Any]:
    requirement = task_requirements(task, DEMO_ALLOWANCES)
    return {
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        "department": task["department"],
        "section_id": task["section_id"],
        "criticality": task["criticality"],
        "urgency": task["urgency"],
        "overdue_days": task["overdue_days"],
        "crew_type": requirement.crew_type,
        "machine_type": requirement.machine_type,
        "requires_power_block": requirement.requires_power_isolation,
        "reservation_minutes": requirement.required_minutes,
        "deadline_check": (
            "PASSED" if scheduled and task.get("deadline") else "NOT_EVALUATED"
        ),
        "resource_checks": resource_checks,
    }


def _block_diagnostics(
    tasks: list[dict[str, Any]], result: dict[str, Any]
) -> list[dict[str, Any]]:
    task_by_id = {task["task_id"]: task for task in tasks}
    slack_by_block = {
        item["block_id"]: item for item in result["boundary_slacks"]
    }
    diagnostics = []
    for block in result["plan"]["blocks"]:
        slack = slack_by_block.get(block["block_id"])
        window_id = slack.get("window_id") if slack else None
        member_ids = set(block["tasks"])
        pair_facts = [
            fact
            for fact in result["pair_checks"]
            if set(fact["tasks"]).issubset(member_ids)
        ]
        task_details = []
        for task_id in block["tasks"]:
            window_fact = next(
                (
                    fact
                    for fact in result["task_windows"]
                    if fact["task_id"] == task_id
                    and fact["window_id"] == window_id
                ),
                None,
            )
            task_details.append(
                _task_summary(
                    task_by_id[task_id],
                    window_fact["resource_checks"] if window_fact else {},
                    scheduled=True,
                )
            )
        compatibility_statuses = sorted({fact["status"] for fact in pair_facts})
        diagnostics.append(
            {
                "block_id": block["block_id"],
                "section_id": block["section_id"],
                "window_id": window_id,
                "feasibility": {
                    "section_match": "PASSED",
                    "duration_fit": "PASSED",
                    "train_conflict": "PASSED",
                    "candidate_window": "PASSED",
                },
                "integration": {
                    "integrated": block["integrated"],
                    "sharing_status": (
                        "SHARED" if len(block["tasks"]) > 1 else "INDIVIDUAL"
                    ),
                    "compatibility_status": (
                        compatibility_statuses[0]
                        if len(compatibility_statuses) == 1
                        else "MIXED"
                        if compatibility_statuses
                        else "NOT_EVALUATED"
                    ),
                    "reason_codes": sorted(
                        {reason for fact in pair_facts for reason in fact["reasons"]}
                    ),
                },
                "robustness": (
                    {
                        "before_boundary_slack_minutes": slack[
                            "before_boundary_slack_minutes"
                        ],
                        "after_boundary_slack_minutes": slack[
                            "after_boundary_slack_minutes"
                        ],
                        "minimum_boundary_slack_minutes": slack[
                            "boundary_slack_minutes"
                        ],
                    }
                    if slack
                    else None
                ),
                "tasks": task_details,
            }
        )
    return diagnostics


def _integrated_gains(
    tasks: list[dict[str, Any]], blocks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    task_by_id = {task["task_id"]: task for task in tasks}
    gains = []
    for block in blocks:
        if not block["integrated"]:
            continue
        task_ids = block["tasks"]
        individual_minutes = sum(
            task_requirements(task_by_id[task_id], DEMO_ALLOWANCES).required_minutes
            for task_id in task_ids
        )
        shared_minutes = _duration_minutes(block)
        gains.append(
            {
                "block_id": block["block_id"],
                "section_id": block["section_id"],
                "task_ids": task_ids,
                "departments": sorted(
                    {task_by_id[task_id]["department"] for task_id in task_ids}
                ),
                "individual_reservation_minutes": individual_minutes,
                "shared_possession_minutes": shared_minutes,
                "coordination_gain_minutes": individual_minutes - shared_minutes,
            }
        )
    return gains


def _unscheduled_diagnostics(
    tasks: list[dict[str, Any]], result: dict[str, Any]
) -> list[dict[str, Any]]:
    task_by_id = {task["task_id"]: task for task in tasks}
    details = []
    for task_id in result["unscheduled_tasks"]:
        window_facts = [
            fact for fact in result["task_windows"] if fact["task_id"] == task_id
        ]
        details.append(
            {
                "task": _task_summary(task_by_id[task_id], {}, scheduled=False),
                "outcome": result["outcomes"].get(task_id, "UNKNOWN"),
                "reason_codes": sorted(
                    {reason for fact in window_facts for reason in fact["reasons"]}
                ),
                "candidate_windows": window_facts,
            }
        )
    return details


def _analysis(
    territory: LoadedTerritory, compared: dict[str, Any]
) -> dict[str, Any]:
    baseline = compared["baseline"]
    optimized = compared["optimized"]
    comparison = compared["comparison"]
    same_task_set = comparison["same_task_set"]
    return {
        "fairness": {
            "baseline_label": BASELINE_LABEL,
            "same_task_set": same_task_set,
            "possession_saved_minutes": (
                comparison["closure_saved_minutes"] if same_task_set else None
            ),
            "possession_reduction_percent": (
                comparison["closure_reduction_percent"] if same_task_set else None
            ),
            "statement": (
                "Both planners delivered the same maintenance task set; possession "
                "use is directly comparable."
                if same_task_set
                else "Pure possession savings are not reported because the planners "
                "delivered different maintenance task sets."
            ),
        },
        "baseline": _analysis_plan(baseline),
        "railsync": _analysis_plan(optimized),
        "integrated_blocks": _integrated_gains(
            territory.maintenance_tasks, optimized["plan"]["blocks"]
        ),
        "block_diagnostics": _block_diagnostics(
            territory.maintenance_tasks, optimized
        ),
        "unscheduled_tasks": _unscheduled_diagnostics(
            territory.maintenance_tasks, optimized
        ),
    }


def _response(
    territory: LoadedTerritory,
    compared: dict[str, Any],
    *,
    parent_plan_id: str | None = None,
) -> dict[str, Any]:
    baseline = compared["baseline"]
    optimized = compared["optimized"]
    plan = optimized["plan"]
    comparison = compared["comparison"]
    if plan.get("status") != "success":
        raise PlanningExecutionError(
            f"Optimizer returned non-success status {plan.get('status')!r}."
        )

    horizon = territory.manifest.planning_horizon
    response = {
        "status": plan["status"],
        "blocks": plan["blocks"],
        "unscheduled_tasks": plan["unscheduled_tasks"],
        "metrics": {
            "baseline_block_hours": _hours(baseline["possession_minutes"]),
            "optimized_block_hours": _hours(optimized["possession_minutes"]),
            "baseline_affected_trains": baseline["plan"]["metrics"][
                "optimized_affected_trains"
            ],
            "optimized_affected_trains": plan["metrics"]["optimized_affected_trains"],
            "integrated_blocks": optimized["integrated_blocks"],
        },
        "proof_state": optimized["proof_state"],
        "comparison_proof_state": compared["comparison_proof_state"],
        "comparison": {
            "baseline_label": BASELINE_LABEL,
            "same_task_set": comparison["same_task_set"],
            "closure_saved_minutes": comparison["closure_saved_minutes"],
            "closure_reduction_percent": comparison["closure_reduction_percent"],
            "baseline_proof_state": baseline["proof_state"],
            "optimized_proof_state": optimized["proof_state"],
        },
        "planning_context": {
            "territory_id": territory.manifest.territory_id,
            "display_name": territory.manifest.display_name,
            "territory_status": territory.manifest.status,
            "provenance": sorted(
                {item["label"] for item in territory.manifest.provenance}
            ),
            "horizon_start": horizon["start_time"],
            "horizon_end": horizon["end_time"],
            "resource_context_applied": territory.resource_context is not None,
            "resource_provenance": territory.resource_provenance,
            "solver_time_limit_seconds_per_plan": DEMO_SOLVE_LIMIT_SECONDS,
        },
        "analysis": _analysis(territory, compared),
        "alternatives": [
            {
                "alternative_id": "rail-separate",
                "label": "Separate departmental possessions",
                "solver_backed": True,
                "proof_state": baseline["proof_state"],
                "blocks": baseline["plan"]["blocks"],
                "metrics": _analysis_plan(baseline)["metrics"],
                "tradeoff": "Preserves department separation but consumes more possession minutes when tasks can safely share.",
            },
            {
                "alternative_id": "railsync-coordinated",
                "label": "Coordinated RailSync plan",
                "solver_backed": True,
                "proof_state": optimized["proof_state"],
                "blocks": plan["blocks"],
                "metrics": _analysis_plan(optimized)["metrics"],
                "tradeoff": "Integrates compatible work while retaining every hard capacity, train, deadline, power, crew, and machine constraint.",
            },
        ],
    }
    response["plan_identity"] = register_plan(
        territory.manifest.territory_id, response, parent_plan_id
    )
    return response


def optimize_registered_territory(
    territory_id: str = DEFAULT_TERRITORY_ID,
    *,
    profile: str = SUPPORTED_PROFILE,
    horizon_hours: int | None = None,
    risk_mode: str = "STATIC",
    risk_profiles=(),
    task_overrides: list[dict[str, Any]] | None = None,
    parent_plan_id: str | None = None,
) -> dict[str, Any]:
    """Run the existing fair comparison for one registered planning input."""
    if profile != SUPPORTED_PROFILE:
        raise InvalidPlanningRequest(f"Unsupported planning profile {profile!r}.")
    territory = load_planning_territory(territory_id)
    if task_overrides:
        tasks = {task["task_id"]: dict(task) for task in territory.maintenance_tasks}
        allowed = {
            "duration_minutes", "deadline", "criticality", "urgency", "overdue_days",
            "requires_power_block", "crew_type", "machine_type", "preferred_window",
            "section_id", "section_ids", "capacity_resource_ids",
        }
        for override in task_overrides:
            task_id = override.get("task_id")
            if task_id not in tasks:
                raise InvalidPlanningRequest(f"Unknown task override: {task_id}")
            unexpected = sorted(set(override) - allowed - {"task_id"})
            if unexpected:
                raise InvalidPlanningRequest(
                    f"Unsupported task override fields: {', '.join(unexpected)}"
                )
            tasks[task_id].update({key: value for key, value in override.items() if key != "task_id"})
        territory = replace(territory, maintenance_tasks=list(tasks.values()))
    start_time, end_time, configured_hours = _horizon(territory)
    if horizon_hours is not None and horizon_hours != configured_hours:
        raise InvalidPlanningRequest(
            f"Territory {territory_id!r} uses a fixed {configured_hours:g}-hour horizon."
        )
    _validate_resource_coverage(territory)
    try:
        penalties, risk = planning_risk(territory.train_occupancy, risk_mode, risk_profiles)
    except ValueError as error:
        raise InvalidPlanningRequest(str(error)) from error

    try:
        compared = compare_plans(
            territory.as_optimizer_input(),
            start_time,
            end_time,
            resource_context=territory.resource_context,
            allowances=DEMO_ALLOWANCES,
            time_limit_seconds=DEMO_SOLVE_LIMIT_SECONDS,
            risk_penalties=penalties,
        )
    except RuntimeError as error:
        raise PlanningExecutionError(str(error)) from error
    return dict(_response(territory, compared, parent_plan_id=parent_plan_id), risk=risk)
