# Phase 7 recovery

`POST /api/reoptimize` validates a supplied current plan against the registered
territory, then applies a deterministic disruption and solves the existing CP-SAT
model with additional stability objectives. It does not call `/api/optimize` or
rerun a baseline. The returned base plan remains immutable for comparison.

Only `TRAIN_DELAY` is supported. All supplied occupancy rows for the selected
train shift entry and exit forward by the same integer delay (0–1440 minutes),
including rows that move beyond the horizon. Duration and order are preserved.
No propagation to other trains, dispatcher simulation, actual-time inference or
live running-status connection is claimed. Candidate generation reruns over the
modified rows and keeps static safety margins. Zero delay is a valid no-change
test. Emergency maintenance, crew disruptions and section closures are deferred.

This is a full-horizon what-if simulation. It has no current-time/frozen-work
boundary, executed-task state or approval workflow. Scenario results do not
automatically replace the Planning result; every new scenario starts from that
original base and the registered input snapshot. Chained scenarios are unsupported.

## Request and validation

```json
{
  "territory_id": "eastern_hdn_test_fixture",
  "horizon_start": "2026-09-01T00:00:00",
  "horizon_end": "2026-09-01T06:00:00",
  "current_plan": { "blocks": [], "unscheduled_tasks": [] },
  "disruption": { "type": "TRAIN_DELAY", "train_id": "EHDN_TR105", "delay_minutes": 25 },
  "risk_mode": "STATIC",
  "risk_profiles": []
}
```

Replace the illustrated empty plan with the real Planning result's `blocks` and
`unscheduled_tasks`. The horizon must match the territory manifest. Unknown and
placeholder territories are rejected. Task accounting, duplicate tasks/block
IDs, duration, compatibility, section, train safety, deadlines, power and aggregate
crew/machine capacity are validated before solving. The request is a feasible
user-supplied current plan, not proof of Railway approval. Unsupported legacy
placeholder inputs receive 422. No incumbent receives 503, never fake success.

## Lexicographic objectives

All hard constraints apply first. Recovery maximizes criticality, urgency,
overdue days and task count in the same order as normal planning. It then:

1. Maximizes previously scheduled tasks still scheduled.
2. Maximizes intact previous possession task memberships.
3. Maximizes intact possessions with unchanged start times (duration is fixed by membership).
4. Maximizes previously scheduled tasks with unchanged starts.
5. Minimizes summed absolute start displacement of previous tasks still scheduled.
6. Uses normal possession minutes, block count, optional ML reserve, raw minimum
   and total boundary slack, then earliest task starts.

These are sequential exact objectives, not arbitrary weighted penalties.
Dropping work cannot buy stability above the maintenance-service priorities.
An old grouping is matched by its full task set and section, independent of new
solver block IDs. Group preservation precedes counting unchanged groups to prevent
regrouping from hiding shifts. No stability variable changes hard feasibility.

The existing five-second total solver budget applies to the full recovery solve,
not five seconds per stage. FULLY_OPTIMAL requires proof of every added stage.
FEASIBLE_BOUNDED retains a valid incumbent and makes no optimal-stability claim.
Skipped diagnostics enumerate the actual remaining stages, including extensions.

## Recovery accounting

An unchanged group is RETAINED; same group at another time is SHIFTED. A former
group without an exact new membership match is CANCELLED; a new unmatched group
is NEW. Group cancellation is not equivalent to task cancellation. Task changes
independently distinguish retained starts, shifted starts, newly scheduled and
newly unscheduled work; `regrouped` preserves membership-change information.

`total_shift_minutes` sums absolute reservation-start differences over old tasks
still scheduled, counting each task once (including members sharing a possession).
`total_block_shift_minutes` counts only exact matched groups once. Neither metric
assigns a fictitious time displacement to dropped or newly scheduled tasks.
`unscheduled_tasks_after_disruption` counts all outstanding tasks, while
`newly_unscheduled_task_ids` is the subset that was previously scheduled.

Original blocks invalidated by train protection are listed separately from all
changed groups. Other shifts may be caused by resource/section competition; the
UI does not claim a causal reason that the solver did not establish. Existing
task-window findings, resources, compatibility, slack and proof states are reused.
No recovery closure-savings claim is generated against a now-infeasible base.

## Frontend

Planning, Analysis and Scenario Lab share the latest plan in App state. Recovery
is stored separately and is cleared when normal optimization begins. Navigation
does not trigger a solve. Scenario Lab requires a real base plan, posts the selected
train and delay, handles loading/errors, and displays original/disrupted trains
and before/recovered possessions on one axis. The returned plan is informational,
not automatically approved. All scenario operations remain synthetic experiments.
