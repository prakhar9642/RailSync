# RailSync Shared Contracts

Do not rename shared fields or endpoints without team discussion.

## Maintenance Task

```json
{
  "task_id": "ENG017",
  "department": "ENGINEERING",
  "section_id": "SEC03",
  "task_type": "Rail Weld Inspection",
  "duration_minutes": 120,
  "criticality": 9,
  "urgency": 8,
  "overdue_days": 12,
  "deadline": "2026-09-02T05:00:00",
  "requires_power_block": false,
  "crew_type": "TRACK_CREW",
  "compatibility_group": "LINE_BLOCK_A"
}
```

## Train Section Occupancy

```json
{
  "train_id": "TR104",
  "section_id": "SEC03",
  "entry_time": "2026-09-01T01:20:00",
  "exit_time": "2026-09-01T01:37:00"
}
```

## Scheduled Block

```json
{
  "block_id": "BLK001",
  "section_id": "SEC03",
  "start_time": "2026-09-01T02:00:00",
  "end_time": "2026-09-01T04:00:00",
  "tasks": ["ENG017", "SNT004"],
  "integrated": true,
  "affected_trains": [],
  "explanation": []
}
```

## API Endpoints

- GET /health
- GET /api/tasks
- GET /api/trains
- GET /api/dashboard
- POST /api/optimize
- POST /api/reoptimize

## Optimize Response

```json
{
  "status": "success",
  "blocks": [],
  "unscheduled_tasks": [],
  "metrics": {
    "baseline_block_hours": 0,
    "optimized_block_hours": 0,
    "baseline_affected_trains": 0,
    "optimized_affected_trains": 0,
    "integrated_blocks": 0
  }
}
```