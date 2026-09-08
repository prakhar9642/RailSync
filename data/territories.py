"""Manifest registry and canonical territory loader."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .adapters import ADAPTERS, load_resource_context

DATA_DIR = Path(__file__).resolve().parent
CORRIDORS_DIR = DATA_DIR / "corridors"
FIXTURES_DIR = DATA_DIR / "fixtures"
MANIFEST_ROOTS = (CORRIDORS_DIR, FIXTURES_DIR)

POPULATED = "POPULATED"
PLACEHOLDER = "PLACEHOLDER"
PROVENANCE_LABELS = {
    "PUBLIC_TIMETABLE_DERIVED",
    "SYNTHETIC_PROTOTYPE",
    "SYNTHETIC_SCENARIO",
    "TEST_FIXTURE",
}

CANONICAL_FIELDS = {
    "stations": {"station_id", "station_name", "order"},
    "sections": {"section_id", "from_station", "to_station"},
    "train_occupancy": {"train_id", "section_id", "entry_time", "exit_time"},
    "maintenance_tasks": {
        "task_id",
        "department",
        "section_id",
        "task_type",
        "duration_minutes",
        "criticality",
        "urgency",
        "overdue_days",
        "deadline",
        "requires_power_block",
        "crew_type",
        "compatibility_group",
    },
}
CORE_DATASETS = {"stations", "sections", "train_occupancy"}


class TerritoryError(ValueError):
    """Base error for territory discovery and loading."""


class UnknownTerritoryError(TerritoryError):
    """Raised when no registered manifest matches a territory ID."""


class TerritoryNotPopulatedError(TerritoryError):
    """Raised when a registered placeholder has no usable data."""


@dataclass(frozen=True)
class TerritoryManifest:
    territory_id: str
    display_name: str
    description: str
    status: str
    provenance: tuple[Mapping[str, Any], ...]
    datasets: Mapping[str, Mapping[str, str]]
    scenario_references: tuple[str, ...]
    planning_horizon: Mapping[str, str] | None
    resource_context: Mapping[str, str] | None
    path: Path

    @property
    def available_datasets(self) -> tuple[str, ...]:
        return tuple(sorted(self.datasets))


@dataclass(frozen=True)
class LoadedTerritory:
    """Canonical records plus separately held ingestion metadata."""

    manifest: TerritoryManifest
    stations: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    train_occupancy: list[dict[str, Any]]
    maintenance_tasks: list[dict[str, Any]]
    resource_context: Any | None = None
    resource_provenance: str | None = None

    def as_optimizer_input(self) -> dict[str, list[dict[str, Any]]]:
        """Return only canonical data fields accepted by the existing optimizer."""
        return deepcopy(
            {
                "stations": self.stations,
                "sections": self.sections,
                "train_occupancy": self.train_occupancy,
                "maintenance_tasks": self.maintenance_tasks,
            }
        )


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise TerritoryError(f"Could not read {label} at {path}: {error}") from error
    if not isinstance(value, dict):
        raise TerritoryError(f"{label} at {path} must contain a JSON object.")
    return value


def _manifest_from_path(path: Path) -> TerritoryManifest:
    raw = _read_json_object(path, "territory manifest")
    required = {
        "territory_id",
        "display_name",
        "description",
        "status",
        "provenance",
        "datasets",
        "scenario_references",
    }
    missing = sorted(required - raw.keys())
    if missing:
        raise TerritoryError(f"Manifest {path} is missing: {', '.join(missing)}.")

    territory_id = raw["territory_id"]
    if not isinstance(territory_id, str) or not territory_id:
        raise TerritoryError(f"Manifest {path} has an invalid territory_id.")
    if territory_id != path.parent.name:
        raise TerritoryError(
            f"Manifest territory_id {territory_id!r} must match directory {path.parent.name!r}."
        )
    for field_name in ("display_name", "description"):
        if not isinstance(raw[field_name], str) or not raw[field_name].strip():
            raise TerritoryError(
                f"Manifest {territory_id!r} has an invalid {field_name}."
            )
    if raw["status"] not in {POPULATED, PLACEHOLDER}:
        raise TerritoryError(f"Manifest {territory_id!r} has an invalid status.")
    if not isinstance(raw["datasets"], dict):
        raise TerritoryError(f"Manifest {territory_id!r} datasets must be an object.")
    if not isinstance(raw["provenance"], list):
        raise TerritoryError(f"Manifest {territory_id!r} provenance must be a list.")
    if not isinstance(raw["scenario_references"], list) or not all(
        isinstance(item, str) for item in raw["scenario_references"]
    ):
        raise TerritoryError(
            f"Manifest {territory_id!r} scenario_references must be a string list."
        )

    planning_horizon = raw.get("planning_horizon")
    if planning_horizon is not None and (
        not isinstance(planning_horizon, dict)
        or not all(
            isinstance(planning_horizon.get(field), str) and planning_horizon[field]
            for field in ("start_time", "end_time")
        )
    ):
        raise TerritoryError(
            f"Manifest {territory_id!r} planning_horizon needs start_time and end_time."
        )

    resource_spec = raw.get("resource_context")
    if resource_spec is not None and (
        not isinstance(resource_spec, dict)
        or resource_spec.get("adapter") != "resource_context_json"
        or not isinstance(resource_spec.get("path"), str)
        or not resource_spec["path"]
    ):
        raise TerritoryError(f"Manifest {territory_id!r} has invalid resource_context.")

    for dataset_name, spec in raw["datasets"].items():
        if dataset_name not in CANONICAL_FIELDS:
            raise TerritoryError(
                f"Manifest {territory_id!r} declares unknown dataset {dataset_name!r}."
            )
        if not isinstance(spec, dict) or not all(
            isinstance(spec.get(key), str) and spec[key] for key in ("adapter", "path")
        ):
            raise TerritoryError(
                f"Manifest {territory_id!r} dataset {dataset_name!r} needs adapter and path."
            )
        if spec["adapter"] not in ADAPTERS:
            raise TerritoryError(
                f"Manifest {territory_id!r} uses unknown adapter {spec['adapter']!r}."
            )

    for record in raw["provenance"]:
        if not isinstance(record, dict) or record.get("label") not in PROVENANCE_LABELS:
            raise TerritoryError(f"Manifest {territory_id!r} has invalid provenance.")
        provenance_datasets = record.get("datasets")
        if not isinstance(provenance_datasets, list) or not all(
            isinstance(item, str) and item in raw["datasets"]
            for item in provenance_datasets
        ):
            raise TerritoryError(
                f"Manifest {territory_id!r} provenance references invalid datasets."
            )
        if not isinstance(record.get("description"), str) or not record["description"].strip():
            raise TerritoryError(
                f"Manifest {territory_id!r} provenance needs a description."
            )

    if raw["status"] == PLACEHOLDER and (
        raw["datasets"] or raw["scenario_references"] or resource_spec
    ):
        raise TerritoryError(
            f"Placeholder territory {territory_id!r} cannot declare datasets or scenarios."
        )
    if raw["status"] == POPULATED:
        missing_core = sorted(CORE_DATASETS - raw["datasets"].keys())
        if missing_core:
            raise TerritoryError(
                f"Populated territory {territory_id!r} is missing: {', '.join(missing_core)}."
            )

    return TerritoryManifest(
        territory_id=territory_id,
        display_name=raw["display_name"],
        description=raw["description"],
        status=raw["status"],
        provenance=tuple(raw["provenance"]),
        datasets=raw["datasets"],
        scenario_references=tuple(raw["scenario_references"]),
        planning_horizon=planning_horizon,
        resource_context=resource_spec,
        path=path,
    )


def _registry() -> dict[str, Path]:
    registry: dict[str, Path] = {}
    for root in MANIFEST_ROOTS:
        for path in sorted(root.glob("*/manifest.json")):
            manifest = _manifest_from_path(path)
            if manifest.territory_id in registry:
                raise TerritoryError(f"Duplicate territory_id {manifest.territory_id!r}.")
            registry[manifest.territory_id] = path
    return registry


def registered_territory_ids() -> tuple[str, ...]:
    """Return deterministic IDs discovered from corridor manifests."""
    return tuple(sorted(_registry()))


def get_territory_manifest(territory_id: str) -> TerritoryManifest:
    registry = _registry()
    try:
        return _manifest_from_path(registry[territory_id])
    except KeyError as error:
        available = ", ".join(sorted(registry)) or "none"
        raise UnknownTerritoryError(
            f"Unknown territory_id {territory_id!r}. Registered territories: {available}."
        ) from error


def list_territories() -> tuple[TerritoryManifest, ...]:
    return tuple(get_territory_manifest(item) for item in registered_territory_ids())


def _dataset_path(manifest: TerritoryManifest, relative_path: str) -> Path:
    path = (manifest.path.parent / relative_path).resolve()
    try:
        path.relative_to(DATA_DIR)
    except ValueError as error:
        raise TerritoryError(
            f"Dataset path for {manifest.territory_id!r} escapes the data directory."
        ) from error
    return path


def load_territory(territory_id: str) -> LoadedTerritory:
    """Load one populated territory through manifest-selected adapters."""
    manifest = get_territory_manifest(territory_id)
    if manifest.status != POPULATED:
        raise TerritoryNotPopulatedError(
            f"Territory {territory_id!r} is registered as a placeholder and has no dataset."
        )

    loaded: dict[str, list[dict[str, Any]]] = {
        dataset_name: [] for dataset_name in CANONICAL_FIELDS
    }
    for dataset_name, spec in manifest.datasets.items():
        adapter = ADAPTERS[spec["adapter"]]
        loaded[dataset_name] = adapter(
            _dataset_path(manifest, spec["path"]),
            dataset_name=dataset_name,
            required_fields=CANONICAL_FIELDS[dataset_name],
        )

    resource_context = None
    resource_provenance = None
    if manifest.resource_context is not None:
        resource_context, resource_provenance = load_resource_context(
            _dataset_path(manifest, manifest.resource_context["path"])
        )

    return LoadedTerritory(
        manifest=manifest,
        stations=loaded["stations"],
        sections=loaded["sections"],
        train_occupancy=loaded["train_occupancy"],
        maintenance_tasks=loaded["maintenance_tasks"],
        resource_context=resource_context,
        resource_provenance=resource_provenance,
    )
