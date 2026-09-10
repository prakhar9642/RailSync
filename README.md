# RailSync v2

RailSync is an integrated railway maintenance decision-support prototype. It coordinates Engineering, S&T, and TRD work against public timetable-derived train occupancy using Google OR-Tools CP-SAT.

## Implemented product

- Three selectable public-timetable territories: Saktigarh–Memari, Virar–Dahanu Road, and New Delhi–Palwal.
- Explicit physical sections, capacity resources, directional tracks, multi-section possessions, crew/machines, power windows, setup/release, and deadlines.
- One browser session across Planning, Analysis, and Scenario Lab.
- Route-wide time–distance visualization, solver-backed alternatives, temporary what-if, explanations, alerts, resources, provenance, history, CSV, and print-to-PDF.
- Draft → Reviewed → Approved → Published lifecycle and explicit apply actions.
- Time-aware recovery for train delays, crew/machine unavailability, power cancellation, section unavailability, weather, and emergency work.

Public timetable inputs are frozen decision-support snapshots, not live running data. Maintenance demand, resources, and scenarios are labeled synthetic prototypes. No Railway production system is connected.

## Run locally

From the repository root, install backend/requirements.txt and run:

    python -m uvicorn backend.main:app

In another terminal:

    cd frontend
    npm.cmd install
    npm.cmd run dev

Open http://localhost:5173. Vite proxies /api to FastAPI on 127.0.0.1:8000.

## Verify

    python -m data.validate_data
    python -m pytest -q -p no:cacheprovider
    cd frontend
    npm.cmd test -- --run
    npm.cmd run build

See [contracts](CONTRACTS.md), [assumptions](docs/ASSUMPTIONS.md), [provenance](docs/DATA_PROVENANCE.md), and [recovery semantics](docs/REOPTIMIZATION.md).
