"""In-memory prototype plan lifecycle and operational read models."""

from __future__ import annotations

import csv
import base64
import io
import re
import zipfile
from xml.etree import ElementTree
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


PLAN_STATES = ("DRAFT", "REVIEWED", "APPROVED", "PUBLISHED")
BLOCK_TRANSITIONS = {
    "DRAFT": {"FROZEN", "CANCELLED"},
    "FROZEN": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}
_plans: dict[str, dict[str, Any]] = {}
_territory_versions: dict[str, int] = {}


def register_plan(territory_id: str, payload: dict[str, Any], parent_plan_id: str | None = None):
    version = _territory_versions.get(territory_id, 0) + 1
    _territory_versions[territory_id] = version
    plan_id = f"{territory_id}-v{version}"
    identity = {
        "plan_id": plan_id,
        "version": version,
        "state": "DRAFT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "parent_plan_id": parent_plan_id,
    }
    _plans[plan_id] = {
        "identity": identity,
        "territory_id": territory_id,
        "blocks": deepcopy(payload.get("blocks", [])),
        "unscheduled_tasks": list(payload.get("unscheduled_tasks", [])),
        "metrics": deepcopy(payload.get("metrics", {})),
        "events": [{"state": "DRAFT", "at": identity["created_at"], "actor": "planner"}],
    }
    return identity


def transition_plan(plan_id: str, target_state: str, actor: str = "planner", note: str = ""):
    if plan_id not in _plans:
        raise ValueError(f"Unknown plan ID: {plan_id}")
    if target_state not in PLAN_STATES:
        raise ValueError(f"Unknown plan state: {target_state}")
    plan = _plans[plan_id]
    current = plan["identity"]["state"]
    current_index, target_index = PLAN_STATES.index(current), PLAN_STATES.index(target_state)
    if target_index != current_index + 1:
        raise ValueError(f"Plan transition must advance one step from {current}.")
    timestamp = datetime.now(timezone.utc).isoformat()
    plan["identity"]["state"] = target_state
    plan["events"].append({"state": target_state, "at": timestamp, "actor": actor, "note": note})
    return deepcopy(plan)


def history(territory_id: str | None = None):
    values = [item for item in _plans.values() if territory_id is None or item["territory_id"] == territory_id]
    return sorted((deepcopy(item) for item in values), key=lambda item: item["identity"]["created_at"], reverse=True)


def transition_block(plan_id: str, block_id: str, target_status: str, actor: str = "planner"):
    if plan_id not in _plans:
        raise ValueError(f"Unknown plan ID: {plan_id}")
    plan = _plans[plan_id]
    block = next((item for item in plan["blocks"] if item["block_id"] == block_id), None)
    if block is None:
        raise ValueError(f"Unknown block ID: {block_id}")
    current = block.get("status", "DRAFT")
    if target_status not in BLOCK_TRANSITIONS.get(current, set()):
        raise ValueError(f"Block transition {current} → {target_status} is not allowed.")
    block["status"] = target_status
    plan["events"].append({
        "block_id": block_id,
        "status": target_status,
        "at": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
    })
    return deepcopy(block)


def rolling_view(territory, plan: dict[str, Any] | None = None):
    tasks = territory.maintenance_tasks
    blocks = (plan or {}).get("blocks", [])
    scheduled = {task_id for block in blocks for task_id in block["tasks"]}
    departments = sorted({task["department"] for task in tasks})
    month = [{
        "period": territory.manifest.planning_horizon["start_time"][:7],
        "demand_count": len(tasks),
        "critical_demand_count": sum(task["criticality"] >= 9 for task in tasks),
        "departments": departments,
        "planning_state": "DEMAND_REVIEW",
    }]
    week = [{
        "period": "operating-week",
        "candidate_task_ids": [task["task_id"] for task in tasks],
        "resource_pools": sorted(territory.resource_context.crew_capacities) if territory.resource_context else [],
        "planning_state": "COORDINATION",
    }]
    day = [{
        "date": territory.manifest.planning_horizon["start_time"][:10],
        "scheduled_task_ids": sorted(scheduled),
        "unscheduled_task_ids": sorted({task["task_id"] for task in tasks} - scheduled),
        "blocks": blocks,
        "planning_state": "SOLVER_PLAN" if plan else "READY_TO_SOLVE",
    }]
    return {"monthly": month, "weekly": week, "day_of": day}


