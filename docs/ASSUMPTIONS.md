# Implemented Prototype Assumptions

- Candidate generation is deterministic preprocessing, separate from CP-SAT.
  Section occupancies are half-open intervals. Overlapping, nested, duplicate,
  and touching intervals are merged before their complement is taken.
- Model B: candidate usable time subtracts train safety only. Each task reserves
  `setup_minutes + duration_minutes + release_minutes` inside that time.
  Optional task setup/release values replace configuration defaults, never add
  to them. Productive duration retains its existing contract meaning.
- Public ScheduledBlock start/end are the actual half-open possession interval:
  setup start through release completion. Duration includes setup + work + release.
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
- Existing maximize-count / earlier-start objective and one-task blocks remain.
  No departmental integration, resource roster, or priority model is introduced.
- Internal reason codes: WRONG_SECTION, INSUFFICIENT_USABLE_DURATION,
  DEADLINE_VIOLATION, POWER_BLOCK_UNAVAILABLE, CREW_UNAVAILABLE,
  MACHINE_UNAVAILABLE. Public unscheduled task IDs and response shape remain.
- The existing backend API serves mock responses and is not connected to CP-SAT.
  This phase does not change that architecture or the shared contract.

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
