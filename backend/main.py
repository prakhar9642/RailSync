import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
def run_optimization(profile: str = "Availability First"):
    data = get_mock_data()
    block = data.get("example_optimized_block")
    blocks_list = [block] if block else []
    return {
        "status": "success",
        "profile": profile,
        "blocks": blocks_list,
        "unscheduled_tasks": [],
        "baseline_block_hours": None,
        "optimized_block_hours": None,
        "baseline_affected_trains": None,
        "optimized_affected_trains": None,
        "integrated_blocks": len(blocks_list) if (block and block.get("integrated")) else 0
    }

@app.post("/api/reoptimize")
def run_reoptimization(payload: Optional[Dict[str, Any]] = None):
    data = get_mock_data()
    block = data.get("example_optimized_block")
    blocks_list = [block] if block else []
    return {
        "status": "success",
        "message": "Re-optimization triggered",
        "blocks": blocks_list,
        "unscheduled_tasks": [],
        "baseline_block_hours": None,
        "optimized_block_hours": None,
        "baseline_affected_trains": None,
        "optimized_affected_trains": None,
        "integrated_blocks": len(blocks_list) if (block and block.get("integrated")) else 0
    }