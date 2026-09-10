# RailSync v2 product specification

## Goal

Evolve the maintenance-block demonstration into a credible planning product while preserving the CP-SAT optimizer, comparison workflow, Planning/Analysis/Scenario views, recovery, provenance, and deterministic tests.

## Public product flow

1. Select one of three public timetable territories.
2. Review monthly demand, weekly coordination, and the solver-generated day-of plan.
3. Inspect stations, train paths, tasks, possessions, and capacity footprints in a time–distance view.
4. Compare the non-integrated CP-SAT baseline with the integrated plan on the same task set and constraints.
5. Explain decisions, run temporary what-if changes, review resources/alerts, export results, and advance the lifecycle.
6. Inject disruptions, keep elapsed/frozen work immutable, and explicitly apply a recovery.

## Safety and truthfulness

RailSync is decision support, not signalling, dispatching, or operating authority. Public schedules are snapshots. Maintenance, resource, and disruption data are synthetic. Direction is descriptive unless a section declares an explicit direction-to-capacity mapping. Unknown capacity is protected conservatively.

## Completion criteria

Canonical data validates, backend tests and frontend tests/build pass, and manual browser flows cover landing → planning → analysis → scenario → recovery for all public territories.
