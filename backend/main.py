"""FastAPI transport for the RailSync planning service."""

from __future__ import annotations

import html
import logging

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse

from . import operations_service, planning_service, recovery_service
from .schemas import OptimizeRequest, OptimizeResponse, ReoptimizeRequest, ReoptimizeResponse
from ml.inference import status as ml_status

from data import TerritoryNotPopulatedError, UnknownTerritoryError, list_territories

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="RailSync Optimization API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _http_error(error: Exception) -> HTTPException:
    if isinstance(error, UnknownTerritoryError):
        return HTTPException(
            status_code=404,
            detail={"code": "UNKNOWN_TERRITORY", "message": str(error)},
        )
    if isinstance(error, TerritoryNotPopulatedError):
        return HTTPException(
            status_code=409,
            detail={"code": "TERRITORY_NOT_POPULATED", "message": str(error)},
        )
    if isinstance(error, planning_service.InvalidPlanningRequest):
        return HTTPException(
            status_code=422,
            detail={"code": "INVALID_PLANNING_REQUEST", "message": str(error)},
        )
    if isinstance(error, planning_service.PlanningExecutionError):
        return HTTPException(
            status_code=503,
            detail={"code": "NO_USABLE_PLAN", "message": str(error)},
        )
    LOGGER.exception("Unexpected RailSync planning error")
    return HTTPException(
        status_code=500,
        detail={
            "code": "OPTIMIZER_ERROR",
            "message": "Optimization failed unexpectedly.",
        },
    )


def _load_territory_or_http(territory_id: str):
    try:
        return planning_service.load_planning_territory(territory_id)
    except Exception as error:
        raise _http_error(error) from error


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RailSync Backend",
        "default_territory_id": planning_service.DEFAULT_TERRITORY_ID,
    }


@app.get("/api/dashboard")
def get_dashboard(
    territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID),
):
    territory = _load_territory_or_http(territory_id)
    return {
        "status": "success",
        "territory_id": territory_id,
        "display_name": territory.manifest.display_name,
        "territory_status": territory.manifest.status,
        "provenance": sorted(
            {item["label"] for item in territory.manifest.provenance}
        ),
        "planning_horizon": territory.manifest.planning_horizon,
        "stations": territory.stations,
        "sections": territory.sections,
        "tasks_count": len(territory.maintenance_tasks),
        "trains_count": len(territory.train_occupancy),
        "train_services": territory.train_services,
        "recent_alerts": operations_service.alerts(territory),
        "resources": operations_service.resource_view(territory),
        "system_status": "operational",
    }


@app.get("/api/territories")
def get_territories(include_test: bool = Query(default=False)):
    manifests = list_territories()
    if not include_test:
        manifests = tuple(
            manifest for manifest in manifests
            if manifest.status == "POPULATED"
            and "PUBLIC_TIMETABLE_DERIVED" in {item["label"] for item in manifest.provenance}
        )
    return {
        "territories": [
            {
                "territory_id": manifest.territory_id,
                "display_name": manifest.display_name,
                "description": manifest.description,
                "status": manifest.status,
                "provenance": sorted({item["label"] for item in manifest.provenance}),
                "planning_ready": (
                    manifest.status == "POPULATED"
                    and "maintenance_tasks" in manifest.available_datasets
                    and manifest.planning_horizon is not None
                    and manifest.resource_context is not None
                ),
            }
            for manifest in manifests
        ]
    }


@app.get("/api/tasks")
def get_tasks(
    territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID),
):
    territory = _load_territory_or_http(territory_id)
    return {
        "territory_id": territory_id,
        "provenance": sorted(
            {item["label"] for item in territory.manifest.provenance}
        ),
        "tasks": territory.maintenance_tasks,
    }


@app.get("/api/trains")
def get_trains(
    territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID),
):
    territory = _load_territory_or_http(territory_id)
    return {
        "territory_id": territory_id,
        "provenance": sorted(
            {item["label"] for item in territory.manifest.provenance}
        ),
        "trains": territory.train_occupancy,
        "services": territory.train_services,
    }


@app.get("/api/rolling-plan")
def get_rolling_plan(territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID)):
    territory = _load_territory_or_http(territory_id)
    latest = next(iter(operations_service.history(territory_id)), None)
    return {"territory_id": territory_id, **operations_service.rolling_view(territory, latest)}


