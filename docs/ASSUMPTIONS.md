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
- No baseline scheduler exists. baseline_block_hours and baseline_affected_trains
  are always numeric 0 as an unavailable-baseline placeholder required for API
  compatibility, NOT a measured zero-closure baseline. Do not compute savings,
  differences or improvement percentages from these placeholders.
  Unscheduled tasks remain outstanding work; they contribute no scheduled
  possession hours and are never counted as saved closure.
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
  then sum of task reservation start minutes. Seven CP-SAT solves fix each proven
  optimum before proceeding. Missing priority fields default to 0 for legacy
  minimal inputs; supplied values must be non-negative integers. Deadlines remain
  hard constraints including each task's release. No weighted AI score is used.
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
  Seven exact solves may be expensive for larger instances. One worker ensures
  repeatable small demos; no time limit or large-instance performance guarantee
  is claimed. An unproven stage stops the hierarchy, never fixes its incumbent
  as an optimum; diagnostics distinguish FEASIBLE from OPTIMAL.
- Internal reason codes: WRONG_SECTION, INSUFFICIENT_USABLE_DURATION,
  DEADLINE_VIOLATION, POWER_BLOCK_UNAVAILABLE, CREW_UNAVAILABLE,
  MACHINE_UNAVAILABLE, POWER_WINDOW_UNAVAILABLE. Pair facts additionally include
  COMPATIBLE_GROUP, INCOMPATIBLE_GROUP, UNKNOWN_COMPATIBILITY,
  CREW_CAPACITY_CONFLICT and MACHINE_CAPACITY_CONFLICT. Public response shape remains.
- The existing backend API serves mock responses and is not connected to CP-SAT.
  This phase does not change that architecture or the shared contract.

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
use the same configuration throughout. No external dependencies were added.
The defaults are simple conservative prototype choices, not official Indian
Railways rules. No authoritative operational allowance source exists here.

Run the deterministic demonstration with `python optimizer/test_feasibility.py`.
Its 140-minute nominal gap becomes 110 safety-adjusted minutes. A 120-minute
productive task needs 135 minutes with setup/release and is rejected, while a
60-minute task needs 75 minutes and is scheduled.

# Requires Indian Railways Domain Validation

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
- Future explicit API representation of unavailable baseline metrics, and any
  additional productive-work timestamps, without confusing them with possession.
