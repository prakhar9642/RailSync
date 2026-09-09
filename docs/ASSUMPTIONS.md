# Implemented Prototype Assumptions

- Candidate generation is deterministic preprocessing, separate from CP-SAT.
  Section occupancies are half-open intervals. Overlapping, nested, duplicate,
  and touching intervals are merged before their complement is taken.
- Model B: candidate usable time subtracts train safety only. Each task reserves
  `setup_minutes + duration_minutes + release_minutes` inside that time.
  Optional task setup/release values replace configuration defaults, never add
  to them. Productive duration retains its existing contract meaning.
- Public ScheduledBlock start/end are the actual half-open possession interval:
  setup start through release completion. A shared block starts all members
  together and ends at the latest member release: max(setup + work + release).
  Train conflict checks, section non-overlap and displayed timestamps refer to
  this same interval. Train safety margins remain outside possession.
- optimized_block_hours = round(sum(block possession minutes) / 60, 3).
  This sums section-hours, including concurrent possessions on different sections.
- Non-integrated planning baseline is a technical CP-SAT ablation, NOT an
  asserted reproduction of current Indian Railways manual planning. compare_plans
  sends the same data, horizon, allowances, window/resource contexts, priority
  policy and solver limits to one engine twice. allow_integration=False disables
  ALL sharing (including same-department sharing): each task owns a possession.
  No deliberately weak scheduling heuristic or late-start bias is introduced.
- Comparison is internal only. Standalone optimize_schedule does not run the
  baseline and retains public numeric baseline placeholders (0 = unavailable).
  Actual baseline service/possession metrics live in compare_plans.baseline.
  No backend/API/frontend integration or CONTRACTS.md change is made here.
- Closure saved minutes = baseline possession - optimized possession ONLY when
  scheduled task ID sets are identical. Otherwise saved minutes and reduction
  percent are None. When baseline possession > 0, percentage = saved minutes /
  baseline possession * 100. Equal empty sets have saved minutes 0, percent None.
  Negative differences are retained, not clipped into a positive savings claim.
- Both plans report scheduled/unscheduled IDs, task count, productive minutes,
  criticality/urgency/overdue-days served, possession minutes, block count and
  integrated block count. Unscheduled work remains outstanding, never saved closure.
- maintenance_delivery_efficiency = productive maintenance minutes delivered /
  actual unique possession minutes; None for zero possession. Concurrency can
  legitimately make this ratio exceed one; it is not an AI score.
- coordination_gain_minutes sums, once per shared block, individual setup/work/
  release reservation minutes minus that block's possession minutes. This includes
  same-department sharing, while integrated_blocks still counts cross-department
  possessions only. It is an assumption-dependent accounting measure, not an
  official Railway savings claim or a substitute for same-work baseline comparison.
- Safety is applied only where an actual previous/next train is supplied, including
  outside-horizon trains whose margins extend into the horizon. Horizon edges
  themselves add no fictional train buffer. Setup/release still fit in the horizon.
- Empty usable windows remain available as diagnostics. Their endpoints coincide;
  reported margins partition the nominal interval and are capped when exhausted.
- Existing ISO parsing accepts naive timestamps, offsets, and Z; mixing naive
  and aware timestamps is rejected. Times must align to exact whole minutes
  relative to the horizon, including deadlines. No timezone is inferred.
- Deadlines mean the full reservation, including release, must finish by the
  deadline. Feasibility checks earliest placement and supplies a latest start
  bound enforced in CP-SAT. Actual solved reservations are rechecked.
- Internal `window_contexts` maps candidate window IDs to `FeasibilityContext`.
  A supplied availability boolean applies throughout that particular window.
  Explicit false rejects required power, crew type, or machine type; omitted
  values/keys mean unknown and do not reject. This is conditional eligibility,
  not a verified operational clearance or a shared resource capacity model.
  FeasibilityResult.resource_checks reports power/crew/machine separately:
  PASSED for explicitly available required resources, FAILED for explicitly
  unavailable ones, UNKNOWN when required but availability is missing, and
  NOT_EVALUATED when the task has no corresponding requirement. UNKNOWN and
  NOT_EVALUATED never claim successful resource verification or cause rejection.