@app.get("/api/resources")
def get_resources(territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID)):
    territory = _load_territory_or_http(territory_id)
    return {"territory_id": territory_id, **operations_service.resource_view(territory)}


@app.get("/api/alerts")
def get_alerts(territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID)):
    territory = _load_territory_or_http(territory_id)
    latest = next(iter(operations_service.history(territory_id)), None)
    return {"territory_id": territory_id, "alerts": operations_service.alerts(territory, latest)}


@app.get("/api/data-sources")
def get_data_sources(territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID)):
    territory = _load_territory_or_http(territory_id)
    return {
        "territory_id": territory_id,
        "sources": list(territory.manifest.provenance),
        "datasets": [
            {"dataset": name, "adapter": spec["adapter"], "record_count": len(getattr(territory, name))}
            for name, spec in territory.manifest.datasets.items()
        ],
        "service_source_urls": sorted({item["source_url"] for item in territory.train_services}),
    }


@app.get("/api/plans/history")
def get_plan_history(territory_id: str | None = Query(default=None)):
    return {"plans": operations_service.history(territory_id)}


@app.post("/api/plans/{plan_id}/transition")
def transition_plan(plan_id: str, payload: dict = Body(...)):
    try:
        return operations_service.transition_plan(
            plan_id, payload.get("target_state", ""), payload.get("actor", "planner"), payload.get("note", "")
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "INVALID_PLAN_TRANSITION", "message": str(error)}) from error


