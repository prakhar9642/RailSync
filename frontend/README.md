# RailSync frontend

The Planning Workspace loads the explicitly synthetic
`eastern_hdn_test_fixture` from FastAPI and sends optimization requests to the
real RailSync CP-SAT backend.

## Local development

Start FastAPI from the repository root at `http://127.0.0.1:8000`:

```powershell
python -m uvicorn backend.main:app
```

Then start Vite at `http://localhost:5173`:

```powershell
cd frontend
npm.cmd run dev
```

Vite proxies `/api` to the local FastAPI process. For another deployment, set
`VITE_API_BASE_URL` to the backend API prefix, such as
`https://example.invalid/api`. No external API is required by default.
