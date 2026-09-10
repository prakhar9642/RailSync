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
PUBLIC_DEMO_ID = "saktigarh_memari_public_demo"


def comparison_side(
    *,
    proof_state: str = "FULLY_OPTIMAL",
    scheduled_tasks: list[str] | None = None,
    possession_minutes: int = 0,
) -> dict:
    scheduled_tasks = scheduled_tasks or []
    return {
        "scheduled_tasks": scheduled_tasks,
        "unscheduled_tasks": [],
        "scheduled_task_count": len(scheduled_tasks),
        "productive_minutes": 0,
        "possession_minutes": possession_minutes,
        "block_count": 0,
        "integrated_blocks": 0,
        "criticality_served": 0,
        "urgency_served": 0,
        "overdue_days_served": 0,
        "maintenance_delivery_efficiency": None,
        "coordination_gain_minutes": 0,
        "boundary_slacks": [],
        "minimum_boundary_slack_minutes": 0,
        "total_boundary_slack_minutes": 0,
        "task_windows": [],
        "pair_checks": [],
        "outcomes": {},
        "proof_state": proof_state,
        "plan": {
            "status": "success",
            "blocks": [],
            "unscheduled_tasks": [],
            "metrics": {"optimized_affected_trains": 0},
        },
    }


def comparison_result(
    *,
    proof_state: str = "FULLY_OPTIMAL",
    baseline_tasks: list[str] | None = None,
    optimized_tasks: list[str] | None = None,
    same_task_set: bool = True,
) -> dict:
    return {
        "baseline": comparison_side(
            proof_state=proof_state, scheduled_tasks=baseline_tasks
        ),
        "optimized": comparison_side(
            proof_state=proof_state, scheduled_tasks=optimized_tasks
        ),
        "comparison_proof_state": proof_state,
        "comparison": {
            "same_task_set": same_task_set,
            "closure_saved_minutes": 99,
            "closure_reduction_percent": 50.0,
        },
    }


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


def test_territory_discovery_exposes_both_runnable_demos() -> None:
    response = client.get("/api/territories")
    assert response.status_code == 200
    by_id = {
        item["territory_id"]: item for item in response.json()["territories"]
    }
    assert by_id[FIXTURE_ID]["planning_ready"] is True
    assert by_id[PUBLIC_DEMO_ID]["planning_ready"] is True
    assert by_id[PUBLIC_DEMO_ID]["provenance"] == [
        "PUBLIC_TIMETABLE_DERIVED", "SYNTHETIC_PROTOTYPE"
    ]
    assert by_id["eastern_hdn"]["planning_ready"] is False


def test_public_timetable_demo_optimizes_through_public_api() -> None:
    response = client.post("/api/optimize", json={"territory_id": PUBLIC_DEMO_ID})
    assert response.status_code == 200
    result = response.json()
    assert result["planning_context"]["territory_id"] == PUBLIC_DEMO_ID
    assert result["unscheduled_tasks"] == []
    assert result["comparison"]["same_task_set"] is True
    assert result["comparison"]["closure_saved_minutes"] == 50
    assert result["metrics"]["optimized_block_hours"] == 1.917
    assert all(block["affected_trains"] == [] for block in result["blocks"])


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


def test_analysis_exposes_real_comparison_metrics_and_fair_savings(
    optimized_response: dict,
) -> None:
    analysis = optimized_response["analysis"]
    assert analysis["baseline"]["metrics"] == {
        "scheduled_task_count": 8,
        "unscheduled_task_count": 1,
        "productive_minutes": 285,
        "possession_minutes": 405,
        "block_count": 8,
        "integrated_blocks": 0,
        "criticality_served": 61,
        "urgency_served": 60,
        "overdue_days_served": 72,
        "maintenance_delivery_efficiency": pytest.approx(285 / 405),
        "minimum_boundary_slack_minutes": 0,
        "total_boundary_slack_minutes": 47,
    }
    assert analysis["railsync"]["metrics"]["possession_minutes"] == 300
    assert analysis["railsync"]["metrics"]["integrated_blocks"] == 2
    assert analysis["fairness"]["same_task_set"] is True
    assert analysis["fairness"]["possession_saved_minutes"] == 105
    assert analysis["fairness"]["possession_reduction_percent"] == pytest.approx(
        105 / 405 * 100
    )


