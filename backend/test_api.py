"""HTTP-boundary tests for real registered-territory optimization."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import planning_service
from backend.main import app
from data import load_territory
from optimizer.feasibility import task_requirements
from optimizer.time_utils import parse_datetime

client = TestClient(app)
FIXTURE_ID = "eastern_hdn_test_fixture"


@pytest.fixture(scope="module")
def optimized_response() -> dict:
    response = client.post("/api/optimize", json={"territory_id": FIXTURE_ID})
    assert response.status_code == 200
    return response.json()


def test_health_check_still_works() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "RailSync Backend",
        "default_territory_id": FIXTURE_ID,
    }


def test_dashboard_uses_authoritative_territory() -> None:
    territory = load_territory(FIXTURE_ID)
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["territory_id"] == FIXTURE_ID
    assert dashboard["display_name"] == "Eastern HDN Synthetic Test Fixture"
    assert dashboard["territory_status"] == "POPULATED"
    assert dashboard["provenance"] == ["TEST_FIXTURE"]
    assert dashboard["planning_horizon"] == territory.manifest.planning_horizon
    assert dashboard["stations"] == territory.stations
    assert dashboard["sections"] == territory.sections
    assert dashboard["tasks_count"] == 9
    assert dashboard["trains_count"] == 49


def test_tasks_and_trains_come_from_territory_loader() -> None:
    territory = load_territory(FIXTURE_ID)
    tasks = client.get("/api/tasks").json()
    trains = client.get("/api/trains").json()
    assert tasks == {
        "territory_id": FIXTURE_ID,
        "provenance": ["TEST_FIXTURE"],
        "tasks": territory.maintenance_tasks,
    }
    assert trains == {
        "territory_id": FIXTURE_ID,
        "provenance": ["TEST_FIXTURE"],
        "trains": territory.train_occupancy,
    }


def test_optimize_invokes_real_solver_and_removes_old_mock_block(
    optimized_response: dict,
) -> None:
    assert optimized_response["status"] == "success"
    assert len(optimized_response["blocks"]) == 6
    assert not any(
        block["section_id"] == "SEC01"
        and block["start_time"] == "2026-09-01T02:00:00"
        and block["end_time"] == "2026-09-01T04:00:00"
        for block in optimized_response["blocks"]
    )
    assert optimized_response["planning_context"]["territory_id"] == FIXTURE_ID


@pytest.mark.parametrize("territory_id", ["eastern_hdn", "western_hdn"])
def test_placeholder_territories_are_rejected(territory_id: str) -> None:
    response = client.post("/api/optimize", json={"territory_id": territory_id})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "TERRITORY_NOT_POPULATED"


def test_unknown_territory_is_rejected() -> None:
    response = client.post("/api/optimize", json={"territory_id": "missing"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "UNKNOWN_TERRITORY"


def test_blocks_do_not_overlap_protected_train_occupancy(
    optimized_response: dict,
) -> None:
    territory = load_territory(FIXTURE_ID)
    for block in optimized_response["blocks"]:
        block_start = parse_datetime(block["start_time"])
        block_end = parse_datetime(block["end_time"])
        for train in territory.train_occupancy:
            if train["section_id"] != block["section_id"]:
                continue
            assert not (
                block_start < parse_datetime(train["exit_time"])
                and parse_datetime(train["entry_time"]) < block_end
            )
        assert block["affected_trains"] == []


def test_block_timestamps_cover_complete_reservations(
    optimized_response: dict,
) -> None:
    tasks = {
        task["task_id"]: task
        for task in load_territory(FIXTURE_ID).maintenance_tasks
    }
    for block in optimized_response["blocks"]:
        actual_minutes = int(
            (
                parse_datetime(block["end_time"])
                - parse_datetime(block["start_time"])
            ).total_seconds()
            // 60
        )
        expected_minutes = max(
            task_requirements(tasks[task_id]).required_minutes
            for task_id in block["tasks"]
        )
        assert actual_minutes == expected_minutes


def test_integrated_and_unscheduled_results_survive_serialization(
    optimized_response: dict,
) -> None:
    integrated = [block for block in optimized_response["blocks"] if block["integrated"]]
    assert len(integrated) == 2
    assert all(len(block["tasks"]) == 2 for block in integrated)
    assert optimized_response["unscheduled_tasks"] == ["EHDN_TRD003"]


def test_real_non_integrated_baseline_replaces_fake_zero(
    optimized_response: dict,
) -> None:
    assert optimized_response["metrics"]["baseline_block_hours"] == 6.75
    assert optimized_response["metrics"]["optimized_block_hours"] == 5.0
    assert optimized_response["comparison"]["baseline_label"] == (
        "NON_INTEGRATED_CP_SAT_COMPARISON"
    )
    assert optimized_response["comparison"]["same_task_set"] is True
    assert optimized_response["comparison"]["closure_saved_minutes"] == 105


def test_bounded_feasible_proof_is_not_labeled_optimal(monkeypatch) -> None:
    bounded = {
        "baseline": {
            "possession_minutes": 0,
            "integrated_blocks": 0,
            "proof_state": "FEASIBLE_BOUNDED",
            "plan": {"metrics": {"optimized_affected_trains": 0}},
        },
        "optimized": {
            "possession_minutes": 0,
            "integrated_blocks": 0,
            "proof_state": "FEASIBLE_BOUNDED",
            "plan": {
                "status": "success",
                "blocks": [],
                "unscheduled_tasks": [],
                "metrics": {"optimized_affected_trains": 0},
            },
        },
        "comparison_proof_state": "FEASIBLE_BOUNDED",
        "comparison": {
            "same_task_set": True,
            "closure_saved_minutes": 0,
            "closure_reduction_percent": None,
        },
    }
    monkeypatch.setattr(planning_service, "compare_plans", lambda *args, **kwargs: bounded)
    response = client.post("/api/optimize", json={"territory_id": FIXTURE_ID})
    assert response.status_code == 200
    assert response.json()["proof_state"] == "FEASIBLE_BOUNDED"
    assert response.json()["comparison_proof_state"] == "FEASIBLE_BOUNDED"
    assert "OPTIMAL" not in response.json()["proof_state"]


@pytest.mark.parametrize("solver_status", ["unknown", "infeasible"])
def test_no_incumbent_becomes_honest_service_failure(
    monkeypatch, solver_status: str
) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError(f"baseline planning failed: {solver_status}")

    monkeypatch.setattr(planning_service, "compare_plans", fail)
    response = client.post("/api/optimize", json={"territory_id": FIXTURE_ID})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "NO_USABLE_PLAN"


def test_unexpected_optimizer_exception_becomes_server_failure(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise ArithmeticError("solver defect")

    monkeypatch.setattr(planning_service, "compare_plans", fail)
    response = client.post("/api/optimize", json={"territory_id": FIXTURE_ID})
    assert response.status_code == 500
    assert response.json()["detail"] == {
        "code": "OPTIMIZER_ERROR",
        "message": "Optimization failed unexpectedly.",
    }


def test_invalid_horizon_is_rejected() -> None:
    malformed = client.post(
        "/api/optimize", json={"territory_id": FIXTURE_ID, "horizon_hours": 0}
    )
    mismatched = client.post(
        "/api/optimize", json={"territory_id": FIXTURE_ID, "horizon_hours": 24}
    )
    assert malformed.status_code == 422
    assert mismatched.status_code == 422
    assert mismatched.json()["detail"]["code"] == "INVALID_PLANNING_REQUEST"


def test_synthetic_resource_context_is_passed_and_repeat_is_deterministic(
    monkeypatch, optimized_response: dict
) -> None:
    original = planning_service.compare_plans
    captured = []

    def capture(*args, **kwargs):
        captured.append(kwargs["resource_context"])
        return original(*args, **kwargs)

    monkeypatch.setattr(planning_service, "compare_plans", capture)
    repeated = client.post("/api/optimize", json={"territory_id": FIXTURE_ID})
    assert repeated.status_code == 200
    assert repeated.json() == optimized_response
    context = captured[0]
    assert context.crew_capacities == {
        "TRACK_CREW": 1,
        "SIGNAL_CREW": 1,
        "OHE_CREW": 1,
    }
    assert context.power_windows["EHDN_SEC06"] == ()
    assert optimized_response["planning_context"]["resource_context_applied"] is True
    assert optimized_response["planning_context"]["resource_provenance"] == "TEST_FIXTURE"


def test_reoptimize_is_explicitly_not_implemented() -> None:
    response = client.post(
        "/api/reoptimize",
        json={"cancelled_blocks": ["BLK001"], "emergency_tasks": []},
    )
    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "REOPTIMIZATION_NOT_IMPLEMENTED"
