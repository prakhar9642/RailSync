"""Reproducible small synthetic benchmark; no production-scale performance claim."""

import json
from time import perf_counter

try:
    from .optimizer import optimize_schedule
except ImportError:
    from optimizer import optimize_schedule


def benchmark(task_counts=(10, 20, 40), time_limits=(2.0, 5.0)):
    results = []
    for count in task_counts:
        tasks = [dict(
            task_id=f"T{i:03d}", section_id=f"SEC{i // 5:02d}",
            department=("ENGINEERING", "S&T", "TRD")[i % 3],
            compatibility_group=f"GROUP{i // 5}", duration_minutes=30 + (i % 3) * 15,
            criticality=1 + i % 9, urgency=1 + i % 5, overdue_days=i % 7,
        ) for i in range(count)]
        for budget in time_limits:
            for mode, integration in (("baseline", False), ("optimized", True)):
                print(f"Starting {count} tasks / {mode} ({budget}s total)", flush=True)
                start = perf_counter()
                facts = {}
                plan = optimize_schedule(
                    dict(maintenance_tasks=tasks, train_occupancy=[]),
                    "2026-09-01T00:00:00", "2026-09-01T06:00:00",
                    allow_integration=integration,
                    diagnostics=facts,
                    time_limit_seconds=budget,
                )
                stages = facts["priority_stages"]
                metrics = facts.get("service_metrics", {})
                reached = [stage for stage in stages if stage["status"] != "NOT_RUN"]
                results.append(dict(
                    tasks=count,
                    sections=(count + 4) // 5,
                    mode=mode,
                    total_budget_seconds=budget,
                    wall_seconds=perf_counter() - start,
                    proof_state=facts["proof_state"],
                    last_objective_stage_reached=facts["last_stage_reached"],
                    returned_solution_stage=facts["solution_stage"],
                    last_solver_status=reached[-1]["solver_status"] if reached else None,
                    scheduled_task_count=metrics.get("scheduled_task_count", 0),
                    possession_minutes=metrics.get("possession_minutes", 0),
                    valid_plan_returned=plan["status"] == "success",
                ))
                print(json.dumps(results[-1]), flush=True)
    return results


if __name__ == "__main__":
    benchmark()
