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
    territory_id: Optional[str] = None
    corridor_id: Optional[str] = None
    horizon_hours: Optional[int] = Field(default=None, gt=0)

class ReoptimizeRequest(BaseModel):
    cancelled_blocks: Optional[List[str]] = Field(default_factory=list)
    emergency_tasks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    delay_minutes: Optional[int] = 0


class ComparisonSummary(BaseModel):
    baseline_label: str
    same_task_set: bool
    closure_saved_minutes: Optional[int] = None
    closure_reduction_percent: Optional[float] = None
    baseline_proof_state: str
    optimized_proof_state: str


class PlanningContext(BaseModel):
    territory_id: str
    display_name: str
    territory_status: str
    provenance: List[str]
    horizon_start: str
    horizon_end: str
    resource_context_applied: bool
    resource_provenance: Optional[str] = None
    solver_time_limit_seconds_per_plan: float


class OptimizeResponse(BaseModel):
    status: str
    blocks: List[ScheduledBlock]
    unscheduled_tasks: List[str]
    metrics: OptimizeMetrics
    proof_state: str
    comparison_proof_state: str
    comparison: ComparisonSummary
    planning_context: PlanningContext
