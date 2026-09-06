"""Reproducible small synthetic benchmark; no production-scale performance claim."""

import json
from time import perf_counter

try:
    from .optimizer import optimize_schedule
except ImportError:
    from optimizer import optimize_schedule


def benchmark(task_counts=(10, 20, 40)):
    results = []
    for count in task_counts:
        tasks = [dict(
            task_id=f"T{i:03d}", section_id=f"SEC{i // 5:02d}",
            department=("ENGINEERING", "S&T", "TRD")[i % 3],
            compatibility_group=f"GROUP{i // 5}", duration_minutes=30 + (i % 3) * 15,
            criticality=1 + i % 9, urgency=1 + i % 5, overdue_days=i % 7,
        ) for i in range(count)]
        for mode, integration in (("baseline", False), ("optimized", True)):
            print(f"Starting {count} tasks / {mode} (2 seconds per stage)", flush=True)
            start = perf_counter()
            facts = {}
            plan = optimize_schedule(dict(maintenance_tasks=tasks, train_occupancy=[]),
                                     "2026-09-01T00:00:00", "2026-09-01T06:00:00",
                                     allow_integration=integration, diagnostics=facts,
                                     stage_time_limit_seconds=2)
            stages = facts["priority_stages"]
            results.append(dict(tasks=count, sections=(count + 4) // 5, mode=mode,
                                status=stages[-1]["status"], plan_status=plan["status"],
                                completed_optimal_stages=sum(s["status"] == "OPTIMAL" for s in stages),
                                solver_seconds=sum(s["runtime_seconds"] for s in stages),
                                slowest_stage=max(stages, key=lambda s: s["runtime_seconds"]),
                                wall_seconds=perf_counter() - start))
            print(json.dumps(results[-1]), flush=True)
    return results


if __name__ == "__main__":
    benchmark()
