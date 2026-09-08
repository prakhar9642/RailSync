# Eastern HDN synthetic test fixture

`eastern_hdn_test_fixture` is deterministic fictional data marked `TEST_FIXTURE`.
It is not an Eastern HDN railway dataset, live Indian Railways operational data,
or a production feed. Its only purpose is to exercise the territory adapter and
unchanged optimizer through an explicit fixture ID.

The fixture contains 10 fictional stations, 9 consecutive sections, 49 occupancy
records for eight fictional trains, and 9 synthetic Engineering, S&T, and TRD
maintenance tasks. Dense central-section traffic and relatively open outer
sections provide constrained windows and possession-sharing opportunities.

Power-requiring tasks use the canonical `requires_power_block` field. No resource
calendar is supplied, so availability remains unknown under existing semantics;
the fixture does not claim operational clearance.
