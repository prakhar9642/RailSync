# RailSync - SIH26027

## Goal

RailSync is a railway maintenance block planning prototype.

It combines train timetable / section occupancy information with maintenance requirements from Engineering, S&T and TRD.

The system uses constraint optimization to generate maintenance block plans that aim to reduce maintenance-induced railway asset downtime while respecting operational constraints.

## Prototype Scope

- One railway corridor
- Around 10 stations
- 30-40 trains
- 40-60 maintenance tasks
- Engineering, S&T and TRD departments
- Weekly planning horizon

## Core Flow

Train timetable
+
Maintenance requirements
→
Priority calculation
→
CP-SAT optimization
→
Integrated maintenance blocks
→
FastAPI backend
→
React web application

## Core Features

1. Baseline maintenance scheduler
2. OR-Tools CP-SAT optimizer
3. Train-section occupancy constraints
4. Engineering / S&T / TRD integrated block planning
5. Baseline vs optimized comparison
6. Explainable scheduling decisions
7. Scenario simulation
8. Dynamic re-optimization

## Application Views

1. Command Center
2. Planning Workspace
3. Optimization Analysis
4. Scenario Lab

## Data

Where feasible, public timetable-derived train data will be used.

Maintenance demand will use synthetic/sample data based on documented maintenance categories and clearly stated assumptions.
