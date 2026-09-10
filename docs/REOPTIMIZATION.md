# RailSync v2 recovery semantics

POST /api/reoptimize validates the supplied current plan, applies one explicitly synthetic disruption, regenerates capacity windows, and solves the same CP-SAT model with stability objectives. The base plan is returned unchanged.

## Supported disruption types

- TRAIN_DELAY and TRAIN_DELAYS
- CREW_UNAVAILABLE
- MACHINE_UNAVAILABLE
- POWER_ISOLATION_CANCELLED
- SECTION_UNAVAILABLE
- WEATHER_RESTRICTION
- EMERGENCY_WORK

Every type changes solver inputs; no Scenario Lab option is decorative.

## Time awareness

A disruption may supply effective_time. Tasks in blocks marked COMPLETED, IN_PROGRESS, or FROZEN, plus blocks started before that time, receive hard fixed-start constraints. Future feasible blocks are preserved through stability objectives. If an immutable block is invalidated, escalation_required is returned instead of silently moving history.

Recovery first preserves normal maintenance service priorities, then maximizes previously scheduled tasks, intact groupings, unchanged possessions, and unchanged starts before minimizing displacement. Train, capacity, compatibility, deadline, power, crew, and machine constraints stay hard.

## Status and application

Results distinguish retained, shifted, cancelled/new groups, regrouped tasks, newly unscheduled work, displacement, affected sections, proof state, immutable task IDs, and escalation. Scenario results are synthetic previews. The browser requires “Apply recovered plan explicitly”; recovery never auto-approves or publishes.
