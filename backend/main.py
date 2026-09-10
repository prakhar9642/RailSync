"""FastAPI transport for the RailSync planning service."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import planning_service, recovery_service
from .schemas import OptimizeRequest, OptimizeResponse, ReoptimizeRequest, ReoptimizeResponse
from ml.inference import status as ml_status

from data import TerritoryNotPopulatedError, UnknownTerritoryError, list_territories

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="RailSync Optimization API", version="1.0.0")
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
        "recent_alerts": [],
        "system_status": "operational",
    }


@app.get("/api/territories")
def get_territories():
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
            for manifest in list_territories()
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
    }


@app.get("/api/blocks")
def get_blocks():
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
