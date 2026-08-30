from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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

class TrainOccupancy(BaseModel):
    train_id: str
    section_id: str
    entry_time: str
    exit_time: str

class ScheduledBlock(BaseModel):
    block_id: str
    section_id: str
    start_time: str
    end_time: str
    tasks: List[str]
    integrated: bool
    affected_trains: List[str] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)

class OptimizeMetrics(BaseModel):
    baseline_block_hours: float
    optimized_block_hours: float
    baseline_affected_trains: int
    optimized_affected_trains: int
    integrated_blocks: int

class OptimizeRequest(BaseModel):
    profile: Optional[str] = "Availability First"
    corridor_id: Optional[str] = None
    horizon_hours: Optional[int] = 24

class ReoptimizeRequest(BaseModel):
    cancelled_blocks: Optional[List[str]] = Field(default_factory=list)
    emergency_tasks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    delay_minutes: Optional[int] = 0