def resource_view(territory):
    context = territory.resource_context
    if context is None:
        return {"provenance": None, "crew": [], "machines": [], "power_windows": {}}
    def rows(capacities, calendars):
        return [{
            "resource_id": resource_id,
            "capacity": capacity,
            "availability": [vars(window) for window in calendars.get(resource_id, ())],
        } for resource_id, capacity in sorted(capacities.items())]
    return {
        "provenance": territory.resource_provenance,
        "crew": rows(context.crew_capacities, context.crew_windows),
        "machines": rows(context.machine_capacities, context.machine_windows),
        "power_windows": {key: [vars(window) for window in value] for key, value in context.power_windows.items()},
    }


def alerts(territory, plan: dict[str, Any] | None = None):
    scheduled = {task_id for block in (plan or {}).get("blocks", []) for task_id in block["tasks"]}
    items = []
    for task in territory.maintenance_tasks:
        if task["criticality"] >= 9 and task["task_id"] not in scheduled:
            items.append({"severity": "HIGH", "code": "CRITICAL_TASK_PENDING", "task_id": task["task_id"], "message": f"{task['task_type']} is not yet scheduled."})
        elif task["overdue_days"] > 14:
            items.append({"severity": "MEDIUM", "code": "OVERDUE_MAINTENANCE", "task_id": task["task_id"], "message": f"Task is overdue by {task['overdue_days']} days."})
    return items


def blocks_csv(blocks):
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["block_id", "section_ids", "capacity_resources", "start_time", "end_time", "tasks", "integrated", "affected_trains"])
    for block in blocks:
        writer.writerow([
            block["block_id"],
            "|".join(block.get("section_ids") or [block["section_id"]]),
            "|".join(block.get("capacity_resource_ids", [])),
            block["start_time"], block["end_time"], "|".join(block["tasks"]),
            block["integrated"], "|".join(block.get("affected_trains", [])),
        ])
    return output.getvalue()


def parse_xlsx_records(encoded: str) -> list[dict[str, Any]]:
    """Read the first XLSX worksheet with the standard library; never extracts files."""
    if not isinstance(encoded, str) or len(encoded) > 7_000_000:
        raise ValueError("Excel workbook payload is missing or exceeds the 5 MB prototype limit.")
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Excel workbook payload is not valid base64.") from error
    if len(payload) > 5_000_000:
        raise ValueError("Excel workbook exceeds the 5 MB prototype limit.")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as workbook:
            names = set(workbook.namelist())
            if "xl/worksheets/sheet1.xml" not in names:
                raise ValueError("Excel workbook has no first worksheet.")
            shared = []
            if "xl/sharedStrings.xml" in names:
                root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
                shared = ["".join(node.itertext()) for node in root.findall("{*}si")]
            sheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError) as error:
        raise ValueError("Excel workbook is not a readable XLSX file.") from error

    rows = []
    for row in sheet.findall(".//{*}sheetData/{*}row"):
        values: dict[int, Any] = {}
        for cell in row.findall("{*}c"):
            reference = cell.get("r", "")
            letters = re.match(r"[A-Z]+", reference)
            if not letters:
                continue
            column = 0
            for letter in letters.group(0):
                column = column * 26 + ord(letter) - 64
            value_node = cell.find("{*}v")
            value = value_node.text if value_node is not None else "".join(cell.itertext())
            if cell.get("t") == "s" and value:
                value = shared[int(value)]
            values[column - 1] = value
        if values:
            rows.append([values.get(index, "") for index in range(max(values) + 1)])
    if not rows:
        return []
    headers = [str(value).strip() for value in rows[0]]
    numeric = {"duration_minutes", "criticality", "urgency", "overdue_days"}
    records = []
    for row in rows[1:]:
        record = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            value = row[index] if index < len(row) else ""
            if header in numeric and value != "":
                value = int(float(value))
            record[header] = value
        if any(value != "" for value in record.values()):
            records.append(record)
    return records