- `requires_power_block` OR optional `requires_power_isolation` requires power.
  Optional `machine_type` defaults to none. Existing crew fields are preserved.
  Optional `preferred_window` defaults to none and `splittable` to false; both
  are retained as metadata only. All tasks remain indivisible in this phase.
- Exact lexicographic priorities: maximize scheduled criticality, urgency,
  overdue_days, then task count; minimize unique possession minutes, block count,
  then maximize minimum boundary slack, maximize total boundary slack, then
  minimize sum of task reservation start minutes. Nine CP-SAT solves fix each proven
  optimum before proceeding. Missing priority fields default to 0 for legacy
  minimal inputs; supplied values must be non-negative integers. Deadlines remain
  hard constraints including each task's release. No weighted AI score is used.
- Per-possession before_boundary_slack_minutes = possession start - usable
  candidate start; after_boundary_slack_minutes = usable candidate end - possession
  end; boundary_slack_minutes = min(before, after). Required train safety is already
  subtracted in the candidate, and setup/release are inside the possession.
  The solver associates each active block with its containing candidate window.
- Slack is additional deterministic candidate-boundary margin, including horizon
  edges. It does not measure separation from other maintenance, resource-calendar
  slack, a probability of success, predicted train delay, or official reliability.
  Minimum block slack is maximized BEFORE total block slack, and only AFTER all
  six service/possession/block-count objectives. Unscheduled anchors are excluded
  from the minimum; empty plans have minimum and total slack 0. Both modes share
  this hierarchy. Public timestamps may move later than Phase 2 to gain margin.
- Boundary slacks are independently recomputed from returned possession times
  and checked against the solver values. No robustness percentage is generated.
- CompatibilityPolicy permits same non-empty, exact compatibility_group values
  conditionally, unless integration is disabled or that group is disabled.
  Different groups are INCOMPATIBLE; missing/blank information is UNKNOWN.
  CONDITIONAL means eligible under prototype policy, not railway approval.
- CP-SAT assigns tasks to explicit possession variables. Members synchronize
  reservation starts, each with its own setup/work/release duration. Possession
  length is their maximum, not sum. Every task also retains a separate block
  option; incompatible tasks can execute sequentially inside the same window.
  Overhead is not removed or added twice: per-task overhead remains intact and
  overlaps only under the conditional concurrent-execution policy.
- integrated=true only when one possession has at least two distinct non-empty
  department values. Same-department eligible work can share closure but is not
  counted as a multi-department integrated block. Each shared possession is
  counted once in closure metrics; no post-solve merging changes the objective.
- ResourceContext has crew_capacities and machine_capacities keyed by resource
  type/pool, with non-negative integer capacities. Each task consumes one unit
  for its full reservation. Pools are global across sections; CP-SAT cumulative
  constraints prevent aggregate over-allocation, including three or more tasks.
  No capacity entry means UNKNOWN, not an invented unlimited available crew.
- ResourceContext.power_windows maps section IDs to PowerWindow(start_time,
  end_time) sequences. Missing section means UNKNOWN; an empty sequence means
  explicitly unavailable. Touching/overlapping windows are unioned. Every required
  task's full reservation must fit the power availability union and its deadline.
  A shorter member's power requirement ends with its own reservation, not the
  longer shared possession. Resource allocation/travel outside that reservation
  is not modeled. Actual task reservations are rechecked after solving, and
  a separate event sweep verifies resource capacity.
- Existing window_contexts remain supported. Explicit unavailability there is
  never overridden by a positive global capacity or power window. Resource
  PASSED in candidate feasibility means individual eligibility, not a claim that
  simultaneous aggregate demands are feasible; CP-SAT enforces the latter.
