"""Application service boundary for registered-territory planning."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from data import LoadedTerritory, load_territory
from optimizer.comparison import compare_plans
from optimizer.runtime import DEMO_SOLVE_LIMIT_SECONDS

DEFAULT_TERRITORY_ID = "eastern_hdn_test_fixture"
BASELINE_LABEL = "NON_INTEGRATED_CP_SAT_COMPARISON"
SUPPORTED_PROFILE = "Availability First"


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
        task["section_id"]
        for task in territory.maintenance_tasks
        if task.get("requires_power_block") or task.get("requires_power_isolation")
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


def _response(territory: LoadedTerritory, compared: dict[str, Any]) -> dict[str, Any]:
    baseline = compared["baseline"]
    optimized = compared["optimized"]
    plan = optimized["plan"]
    comparison = compared["comparison"]
    if plan.get("status") != "success":
        raise PlanningExecutionError(
            f"Optimizer returned non-success status {plan.get('status')!r}."
        )

    horizon = territory.manifest.planning_horizon
    return {
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
    }


def optimize_registered_territory(
    territory_id: str = DEFAULT_TERRITORY_ID,
    *,
    profile: str = SUPPORTED_PROFILE,
    horizon_hours: int | None = None,
) -> dict[str, Any]:
    """Run the existing fair comparison for one registered planning input."""
    if profile != SUPPORTED_PROFILE:
        raise InvalidPlanningRequest(f"Unsupported planning profile {profile!r}.")
    territory = load_planning_territory(territory_id)
    start_time, end_time, configured_hours = _horizon(territory)
    if horizon_hours is not None and horizon_hours != configured_hours:
        raise InvalidPlanningRequest(
            f"Territory {territory_id!r} uses a fixed {configured_hours:g}-hour horizon."
        )
    _validate_resource_coverage(territory)

    try:
        compared = compare_plans(
            territory.as_optimizer_input(),
            start_time,
            end_time,
            resource_context=territory.resource_context,
            time_limit_seconds=DEMO_SOLVE_LIMIT_SECONDS,
        )
    except RuntimeError as error:
        raise PlanningExecutionError(str(error)) from error
    return _response(territory, compared)
