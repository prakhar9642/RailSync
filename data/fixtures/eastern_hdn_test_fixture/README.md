# Eastern HDN synthetic test fixture

`eastern_hdn_test_fixture` is deterministic fictional data marked `TEST_FIXTURE`.
It is not an Eastern HDN railway dataset, live Indian Railways operational data,
or a production feed. Its only purpose is to exercise the territory adapter and
unchanged optimizer through an explicit fixture ID.

The fixture contains 10 fictional stations, 9 consecutive sections, 49 occupancy
records for eight fictional trains, and 9 synthetic Engineering, S&T, and TRD
maintenance tasks. Dense central-section traffic and relatively open outer
sections provide constrained windows and possession-sharing opportunities.

The authoritative planning horizon is `2026-09-01T00:00:00` through
`2026-09-01T06:00:00`. `resource_context.json` supplies one explicitly synthetic
unit for every referenced crew pool, no machine pools because no task requires
one, power availability for sections 08 and 09, and explicit unavailability for
section 06. These are deterministic test assumptions, not Railway capacities.

Power-requiring tasks use the canonical `requires_power_block` field. The fixture
does not claim operational clearance.
