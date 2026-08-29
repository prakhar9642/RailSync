import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="RailSync Optimization API", version="1.0.0")

# Enable CORS for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# Canonical Pydantic Schemas (Roadmap Section 7)
# ----------------------------------------------------
class MaintenanceTask(BaseModel):
    task_id: str
    department: str
    section_id: str
    task_type: str
    duration_minutes: int
    criticality: int
    urgency: int
    overdue_days: int
    deadline: str
    requires_power_block: bool
    crew_type: str
    compatibility_group: str
    asset_importance: Optional[int] = None

class TrainOccupancy(BaseModel):
    train_id: str
    section_id: str
    entry_time: str
    exit_time: str
    train_type: Optional[str] = "PASSENGER"
    priority_weight: Optional[int] = 1

class ScheduledBlock(BaseModel):
    block_id: str
    section_id: str
    start_time: str
    end_time: str
    tasks: List[str]
    integrated: bool
    affected_trains: List[str]
    explanation: List[str]

# ----------------------------------------------------
# Helper to read mock-data.json
# ----------------------------------------------------
def get_mock_data() -> Dict[str, Any]:
    # Look in the same folder as main.py first
    json_path = Path(__file__).parent / "mock-data.json"
    if not json_path.exists():
        # Fallback to root or parent folder if needed
        json_path = Path(__file__).parent.parent / "mock-data.json"
    
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ----------------------------------------------------
# API Endpoints
# ----------------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "RailSync Backend"}

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
    block = data.get("example_optimized_block", {})
    return {"blocks": [block] if block else []}

@app.post("/api/optimize")
def run_optimization(profile: str = "Availability First"):
    data = get_mock_data()
    block = data.get("example_optimized_block", {})
    return {
        "status": "OPTIMAL",
        "profile": profile,
        "metrics": {
            "baseline_closure_hours": 3.0,
            "optimized_closure_hours": 2.0,
            "closure_reduction_pct": 33.3,
            "integrated_blocks_count": 1,
            "trains_affected": 0
        },
        "scheduled_blocks": [block] if block else []
    }