- Optional internal diagnostics dictionary receives task-window reasons and
  resource-check states, conditional pair eligibility/capacity conflicts,
  ordered objective optima, and selected/unscheduled outcomes. An individually
  feasible but unselected task is LOWER_PRIORITY_THAN_SELECTED_WORK only when
  the hierarchy is proven optimal. NO_FEASIBLE_TASK_WINDOW retains its underlying
  rejection facts. None of these add fields to the public response.
- Solver size uses at most one block anchor per task, not all compatible subsets.
  Membership variables grow quadratically; pair restrictions can grow cubically.
  Nine exact solves may be expensive for larger instances. One worker ensures
  repeatable small plans; no large-instance performance guarantee is claimed.
  Default solves have no time limit. Optional `time_limit_seconds` is one total
  wall-clock budget covering preprocessing/model construction and all objective
  stages. Before every CP-SAT call, only the remaining budget is supplied. The
  older internal `stage_time_limit_seconds` keyword remains accepted for caller
  compatibility but now has the same total-budget meaning; both names together
  are rejected. An unproven stage stops the hierarchy, never fixes its incumbent
  as an optimum; diagnostics distinguish FEASIBLE from OPTIMAL. Stage runtimes
  are observational and not deterministic. compare_plans.both_proven_optimal
  distinguishes full optimal comparisons from feasible incumbents. A failed solve
  raises instead of being summarized as an empty successful plan.
- Internal reason codes: WRONG_SECTION, INSUFFICIENT_USABLE_DURATION,
  DEADLINE_VIOLATION, POWER_BLOCK_UNAVAILABLE, CREW_UNAVAILABLE,
  MACHINE_UNAVAILABLE, POWER_WINDOW_UNAVAILABLE. Pair facts additionally include
  COMPATIBLE_GROUP, INCOMPATIBLE_GROUP, UNKNOWN_COMPATIBILITY,
  CREW_CAPACITY_CONFLICT and MACHINE_CAPACITY_CONFLICT. The optimizer response
  shape remains; the backend adds proof, comparison and planning context fields.
- POST /api/optimize now loads a registered territory and calls the existing fair
  comparison pipeline. POST /api/reoptimize now supports the additive Phase 7
  train-delay recovery mode described below.

SOURCE/SCHEMA-BACKED: CONTRACTS.md contains department, compatibility_group,
crew_type and requires_power_block fields. It supplies field names, not official
activity compatibility, resource capacities or operating rules.

PROTOTYPE ASSUMPTIONS: same-group conditional integration, synchronized-start
reservations, one resource unit per task, and explicitly supplied synthetic
capacities/power windows. Production Railway rosters have not been supplied.

Run `python optimizer/test_integration.py` for the synthetic three-department
case: ENG017 (135 minutes) + SNT008 (75) share 135 minutes; TRD004 has explicitly
unavailable power; ENG_LOW loses to higher-criticality work. No savings percentage.

# Configurable Parameters

`OperationalAllowances` in `optimizer/candidate_windows.py` centralizes defaults:

| Parameter | Prototype default (minutes) | Applied to |
| --- | ---: | --- |
| safety_after_minutes | 15 | After previous train exit |
| safety_before_minutes | 15 | Before next train entry |
| setup_minutes | 10 | Each task reservation, unless overridden |
| release_minutes | 5 | Each task reservation, unless overridden |

All values must be non-negative whole integers (booleans rejected). Pass an
allowances instance to candidate generation, feasibility, and optimization;
use the same configuration throughout. No new optimizer dependencies were added.
The defaults are simple conservative prototype choices, not official Indian
Railways rules. No authoritative operational allowance source exists here.

Run the deterministic demonstration with `python optimizer/test_feasibility.py`.
Its 140-minute nominal gap becomes 110 safety-adjusted minutes. A 120-minute
productive task needs 135 minutes with setup/release and is rejected, while a
60-minute task needs 75 minutes and is scheduled.

