# RailSync v2 shared contracts

Fields from v1 remain valid. Rich capacity fields are additive.

## Maintenance task

section_id is the primary legacy section. section_ids describes a multi-section possession. capacity_resource_ids names the exact protected infrastructure; when absent, every configured resource on each required section is protected conservatively.

Required legacy fields remain task_id, department, section_id, task_type, duration_minutes, criticality, urgency, overdue_days, deadline, requires_power_block, crew_type, and compatibility_group. Optional fields include section_ids, capacity_resource_ids, machine_type, preferred_window, and power_isolation_zone_id.

## Train occupancy

Required fields remain train_id, section_id, entry_time, and exit_time. direction, traffic_type, track_id, and capacity_resource_ids are optional. Direction selects capacity only when the section supplies direction_capacity_mapping; it never implies a track by itself.

## Scheduled block

Blocks retain v1 fields and may add footprint_id, section_ids, capacity_resource_ids, track_ids, power_isolation_zone_id, and operational status.

## Primary endpoints

- GET /api/territories, /dashboard, /tasks, /trains
- POST /api/optimize, /api/reoptimize, /api/what-if
- GET /api/rolling-plan, /resources, /alerts, /data-sources, /plans/history
- POST /api/plans/{plan_id}/transition, /explain, /copilot
- POST /api/import/tasks/validate, /export/blocks.csv, /export/print

A plan identity contains plan_id, integer version, lifecycle state, created_at, and optional parent_plan_id. What-if and recovery never replace a plan without an explicit apply action.
