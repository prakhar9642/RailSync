import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from schemas import OptimizeRequest, ReoptimizeRequest

app = FastAPI(title="RailSync Optimization API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_mock_data() -> Dict[str, Any]:
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parent
    
    paths_to_check = [
        repo_root / "docs" / "mock-data.json",
        current_dir / "mock-data.json",
        repo_root / "mock-data.json"
    ]
    
    for path in paths_to_check:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

# ----------------- API Endpoints -----------------

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "RailSync Backend"}

@app.get("/api/dashboard")
def get_dashboard():
    data = get_mock_data()
    return {
        "status": "success",
        "tasks_count": len(data.get("maintenance_tasks", [])),
        "trains_count": len(data.get("train_occupancy", [])),
        "recent_alerts": [],
        "system_status": "operational"
    }

@app.get("/api/tasks")
def get_tasks():
    data = get_mock_data()
    return {"tasks": data.get("maintenance_tasks", [])}

@app.get("/api/trains")
def get_trains():
    data = get_mock_data()
    return {"trains": data.get("train_occupancy", [])}

@app.get("/api/blocks")
def get_blocks():
    data = get_mock_data()
    block = data.get("example_optimized_block")
    return {"blocks": [block] if block else []}

@app.post("/api/optimize")
def run_optimization(request: Optional[OptimizeRequest] = None):
    data = get_mock_data()
    block = data.get("example_optimized_block")
    blocks_list = [block] if block else []
    
    total_task_minutes = sum(t.get("duration_minutes", 0) for t in data.get("maintenance_tasks", []))
    baseline_hours = round(total_task_minutes / 60.0, 2)
    
    return {
        "status": "success",
        "blocks": blocks_list,
        "unscheduled_tasks": [],
        "metrics": {
            "baseline_block_hours": baseline_hours,
            "optimized_block_hours": 2.0 if blocks_list else 0.0,
            "baseline_affected_trains": len(data.get("train_occupancy", [])),
            "optimized_affected_trains": sum(len(b.get("affected_trains", [])) for b in blocks_list),
            "integrated_blocks": len([b for b in blocks_list if b.get("integrated")])
        }
    }

@app.post("/api/reoptimize")
def run_reoptimization(request: Optional[ReoptimizeRequest] = None):
    data = get_mock_data()
    req = request or ReoptimizeRequest()
    
    block = data.get("example_optimized_block")
    current_blocks = [block] if block else []
    
    # Remove cancelled blocks if specified
    active_blocks = [b for b in current_blocks if b.get("block_id") not in req.cancelled_blocks]
    
    # Collect unscheduled emergency tasks
    unscheduled = [t.get("task_id", "EMERGENCY_TASK") for t in req.emergency_tasks]
    
    return {
        "status": "success",
        "message": f"Re-optimization complete. {len(req.cancelled_blocks)} blocks removed.",
        "blocks": active_blocks,
        "unscheduled_tasks": unscheduled,
        "metrics": {
            "baseline_block_hours": 4.5,
            "optimized_block_hours": round(len(active_blocks) * 2.0, 2),
            "baseline_affected_trains": len(data.get("train_occupancy", [])),
            "optimized_affected_trains": 0,
            "integrated_blocks": len([b for b in active_blocks if b.get("integrated")])
        }
    }