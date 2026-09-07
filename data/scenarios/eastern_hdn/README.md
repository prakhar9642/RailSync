# Eastern HDN synthetic maintenance scenario

`eastern_hdn_demo_v1` is a `SYNTHETIC_SCENARIO`, not live Indian Railways
operational data. It exists to prove RailSync's corridor-independent architecture
through the normal territory loader and unchanged optimizer.

The scenario combines Engineering, S&T, and TRD work with varied durations and
priorities. Same-section pairs on `EHDN_SEC01` and `EHDN_SEC09` share explicit
compatibility groups, creating conditional possession-sharing opportunities.
`EHDN_ENG003` is urgent and must fit a narrow early window. `EHDN_TRD003` targets
the busiest section and demonstrates work that remains outstanding when no full
setup/work/release reservation fits.

Power-requiring tasks retain the canonical `requires_power_block` field. No
resource calendar is supplied, so power availability remains unknown under the
existing optimizer semantics; this scenario does not claim operational clearance.
