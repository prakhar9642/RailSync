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
