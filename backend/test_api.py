from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_get_dashboard():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "tasks_count" in data
    assert "trains_count" in data

def test_get_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert "tasks" in response.json()
    assert isinstance(response.json()["tasks"], list)

def test_get_trains():
    response = client.get("/api/trains")
    assert response.status_code == 200
    assert "trains" in response.json()
    assert isinstance(response.json()["trains"], list)

def test_optimize_endpoint_schema():
    payload = {
        "profile": "Availability First",
        "corridor_id": "SEC01",
        "horizon_hours": 24
    }
    response = client.post("/api/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "blocks" in data
    assert "metrics" in data
    
    # Verify all contract metrics exist
    metrics = data["metrics"]
    expected_keys = [
        "baseline_block_hours",
        "optimized_block_hours",
        "baseline_affected_trains",
        "optimized_affected_trains",
        "integrated_blocks"
    ]
    for key in expected_keys:
        assert key in metrics

def test_reoptimize_endpoint():
    payload = {
        "cancelled_blocks": ["BLK001"],
        "emergency_tasks": [],
        "delay_minutes": 15
    }
    response = client.post("/api/reoptimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["blocks"]) == 0