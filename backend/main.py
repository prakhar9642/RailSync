"""FastAPI transport for the RailSync planning service."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import planning_service
from .schemas import OptimizeRequest, OptimizeResponse, ReoptimizeRequest

from data import TerritoryNotPopulatedError, UnknownTerritoryError

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
        "tasks_count": len(territory.maintenance_tasks),
        "trains_count": len(territory.train_occupancy),
        "recent_alerts": [],
        "system_status": "operational",
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
        )
    except Exception as error:
        raise _http_error(error) from error


@app.post("/api/reoptimize")
def run_reoptimization(request: ReoptimizeRequest | None = None):
    _ = request
    raise HTTPException(
        status_code=501,
        detail={
            "code": "REOPTIMIZATION_NOT_IMPLEMENTED",
            "message": "Real reoptimization is not implemented in this phase.",
        },
    )
