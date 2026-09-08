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
