"""Infrastructure-capacity footprints for train movements and possessions.

Legacy records without topology metadata remain conservative: every movement and
possession uses one shared capacity resource per physical planning section.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


def section_index(sections: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(section["section_id"]): section for section in sections}


def section_capacity_resources(section: Mapping[str, Any] | None, section_id: str) -> tuple[str, ...]:
    """Return configured resources, or the legacy whole-section bucket."""
    if not section:
        return (section_id,)
    configured = section.get("capacity_resources")
    if isinstance(configured, list):
        values = []
        for item in configured:
            value = item.get("capacity_resource_id") if isinstance(item, Mapping) else item
            if isinstance(value, str) and value:
                values.append(value)
        if values:
            return tuple(dict.fromkeys(values))
    values = section.get("capacity_resource_ids")
    if isinstance(values, list) and all(isinstance(value, str) and value for value in values):
        return tuple(dict.fromkeys(values))
    return (section_id,)


def task_section_ids(task: Mapping[str, Any]) -> tuple[str, ...]:
    footprint = task.get("possession_footprint")
    values = footprint.get("section_ids") if isinstance(footprint, Mapping) else None
    if values is None:
        values = task.get("section_ids")
    if values is None:
        values = [task["section_id"]]
    if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
        raise ValueError("Possession section_ids must be a non-empty string list.")
    result = tuple(dict.fromkeys(values))
    if task["section_id"] not in result:
        raise ValueError("The legacy section_id must be included in section_ids.")
    return result


def _explicit_resources(record: Mapping[str, Any]) -> list[str] | None:
    footprint = record.get("possession_footprint")
    values = footprint.get("capacity_resource_ids") if isinstance(footprint, Mapping) else None
    if values is None:
        values = record.get("capacity_resource_ids")
    if values is None:
        return None
    if not isinstance(values, list) or not values or not all(isinstance(value, str) and value for value in values):
        raise ValueError("capacity_resource_ids must be a non-empty string list.")
    return list(dict.fromkeys(values))


def task_capacity_resources(task: Mapping[str, Any], sections: Mapping[str, Mapping[str, Any]]) -> tuple[str, ...]:
    explicit = _explicit_resources(task)
    if explicit is not None:
        return tuple(explicit)
    resources = []
    for section_id in task_section_ids(task):
        resources.extend(section_capacity_resources(sections.get(section_id), section_id))
    return tuple(dict.fromkeys(resources))


def movement_capacity_resources(
    movement: Mapping[str, Any], sections: Mapping[str, Mapping[str, Any]]
) -> tuple[str, ...]:
    explicit = _explicit_resources(movement)
    if explicit is not None:
        return tuple(explicit)
    section_id = movement["section_id"]
    section = sections.get(section_id)
    if section:
        track_id = movement.get("track_id")
        configured = section.get("capacity_resources")
        if track_id and isinstance(configured, list):
            matches = [
                item.get("capacity_resource_id")
                for item in configured
                if isinstance(item, Mapping) and item.get("track_id") == track_id
            ]
            if matches:
                return tuple(matches)
        mapping = section.get("direction_capacity_mapping")
        direction = movement.get("direction")
        if direction and isinstance(mapping, Mapping) and mapping.get(direction):
            return (str(mapping[direction]),)
    # Direction never implies a physical track. Without an explicit mapping all
    # configured resources are protected conservatively.
    return section_capacity_resources(section, section_id)


def footprint_id(resources: Iterable[str]) -> str:
    return "CAP:" + "+".join(sorted(dict.fromkeys(resources)))


def track_ids_for_resources(
    sections: Iterable[Mapping[str, Any]], resources: Iterable[str]
) -> tuple[str, ...]:
    required = set(resources)
    tracks = []
    for section in sections:
        for item in section.get("capacity_resources", []):
            if (
                isinstance(item, Mapping)
                and item.get("capacity_resource_id") in required
                and isinstance(item.get("track_id"), str)
                and item["track_id"]
            ):
                tracks.append(item["track_id"])
    return tuple(dict.fromkeys(tracks))


def normalize_tasks(
    tasks: Iterable[Mapping[str, Any]], sections: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    by_section = section_index(sections)
    normalized = []
    for source in tasks:
        task = deepcopy(dict(source))
        section_ids = task_section_ids(task)
        missing = [section_id for section_id in section_ids if section_id not in by_section]
        if by_section and missing:
            raise ValueError(f"Task {task.get('task_id')!r} references unknown sections: {missing}.")
        resources = task_capacity_resources(task, by_section)
        task["_section_ids"] = section_ids
        task["_capacity_resource_ids"] = resources
        task["_footprint_id"] = footprint_id(resources)
        task["_rich_footprint"] = bool(
            task.get("section_ids")
            or task.get("capacity_resource_ids")
            or task.get("possession_footprint")
            or any(
                by_section.get(section_id, {}).get("capacity_resources")
                or by_section.get(section_id, {}).get("capacity_resource_ids")
                for section_id in section_ids
            )
        )
        normalized.append(task)
    return normalized


def footprints_overlap(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    return bool(
        set(first.get("_capacity_resource_ids", (first["section_id"],)))
        & set(second.get("_capacity_resource_ids", (second["section_id"],)))
    )
