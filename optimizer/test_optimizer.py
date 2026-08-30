"""Tests for the RailSync Day 1 CP-SAT optimizer."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPTIMIZER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(OPTIMIZER_DIR))

from optimizer import load_mock_data, optimize_schedule  # noqa: E402


DEFAULT_MOCK_DATA_PATH = PROJECT_ROOT / "backend" / "mock-data.json"
MOCK_DATA_PATH = Path(
    os.environ.get("RAILSYNC_MOCK_DATA_PATH", DEFAULT_MOCK_DATA_PATH)
)
REQUIRED_METRIC_KEYS = {
    "baseline_block_hours",
    "optimized_block_hours",
    "baseline_affected_trains",
    "optimized_affected_trains",
    "integrated_blocks",
}


@pytest.fixture(scope="module")
def mock_data() -> dict:
    return load_mock_data(MOCK_DATA_PATH)


@pytest.fixture(scope="module")
def result(mock_data: dict) -> dict:
    return optimize_schedule(mock_data)


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _overlaps(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> bool:
    return first_start < second_end and second_start < first_end


def test_backend_mock_data_loads_successfully(mock_data: dict) -> None:
    assert isinstance(mock_data, dict)
    assert isinstance(mock_data["maintenance_tasks"], list)
    assert isinstance(mock_data["train_occupancy"], list)


def test_optimize_schedule_returns_contract_shape(result: dict) -> None:
    assert isinstance(result, dict)
    assert {"status", "blocks", "unscheduled_tasks", "metrics"}.issubset(result)


def test_feasible_mock_data_generates_a_block(result: dict) -> None:
    assert result["status"] == "success"
    assert len(result["blocks"]) >= 1


def test_scheduled_duration_matches_task_duration(
    mock_data: dict, result: dict
) -> None:
    task_by_id = {
        task["task_id"]: task for task in mock_data["maintenance_tasks"]
    }
    for block in result["blocks"]:
        assert len(block["tasks"]) == 1
        task = task_by_id[block["tasks"][0]]
        duration_minutes = (
            _parse(block["end_time"]) - _parse(block["start_time"])
        ).total_seconds() / 60
        assert duration_minutes == task["duration_minutes"]
        assert block["section_id"] == task["section_id"]


def test_blocks_do_not_overlap_trains_on_the_same_section(
    mock_data: dict, result: dict
) -> None:
    for block in result["blocks"]:
        for occupancy in mock_data["train_occupancy"]:
            if block["section_id"] != occupancy["section_id"]:
                continue
            assert not _overlaps(
                _parse(block["start_time"]),
                _parse(block["end_time"]),
                _parse(occupancy["entry_time"]),
                _parse(occupancy["exit_time"]),
            )


def test_blocks_do_not_overlap_each_other_on_the_same_section(
    result: dict,
) -> None:
    blocks = result["blocks"]
    for index, block in enumerate(blocks):
        for other_block in blocks[index + 1 :]:
            if block["section_id"] != other_block["section_id"]:
                continue
            assert not _overlaps(
                _parse(block["start_time"]),
                _parse(block["end_time"]),
                _parse(other_block["start_time"]),
                _parse(other_block["end_time"]),
            )


def test_all_contract_metric_keys_exist(result: dict) -> None:
    assert REQUIRED_METRIC_KEYS.issubset(result["metrics"])


def test_too_short_horizon_reports_tasks_as_unscheduled(mock_data: dict) -> None:
    short_result = optimize_schedule(
        mock_data,
        horizon_start="2026-09-01T00:00:00",
        horizon_end="2026-09-01T00:30:00",
    )
    assert short_result["status"] == "success"
    assert short_result["blocks"] == []
    assert set(short_result["unscheduled_tasks"]) == {
        task["task_id"] for task in mock_data["maintenance_tasks"]
    }
