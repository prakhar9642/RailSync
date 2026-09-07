# RailSync Day 1 Corridor Data

## Corridor

**Delhi–Agra main line (real station names, synthetic train movements)**

This is a prototype corridor for RailSync. Station names and corridor order come from publicly documented Indian Railways Delhi–Agra route information. **Train IDs, occupancy windows, and all maintenance tasks are synthetic.** They must not be treated as live operational data or as an official Indian Railways timetable.

Stations in corridor order:

1. `STN01` — New Delhi
2. `STN02` — Hazrat Nizamuddin
3. `STN03` — Faridabad
4. `STN04` — Palwal
5. `STN05` — Kosi Kalan
6. `STN06` — Mathura Junction
7. `STN07` — Chata
8. `STN08` — Raja Ki Mandi
9. `STN09` — Agra Cantt

Eight consecutive sections (`SEC01`–`SEC08`) connect adjacent stations from New Delhi to Agra Cantt.

## Dataset Summary

- `stations.json` — 9 ordered corridor endpoints
- `sections.json` — 8 consecutive inter-station blocks
- `train_occupancy.json` — section occupancy for 35 trains (`TR101`–`TR135`)
- `maintenance_tasks.json` — 48 synthetic Day 1 tasks across Engineering, S&T, and TRD

Shared field names follow `CONTRACTS.md` exactly. Occupancy records use only `train_id`, `section_id`, `entry_time`, and `exit_time`.

## What Is Public vs Synthetic

### Public / documented (not copied as live train times)

**Sources checked:** [Indian Railways enquiry portal](https://enquiry.indianrail.gov.in/) and [RailYatri train route pages](https://www.railyatri.in/) for the Delhi–Agra corridor.

- **Access date:** 2026-08-31
- **Used from public sources:** Real station names, corridor ordering, and the general knowledge that this corridor carries mixed mail/express and slower services.
- **Not used:** Published train numbers, published departure/arrival minutes, or any claim that a `TRxxx` row is a real running train.

### Synthetic / assumed (do not treat as Railway data)

- All `train_id` values (`TR101`–`TR135`)
- All `entry_time` / `exit_time` occupancy windows
- Section travel times (about 13–23 minutes by constructed service type)
- All maintenance tasks, durations, scores, deadlines, crew types, and compatibility groups

**Do not claim these synthetic timings as real Railway data.**

### Assumptions

- All trains run in the down direction (New Delhi → Agra Cantt). Reverse-direction sections are not modelled on Day 1.
- Occupancy is continuous across consecutive sections: the next section `entry_time` equals the previous `exit_time` (no separate station dwell field).
- Planning window is the week of 2026-09-01 through 2026-09-07.
- `TR104` occupancy on `SEC03` matches the shared contract example in `CONTRACTS.md`.
- `ENG017` matches the shared maintenance-task example in `CONTRACTS.md`.
- `SNT004` is on `SEC03` so it can sit in the sample scheduled block from `CONTRACTS.md`.
- Engineering and S&T tasks that share `LINE_BLOCK_A` are intended to be combinable in an integrated possession.
- TRD tasks that need an electrical isolation use `requires_power_block: true` and `compatibility_group: POWER_BLOCK`.

## Data Rules

- Field names `train_id`, `section_id`, `entry_time`, and `exit_time` follow `CONTRACTS.md` exactly.
- Maintenance fields `task_id`, `department`, `section_id`, `task_type`, `duration_minutes`, `criticality`, `urgency`, `overdue_days`, `deadline`, `requires_power_block`, `crew_type`, and `compatibility_group` follow `CONTRACTS.md` exactly.
- Allowed `department` values: `ENGINEERING`, `S&T`, `TRD`.
- Every `section_id` in occupancy and tasks exists in `sections.json`.
- All occupancy records have `entry_time` earlier than `exit_time`.
- Trains moving across multiple sections progress forward in time along consecutive sections.

## Validation

```bash
python data/validate_data.py
```

The validator checks JSON parsing, contract field sets, referential integrity, occupancy temporal ordering, consecutive-section continuity, and maintenance-task department/score/deadline rules.
