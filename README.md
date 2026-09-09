# RailSync

SIH26027 prototype for integrated railway maintenance block planning.

## Stack

- Python
- Google OR-Tools CP-SAT
- FastAPI
- React
- CSV / JSON
- NetworkX where required

## Team Development

Read these files before development:

- PROJECT_SPEC.md
- CONTRACTS.md

Do not modify shared contracts without team discussion.

## Backend demo

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app
```

`POST /api/optimize` defaults to the explicitly synthetic
`eastern_hdn_test_fixture` planning input.

## Frontend demo

With FastAPI running on `http://127.0.0.1:8000`, start Vite:

```powershell
cd frontend
npm.cmd run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/api` to
FastAPI. `VITE_API_BASE_URL` can override the API prefix for another deployment.

## Phase 7: predict, optimize, recover

Planning and Analysis retain the real static CP-SAT workflow. Scenario Lab now
uses the current Planning result with `POST /api/reoptimize` for a train-delay
what-if scenario. Choose a train and delay, then inspect unchanged/shifted
possessions, outstanding tasks and solver proof. Each scenario preserves the
original base for comparison. Only train delay is currently supported.

An optional **experimental historical risk estimate** uses a frozen public
train–station aggregate dataset (1,479 rows / 42 trains). Its route-group holdout
MAE is 61.0 minutes, RMSE 90.2: it is not accurate individual-run forecasting.
Fictional fixture trains have no automatic historical mapping. Applying a public
profile requires an explicit synthetic forecast selection. Static mode is default;
ML never reduces hard safety margins. Inference uses a local JSON artifact and
does not need scikit-learn installed; optional offline training uses
`python -m pip install -r ml/requirements.txt` and `python -m ml.train`.

See [ML model and source](docs/ML_RISK_MODEL.md),
[recovery semantics](docs/REOPTIMIZATION.md), and
[data provenance](docs/DATA_PROVENANCE.md). No live Railway feed is connected.

Validation from the root (suites run separately because legacy optimizer tests
use direct-script imports):

```powershell
python data/validate_data.py
python -m pytest data -vv
python -m pytest optimizer -vv
python -m pytest backend -vv
python -m pytest ml -vv
cd frontend
npm.cmd run build
npm.cmd run lint
```