def test_different_task_sets_suppress_pure_savings(monkeypatch) -> None:
    compared = comparison_result(
        baseline_tasks=["EHDN_ENG001"],
        optimized_tasks=["EHDN_ENG002"],
        same_task_set=False,
    )
    monkeypatch.setattr(planning_service, "compare_plans", lambda *args, **kwargs: compared)
    response = client.post("/api/optimize", json={"territory_id": FIXTURE_ID})
    assert response.status_code == 200
    fairness = response.json()["analysis"]["fairness"]
    assert fairness["same_task_set"] is False
    assert fairness["possession_saved_minutes"] is None
    assert fairness["possession_reduction_percent"] is None
    assert fairness["statement"] == (
        "Pure possession savings are not reported because the planners delivered "
        "different maintenance task sets."
    )


def test_integrated_and_unscheduled_explanations_are_factual(
    optimized_response: dict,
) -> None:
    analysis = optimized_response["analysis"]
    integrated = analysis["integrated_blocks"][0]
    assert integrated["task_ids"] == ["EHDN_ENG001", "EHDN_SNT001"]
    assert integrated["departments"] == ["ENGINEERING", "S&T"]
    assert integrated["coordination_gain_minutes"] == 60
    block = next(
        item for item in analysis["block_diagnostics"] if item["block_id"] == "BLK003"
    )
    assert block["integration"]["compatibility_status"] == "CONDITIONAL"
    assert block["integration"]["reason_codes"] == ["COMPATIBLE_GROUP"]
    unscheduled = analysis["unscheduled_tasks"][0]
    assert unscheduled["task"]["task_id"] == "EHDN_TRD003"
    assert unscheduled["task"]["deadline_check"] == "NOT_EVALUATED"
    assert "POWER_WINDOW_UNAVAILABLE" in unscheduled["reason_codes"]
    assert all(
        window["resource_checks"]["power"] == "FAILED"
        for window in unscheduled["candidate_windows"]
    )


def test_unknown_resource_diagnostic_remains_unknown() -> None:
    task = load_territory(FIXTURE_ID).maintenance_tasks[0]
    result = comparison_side(scheduled_tasks=[task["task_id"]])
    result["plan"]["blocks"] = [
        {
            "block_id": "BLK001",
            "section_id": task["section_id"],
            "start_time": "2026-09-01T02:37:00",
            "end_time": "2026-09-01T03:52:00",
            "tasks": [task["task_id"]],
            "integrated": False,
            "affected_trains": [],
            "explanation": [],
        }
    ]
    result["boundary_slacks"] = [
        {
            "block_id": "BLK001",
            "window_id": "WIN_TEST",
            "before_boundary_slack_minutes": 1,
            "after_boundary_slack_minutes": 2,
            "boundary_slack_minutes": 1,
        }
    ]
    result["task_windows"] = [
        {
            "task_id": task["task_id"],
            "window_id": "WIN_TEST",
            "feasible": True,
            "reasons": [],
            "resource_checks": {
                "crew": "UNKNOWN",
                "machine": "NOT_EVALUATED",
                "power": "NOT_EVALUATED",
            },
        }
    ]
    diagnostics = planning_service._block_diagnostics([task], result)
    assert diagnostics[0]["tasks"][0]["resource_checks"]["crew"] == "UNKNOWN"


def test_bounded_feasible_proof_is_not_labeled_optimal(monkeypatch) -> None:
    bounded = comparison_result(proof_state="FEASIBLE_BOUNDED")
    monkeypatch.setattr(planning_service, "compare_plans", lambda *args, **kwargs: bounded)
    response = client.post("/api/optimize", json={"territory_id": FIXTURE_ID})
    assert response.status_code == 200
    assert response.json()["proof_state"] == "FEASIBLE_BOUNDED"
    assert response.json()["comparison_proof_state"] == "FEASIBLE_BOUNDED"
    assert response.json()["analysis"]["baseline"]["proof_state"] == "FEASIBLE_BOUNDED"
    assert response.json()["analysis"]["railsync"]["proof_state"] == "FEASIBLE_BOUNDED"
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


def test_reoptimize_rejects_legacy_request_without_current_plan() -> None:
    response = client.post(
        "/api/reoptimize",
        json={"cancelled_blocks": ["BLK001"], "emergency_tasks": []},
    )
    assert response.status_code == 422
    assert any(item["loc"] == ["body", "current_plan"] for item in response.json()["detail"])
