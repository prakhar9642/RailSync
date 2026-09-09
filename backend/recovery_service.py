"""Validate a supplied current plan against registered inputs, then recover it."""
from ml.inference import planning_risk
from optimizer.recovery import recover_schedule
from optimizer.runtime import DEMO_SOLVE_LIMIT_SECONDS
from . import planning_service as planning


def reoptimize(request):
    territory = planning.load_planning_territory(request.territory_id)
    start, end, _ = planning._horizon(territory)
    if (request.horizon_start, request.horizon_end) != (start,end):
        raise planning.InvalidPlanningRequest("Recovery horizon must match the registered base planning horizon")
    planning._validate_resource_coverage(territory)
    data = territory.as_optimizer_input()
    base = request.current_plan.model_dump()
    scheduled = {t for b in base["blocks"] for t in b["tasks"]}
    expected = {t["task_id"] for t in territory.maintenance_tasks} - scheduled
    if set(base["unscheduled_tasks"]) != expected or len(base["unscheduled_tasks"]) != len(expected):
        raise planning.InvalidPlanningRequest("Current plan task accounting does not match the territory")
    try:
        penalties, risk = planning_risk(data["train_occupancy"], request.risk_mode,
                                        [p.model_dump() for p in request.risk_profiles])
        result = recover_schedule(data, base["blocks"], request.disruption.model_dump(), start, end,
            resource_context=territory.resource_context, allowances=planning.DEMO_ALLOWANCES,
            time_limit_seconds=DEMO_SOLVE_LIMIT_SECONDS, risk_penalties=penalties)
    except (ValueError, TypeError, KeyError) as error:
        raise planning.InvalidPlanningRequest(str(error)) from error
    except RuntimeError as error:
        raise planning.PlanningExecutionError(str(error)) from error
    facts, plan = result["diagnostics"], result["plan"]
    summary = dict(facts["service_metrics"], plan=plan, proof_state=facts["proof_state"],
                   task_windows=facts["task_windows"], pair_checks=facts["pair_checks"], outcomes=facts["outcomes"])
    recovered = dict(plan, proof_state=facts["proof_state"],
        service_metrics=planning._analysis_plan(summary)["metrics"],
        block_diagnostics=planning._block_diagnostics(territory.maintenance_tasks, summary),
        unscheduled_diagnostics=planning._unscheduled_diagnostics(territory.maintenance_tasks, summary))
    changes = result["changes"]
    return dict(status="success", territory_id=request.territory_id, horizon_start=start, horizon_end=end,
        disruption=request.disruption.model_dump(), scenario_provenance="SYNTHETIC_FORECAST_SCENARIO",
        base_plan=base, recovered_plan=recovered, recovery_metrics=changes["metrics"],
        block_changes=changes["block_changes"], task_changes=changes["task_changes"],
        newly_unscheduled_task_ids=changes["newly_unscheduled_task_ids"],
        invalidated_blocks=result["invalidated_blocks"], affected_sections=result["affected_sections"],
        train_occupancy=result["train_occupancy"], risk=risk)
