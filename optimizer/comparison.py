"""Non-integrated CP-SAT ablation, not a model of Railway manual planning."""

try:
    from .optimizer import optimize_schedule, DEFAULT_HORIZON_START, DEFAULT_HORIZON_END
    from .candidate_windows import OperationalAllowances
    from .compatibility import CompatibilityPolicy
    from .metrics import compare_service
except ImportError:
    from optimizer import optimize_schedule, DEFAULT_HORIZON_START, DEFAULT_HORIZON_END
    from candidate_windows import OperationalAllowances
    from compatibility import CompatibilityPolicy
    from metrics import compare_service


def compare_plans(
    data, horizon_start=DEFAULT_HORIZON_START, horizon_end=DEFAULT_HORIZON_END, *,
    allowances=OperationalAllowances(), window_contexts=None, resource_context=None,
    compatibility_policy=CompatibilityPolicy(), time_limit_seconds=None,
    stage_time_limit_seconds=None,
    risk_penalties=None,
):
    """Same solver/inputs/objectives; only possession sharing differs.

    Returns internal summaries and plans. No new endpoint or public API fields.
    """
    results = {}
    for name, allow_integration in (("baseline", False), ("optimized", True)):
        diagnostics = {}
        plan = optimize_schedule(
            data, horizon_start, horizon_end, allowances=allowances,
            window_contexts=window_contexts, resource_context=resource_context,
            compatibility_policy=compatibility_policy, allow_integration=allow_integration,
            diagnostics=diagnostics, time_limit_seconds=time_limit_seconds,
            stage_time_limit_seconds=stage_time_limit_seconds,
            risk_penalties=risk_penalties,
        )
        if plan["status"] != "success":
            raise RuntimeError(f"{name} planning failed: {plan['status']}")
        results[name] = dict(diagnostics["service_metrics"], plan=plan,
                             priority_stages=diagnostics["priority_stages"],
                             task_windows=diagnostics["task_windows"],
                             pair_checks=diagnostics["pair_checks"],
                             outcomes=diagnostics["outcomes"],
                             proof_state=diagnostics["proof_state"],
                             last_stage_reached=diagnostics["last_stage_reached"],
                             solution_stage=diagnostics["solution_stage"],
                             time_limit_seconds=diagnostics["time_limit_seconds"])
    results["both_proven_optimal"] = all(
        results[name]["proof_state"] == "FULLY_OPTIMAL"
        for name in ("baseline", "optimized")
    )
    results["comparison_proof_state"] = (
        "FULLY_OPTIMAL" if results["both_proven_optimal"] else "FEASIBLE_BOUNDED"
    )
    results["comparison"] = compare_service(results["baseline"], results["optimized"])
    return results