@app.post("/api/plans/{plan_id}/blocks/{block_id}/status")
def transition_block(plan_id: str, block_id: str, payload: dict = Body(...)):
    try:
        return operations_service.transition_block(
            plan_id, block_id, payload.get("target_status", ""), payload.get("actor", "planner")
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": "INVALID_BLOCK_TRANSITION", "message": str(error)}) from error


@app.post("/api/what-if")
def run_what_if(payload: dict = Body(...)):
    try:
        result = planning_service.optimize_registered_territory(
            payload.get("territory_id", planning_service.DEFAULT_TERRITORY_ID),
            task_overrides=payload.get("task_overrides") or [],
            parent_plan_id=payload.get("parent_plan_id"),
        )
        return {"permanent": False, "scenario_provenance": "SYNTHETIC_WHAT_IF", "result": result}
    except Exception as error:
        raise _http_error(error) from error


@app.post("/api/explain")
def explain_plan(payload: dict = Body(...)):
    block = payload.get("block") or {}
    if not block:
        raise HTTPException(status_code=422, detail={"code": "BLOCK_REQUIRED", "message": "Select a block to explain."})
    sections = block.get("section_ids") or [block.get("section_id")]
    resources = block.get("capacity_resource_ids") or sections
    return {
        "summary": f"{block.get('block_id', 'Block')} protects {len(resources)} capacity resource(s) across {len(sections)} physical section(s).",
        "facts": {
            "section_ids": sections,
            "capacity_resource_ids": resources,
            "tasks": block.get("tasks", []),
            "affected_trains": block.get("affected_trains", []),
            "integrated": bool(block.get("integrated")),
        },
        "reasoning": block.get("explanation", []),
        "counterfactual": "Use the solver-backed alternatives or What-if action to test a different duration, deadline, or footprint.",
    }


@app.post("/api/copilot")
def copilot(payload: dict = Body(...)):
    territory_id = payload.get("territory_id", planning_service.DEFAULT_TERRITORY_ID)
    territory = _load_territory_or_http(territory_id)
    selected = payload.get("selected_block")
    preview = None
    engine = "FACTUAL_PLAN_CONTEXT"
    if payload.get("task_overrides"):
        preview = run_what_if({
            "territory_id": territory_id,
            "task_overrides": payload["task_overrides"],
            "parent_plan_id": payload.get("parent_plan_id"),
        })
        engine = "CP_SAT_WHAT_IF"
    answer = (
        f"This plan uses {len(territory.sections)} physical sections and {len(territory.train_services)} named public services. "
        f"The selected block contains {len(selected.get('tasks', []))} task(s)."
        if selected else
        f"{territory.manifest.display_name} has {len(territory.maintenance_tasks)} prototype maintenance tasks and {len(territory.train_services)} named public services in this planning slice."
    )
    return {"answer": answer, "engine": engine, "selected_block": selected, "action_preview": preview, "disclaimer": "Copilot reports loaded facts and invokes the optimization engine for action previews; it does not certify railway operating authority."}


@app.post("/api/import/tasks/validate")
def validate_task_import(payload: dict = Body(...)):
    territory = _load_territory_or_http(payload.get("territory_id", planning_service.DEFAULT_TERRITORY_ID))
    records = payload.get("records")
    if records is None and payload.get("workbook_base64"):
        try:
            records = operations_service.parse_xlsx_records(payload["workbook_base64"])
        except ValueError as error:
            raise HTTPException(status_code=422, detail={"code": "INVALID_EXCEL_IMPORT", "message": str(error)}) from error
    if not isinstance(records, list):
        raise HTTPException(status_code=422, detail={"code": "INVALID_IMPORT", "message": "Provide canonical records or a base64 XLSX workbook."})
    required = {"task_id", "department", "section_id", "task_type", "duration_minutes"}
    section_ids = {item["section_id"] for item in territory.sections}
    errors = []
    seen = set()
    for index, record in enumerate(records, 1):
        missing = sorted(required - set(record)) if isinstance(record, dict) else sorted(required)
        if missing:
            errors.append({"row": index, "code": "MISSING_FIELDS", "detail": missing})
            continue
        if record["task_id"] in seen:
            errors.append({"row": index, "code": "DUPLICATE_TASK_ID", "detail": record["task_id"]})
        if record["section_id"] not in section_ids:
            errors.append({"row": index, "code": "UNKNOWN_SECTION", "detail": record["section_id"]})
        seen.add(record["task_id"])
    return {"valid": not errors, "permanent": False, "errors": errors, "preview": records[:20]}


@app.post("/api/export/blocks.csv", response_class=PlainTextResponse)
def export_blocks_csv(payload: dict = Body(...)):
    return PlainTextResponse(
        operations_service.blocks_csv(payload.get("blocks", [])),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=railsync-blocks.csv"},
    )


@app.post("/api/export/print", response_class=HTMLResponse)
def export_print_report(payload: dict = Body(...)):
    blocks = payload.get("blocks", [])
    rows = "".join(
        f"<tr><td>{html.escape(str(block.get('block_id', '')))}</td><td>{html.escape(', '.join(block.get('section_ids') or [block.get('section_id', '')]))}</td><td>{html.escape(str(block.get('start_time', '')))}</td><td>{html.escape(str(block.get('end_time', '')))}</td><td>{html.escape(', '.join(block.get('tasks', [])))}</td></tr>"
        for block in blocks
    )
    return HTMLResponse(f"<!doctype html><title>RailSync plan</title><style>body{{font:14px system-ui;margin:32px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #aaa;padding:8px}}</style><h1>RailSync plan report</h1><p>Print this verified view to PDF using the browser print dialog.</p><table><thead><tr><th>Block</th><th>Sections</th><th>Start</th><th>End</th><th>Tasks</th></tr></thead><tbody>{rows}</tbody></table>")


@app.get("/api/blocks")
def get_blocks(territory_id: str = Query(default=planning_service.DEFAULT_TERRITORY_ID)):
    latest = next(iter(operations_service.history(territory_id)), None)
    if latest:
        return {"status": "success", "territory_id": territory_id, "plan_identity": latest["identity"], "blocks": latest["blocks"]}
    return {
        "status": "not_generated",
        "blocks": [],
        "message": "Submit POST /api/optimize to generate a current plan.",
    }


@app.post("/api/optimize", response_model=OptimizeResponse)
def run_optimization(request: OptimizeRequest | None = None):
    request = request or OptimizeRequest()
    if request.corridor_id is not None and request.territory_id is not None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "AMBIGUOUS_TERRITORY",
                "message": "Specify territory_id or the legacy corridor_id alias, not both.",
            },
        )
    territory_id = (
        request.territory_id
        or request.corridor_id
        or planning_service.DEFAULT_TERRITORY_ID
    )
    try:
        return planning_service.optimize_registered_territory(
            territory_id,
            profile=request.profile or planning_service.SUPPORTED_PROFILE,
            horizon_hours=request.horizon_hours,
            risk_mode=request.risk_mode,
            risk_profiles=[p.model_dump() for p in request.risk_profiles],
        )
    except Exception as error:
        raise _http_error(error) from error


@app.post("/api/reoptimize", response_model=ReoptimizeResponse)
def run_reoptimization(request: ReoptimizeRequest):
    try:
        return recovery_service.reoptimize(request)
    except Exception as error:
        raise _http_error(error) from error


@app.get("/api/ml/status")
def get_ml_status():
    return ml_status()
