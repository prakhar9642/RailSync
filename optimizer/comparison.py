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
    compatibility_policy=CompatibilityPolicy(), stage_time_limit_seconds=None,
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
            diagnostics=diagnostics, stage_time_limit_seconds=stage_time_limit_seconds,
        )
        if plan["status"] != "success":
            raise RuntimeError(f"{name} planning failed: {plan['status']}")
        results[name] = dict(diagnostics["service_metrics"], plan=plan,
                             priority_stages=diagnostics["priority_stages"])
    results["both_proven_optimal"] = all(
        len(results[name]["priority_stages"]) == 9
        and all(stage["status"] == "OPTIMAL" for stage in results[name]["priority_stages"])
        for name in ("baseline", "optimized")
    )
    results["comparison"] = compare_service(results["baseline"], results["optimized"])
    return results
