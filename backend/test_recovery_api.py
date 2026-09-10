from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend import recovery_service
from data import load_territory
from optimizer.recovery import validate_current_plan
from ml import inference

client = TestClient(app)
TERRITORY = "eastern_hdn_test_fixture"


@pytest.fixture(scope="module")
def base_plan():
    response = client.post("/api/optimize",json={"territory_id":TERRITORY})
    assert response.status_code == 200
    return response.json()


def payload(base,delay=10):
    return dict(territory_id=TERRITORY,horizon_start=base["planning_context"]["horizon_start"],
                horizon_end=base["planning_context"]["horizon_end"],
                current_plan=dict(blocks=deepcopy(base["blocks"]),unscheduled_tasks=base["unscheduled_tasks"]),
                disruption=dict(type="TRAIN_DELAY",train_id="EHDN_TR103",delay_minutes=delay))


def test_real_recovery_preserves_base_and_has_factual_metrics(base_plan):
    request = payload(base_plan)
    original = deepcopy(request)
    response = client.post("/api/reoptimize",json=request)
    assert response.status_code == 200, response.text
    result = response.json()
    assert request == original
    assert result["base_plan"] == request["current_plan"]
    recovered = result["recovered_plan"]
    assert recovered["status"] == "success"
    assert recovered["proof_state"] == "FULLY_OPTIMAL"
    changes = result["block_changes"]
    for name in ("retained","shifted","cancelled","new"):
        assert result["recovery_metrics"][f"{name}_blocks"] == sum(c["state"] == name.upper() for c in changes)
    assert result["invalidated_blocks"]
    assert result["recovery_metrics"]["retained_blocks"] > 0
    assert result["recovery_metrics"]["shifted_blocks"] > 0
    territory = load_territory(TERRITORY)
    data = territory.as_optimizer_input()
    data["train_occupancy"] = result["train_occupancy"]
    validate_current_plan(data,recovered["blocks"],request["horizon_start"],request["horizon_end"],territory.resource_context)
    assert result["recovery_metrics"]["unscheduled_tasks_after_disruption"] == len(recovered["unscheduled_tasks"])
    assert result["recovery_metrics"]["total_shift_minutes"] == sum(c["shift_minutes"] or 0 for c in result["task_changes"])


def test_zero_delay_has_no_invented_changes(base_plan):
    result = client.post("/api/reoptimize",json=payload(base_plan,0)).json()
    assert result["recovered_plan"]["blocks"] == base_plan["blocks"]
    assert result["recovery_metrics"]["retained_blocks"] == len(base_plan["blocks"])
    assert result["recovery_metrics"]["total_shift_minutes"] == 0


def test_disruption_can_remove_work_without_calling_it_saved_closure(base_plan):
    request=payload(base_plan,25)
    request["disruption"]["train_id"]="EHDN_TR105"
    result=client.post("/api/reoptimize",json=request).json()
    assert result["newly_unscheduled_task_ids"] == ["EHDN_ENG002"]
    assert result["recovery_metrics"]["cancelled_blocks"] == 1
    assert result["recovery_metrics"]["unscheduled_tasks_after_disruption"] == 2
    assert "closure_saved_minutes" not in result


@pytest.mark.parametrize("territory,status",[("missing",404),("eastern_hdn",409)])
def test_invalid_territory(base_plan,territory,status):
    request=payload(base_plan);request["territory_id"]=territory
    assert client.post("/api/reoptimize",json=request).status_code == status


@pytest.mark.parametrize("disruption",[{"type":"NOPE","train_id":"EHDN_TR105","delay_minutes":10},
    {"type":"TRAIN_DELAY","train_id":"missing","delay_minutes":10},
    {"type":"TRAIN_DELAY","train_id":"EHDN_TR105","delay_minutes":-1},
    {"type":"TRAIN_DELAY","train_id":"EHDN_TR105","delay_minutes":True}])
def test_invalid_disruption(base_plan,disruption):
    request=payload(base_plan);request["disruption"]=disruption
    assert client.post("/api/reoptimize",json=request).status_code == 422


def test_invalid_current_plan_and_horizon(base_plan):
    request=payload(base_plan)
    request["current_plan"]["blocks"][0]["tasks"]=["FAKE"]
    assert client.post("/api/reoptimize",json=request).status_code == 422
    request=payload(base_plan);request["horizon_end"]="2026-09-02T06:00:00"
    assert client.post("/api/reoptimize",json=request).status_code == 422
    request=payload(base_plan);request["current_plan"]["blocks"][0]["start_time"]="2026-09-01T00:00:00"
    assert client.post("/api/reoptimize",json=request).status_code == 422


def test_bounded_solver_response_remains_bounded(base_plan,monkeypatch):
    import optimizer.possessions as possessions
    from ortools.sat.python import cp_model
    original = possessions._make_stage_solver
    class BoundedSolver:
        def __init__(self,solver): self.solver=solver
        def Solve(self,model):
            status=self.solver.Solve(model)
            assert status == cp_model.OPTIMAL
            return cp_model.FEASIBLE
        def Value(self,expression): return self.solver.Value(expression)
        def StatusName(self,status): return self.solver.StatusName(status)
    monkeypatch.setattr(possessions,"_make_stage_solver",lambda *args: BoundedSolver(original(*args)))
    response=client.post("/api/reoptimize",json=payload(base_plan))
    assert response.status_code == 200
    assert response.json()["recovered_plan"]["proof_state"] == "FEASIBLE_BOUNDED"


def test_solver_failure_is_not_fake_recovery(base_plan,monkeypatch):
    def fail(*args,**kwargs): raise RuntimeError("Recovery has no usable incumbent")
    monkeypatch.setattr(recovery_service,"recover_schedule",fail)
    response=client.post("/api/reoptimize",json=payload(base_plan))
    assert response.status_code == 503
    assert "recovered_plan" not in response.json()


def test_experimental_ml_status_binding_and_static_fallback(base_plan,monkeypatch):
    status=client.get("/api/ml/status").json()
    assert status["model_available"]
    profile=status["profiles"][0]
    binding=dict(train_id="EHDN_TR105",section_id="EHDN_SEC01",historical_train_id=profile["train_id"],historical_station_id=profile["station_code"])
    request=payload(base_plan);request.update(risk_mode="ML_ASSISTED",risk_profiles=[binding])
    response=client.post("/api/reoptimize",json=request)
    assert response.status_code == 200, response.text
    assert response.json()["risk"]["predictions"][0]["model_available"]
    assert response.json()["risk"]["effective_mode"] == "ML_ASSISTED"
    monkeypatch.setattr(inference,"load_model",lambda:None)
    fallback=client.post("/api/optimize",json=dict(territory_id=TERRITORY,risk_mode="ML_ASSISTED",risk_profiles=[binding])).json()
    assert fallback["blocks"] == base_plan["blocks"]
    assert fallback["risk"]["effective_mode"] == "STATIC"
