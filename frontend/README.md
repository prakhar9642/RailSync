# RailSync frontend

The React/Vite client preserves one session across Landing, Planning, Analysis, and Scenario Lab.

Planning loads one of three public timetable territories and shows a route-wide time–distance diagram, maintenance demand, resource/risk controls, lifecycle, alternatives, what-if, exports, provenance, alerts, and Copilot. Analysis compares the same-work non-integrated CP-SAT baseline with RailSync. Scenario Lab runs real recovery engines and requires an explicit apply action.

Start FastAPI at http://127.0.0.1:8000, then run:

    npm.cmd install
    npm.cmd run dev

Vite proxies /api to FastAPI. Set VITE_API_BASE_URL for another deployment.