# Requires Indian Railways Domain Validation

- Numeric criticality/urgency/overdue prioritization remains a prototype decision
  policy, requiring domain validation; boundary slack requires later disruption
  testing and is not predictive reliability.
- Exact Engineering/S&T/TRD activity-to-activity compatibility, shared setup/release
  procedures, real crew capacities, machine allocations and power-block windows.
- Safety margins by signalling, traffic direction, section, and train category.
- Actual possession/setup and restoration/release procedures and durations;
  whether overhead is per task or shared across coordinated departmental work.
- Deadline semantics and whether deadlines include possession release.
- Electrical isolation approval, applicable power availability, and restoration.
- Crew skills, real rosters, travel, machine availability, and shared capacities.
- Occupancy completeness, horizon boundary coverage, timezone conventions,
  bidirectional movement and crossing protection. Supplied sample data is synthetic.
- Any additional productive-work timestamps must remain distinct from possession.


Run `python optimizer/test_comparison.py` for same-work, different-work and robust
placement demos. Run `python optimizer/benchmark_planning.py` for bounded 10/20/40
synthetic task benchmarks (five tasks per section, no train/resource contention).
These are modest distributed instances, not production-scale railway benchmarks.

`DEMO_SOLVE_LIMIT_SECONDS = 5.0` in `optimizer/runtime.py` is the backend demo
limit supplied independently to the non-integrated and integrated plans. A full
comparison may therefore consume up to two solver budgets plus preprocessing and
HTTP overhead. This is an engineering setting, not a Railway rule. `None` retains
uncapped development behavior for direct optimizer callers.

Each run records `proof_state`: FULLY_OPTIMAL only after all nine stages are
proven; FEASIBLE_BOUNDED when a valid incumbent is returned after a budget or
unproven stage; INFEASIBLE when the model is proven infeasible before any plan;
NO_SOLUTION when no incumbent exists. A FEASIBLE result is never relabeled as
optimal. If a stage returns UNKNOWN, the previous stage's solver response is
retained. If no prior solution exists, public status remains non-success.

Every `priority_stages` diagnostic records stage/objective name, solver status,
termination reason, stage and cumulative elapsed seconds, remaining budget before
the call, and objective value when an incumbent exists. Proven values also carry
`optimum`. Skipped lower stages are explicitly `NOT_RUN`. Timing fields are
observational; tests do not depend on exact milliseconds.

Baseline and RailSync comparison gives each planner the same complete budget,
independently. Their proof states and the aggregate comparison proof state remain
visible internally. Same-task-set arithmetic is still available for bounded valid
plans, but the comparison is not labeled fully optimal unless both runs prove all
nine stages.

The authoritative backend demonstration uses `eastern_hdn_test_fixture` from
2026-09-01T00:00:00 through 2026-09-01T06:00:00. Its one-unit crew capacities and
section power windows are `TEST_FIXTURE` assumptions. The API labels its baseline
`NON_INTEGRATED_CP_SAT_COMPARISON`; it is not current or manual Railway practice.

## Phase 7 additions

Normal STATIC optimization retains all nine original objectives and hard
constraints. Optional ML_ASSISTED mode adds risk-reserve preferences after
possession/block-count objectives. The model estimates historical aggregate
average delay with substantial error; it does not predict an individual future
train's arrival or certify safe maintenance. Fictional trains require explicit
synthetic profile transfer. Missing model/profile data falls back to static.
See [ML_RISK_MODEL.md](ML_RISK_MODEL.md) for exact mathematics and evaluation.

Recovery shifts all supplied occupancies of one selected train by the injected
delay, regenerates candidate windows, and adds exact stability stages after the
four maintenance-service objectives. Group and task changes are measured
separately. This full-horizon what-if mode does not freeze completed/in-progress
work or model dispatch/knock-on delays. It is not live operational recovery.
See [REOPTIMIZATION.md](REOPTIMIZATION.md) for validation, hierarchy and metrics.
