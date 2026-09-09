"""Deterministic recovery and risk preferences through the real CP-SAT engine."""
import sys
from pathlib import Path
from copy import deepcopy
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from optimizer import optimize_schedule
from recovery import apply_train_delay, recover_schedule, plan_changes, validate_current_plan
from candidate_windows import OperationalAllowances
from time_utils import datetime_to_minutes

START, END = "2026-09-01T00:00:00", "2026-09-01T06:00:00"
ALLOW = OperationalAllowances(safety_after_minutes=5, safety_before_minutes=5, setup_minutes=10, release_minutes=5)


def inputs():
    return {"maintenance_tasks":[
        dict(task_id="A", section_id="S", duration_minutes=30, criticality=9, urgency=8),
        dict(task_id="B", section_id="OTHER", duration_minutes=30, criticality=3)],
        "train_occupancy":[dict(train_id="T", section_id="S", entry_time=START, exit_time="2026-09-01T01:00:00")]}


def base(data):
    return optimize_schedule(data, START, END, allowances=ALLOW)["blocks"]


def test_shift_all_train_rows_without_mutating_input():
    data = inputs()
    data["train_occupancy"].append(dict(train_id="T", section_id="OTHER", entry_time="2026-09-01T01:00:00", exit_time="2026-09-01T01:20:00"))
    original = deepcopy(data)
    changed = apply_train_delay(data,"T",25)
    assert data == original
    for old,new in zip(data["train_occupancy"],changed["train_occupancy"]):
        assert datetime_to_minutes(new["entry_time"], old["entry_time"]) == 25
        assert datetime_to_minutes(new["exit_time"], old["exit_time"]) == 25


def test_no_change_retains_identical_possessions():
    data = inputs()
    old = base(data)
    result = recover_schedule(data,old,dict(type="TRAIN_DELAY",train_id="T",delay_minutes=0),START,END,allowances=ALLOW)
    assert result["plan"]["blocks"] == old
    assert result["changes"]["metrics"]["retained_blocks"] == 2
    assert result["changes"]["metrics"]["total_shift_minutes"] == 0
    assert result["invalidated_blocks"] == []


def test_invalidated_block_is_repaired_and_unaffected_block_retained():
    data = inputs()
    old = base(data)
    result = recover_schedule(data,old,dict(type="TRAIN_DELAY",train_id="T",delay_minutes=130),START,END,allowances=ALLOW)
    assert len(result["invalidated_blocks"]) == 1
    assert result["changes"]["metrics"]["retained_blocks"] == 1
    assert result["changes"]["metrics"]["shifted_blocks"] == 1
    assert result["diagnostics"]["proof_state"] == "FULLY_OPTIMAL"
    changed = apply_train_delay(data,"T",130)
    validate_current_plan(changed,result["plan"]["blocks"],START,END,allowances=ALLOW)


def test_stability_beats_lower_order_efficiency_and_slack():
    data = inputs()
    old = base(data)
    old[0]["start_time"],old[0]["end_time"] = "2026-09-01T00:01:00","2026-09-01T00:46:00"
    # OTHER section has no train; this valid edge placement has worse slack.
    assert old[0]["section_id"] == "OTHER"
    result = recover_schedule(data,old,dict(type="TRAIN_DELAY",train_id="T",delay_minutes=0),START,END,allowances=ALLOW)
    assert result["plan"]["blocks"] == old
    names = [s["stage"] for s in result["diagnostics"]["priority_stages"]]
    assert names[:4] == ["criticality","urgency","overdue_days","task_count"]
    assert names.index("unchanged_previous_possessions") < names.index("possession_minutes")


@pytest.mark.parametrize("field",["criticality","urgency"])
def test_higher_service_priority_beats_retaining_old_work(field):
    data = {"maintenance_tasks":[dict(task_id="LOW",section_id="S",duration_minutes=180,criticality=1,urgency=1),
                                 dict(task_id="HIGH",section_id="S",duration_minutes=180,criticality=1,urgency=1)],
            "train_occupancy":[dict(train_id="T",section_id="S",entry_time="2026-09-01T05:30:00",exit_time=END)]}
    data["maintenance_tasks"][1][field] = 9
    old = [dict(block_id="OLD",section_id="S",start_time=START,end_time="2026-09-01T03:15:00",tasks=["LOW"],integrated=False,affected_trains=[],explanation=[])]
    result = recover_schedule(data,old,dict(type="TRAIN_DELAY",train_id="T",delay_minutes=0),START,END,allowances=ALLOW)
    assert result["plan"]["blocks"][0]["tasks"] == ["HIGH"]
    assert result["changes"]["newly_unscheduled_task_ids"] == ["LOW"]


def test_matching_uses_task_sets_not_solver_block_ids():
    old = base(inputs())
    renamed = deepcopy(old)
    for b in renamed:
        b["block_id"] = "NEW_"+b["block_id"]
    changes = plan_changes(old,renamed)
    assert changes["metrics"]["retained_blocks"] == 2
    assert changes["metrics"]["new_blocks"] == 0


def test_risk_prefers_extra_reserve_without_relaxing_safety():
    data = inputs()
    normal = optimize_schedule(data,START,END,allowances=ALLOW)
    risk = optimize_schedule(data,START,END,allowances=ALLOW,risk_penalties={("T","S"):60})
    a = next(b for b in normal["blocks"] if b["section_id"] == "S")
    b = next(b for b in risk["blocks"] if b["section_id"] == "S")
    assert datetime_to_minutes(b["start_time"],a["start_time"]) > 0
    validate_current_plan(data,risk["blocks"],START,END,allowances=ALLOW)
    assert optimize_schedule(data,START,END,allowances=ALLOW,risk_penalties={}) == normal


@pytest.mark.parametrize("penalties",[{("UNKNOWN","S"):12},{("T","S"):-1},{("T","S"):float("nan")},{("T","S"):True}])
def test_unsupported_risk_is_rejected(penalties):
    with pytest.raises(ValueError,match="Risk requires"):
        optimize_schedule(inputs(),START,END,allowances=ALLOW,risk_penalties=penalties)


def test_impossible_repair_is_explicitly_unscheduled():
    data = inputs()
    data["maintenance_tasks"][0]["deadline"] = "2026-09-01T02:00:00"
    old = base(data)
    # Shift long occupancy over all reservation starts that meet A's deadline.
    data["train_occupancy"][0]["entry_time"] = "2026-08-31T23:00:00"
    result = recover_schedule(data,old,dict(type="TRAIN_DELAY",train_id="T",delay_minutes=60),START,END,allowances=ALLOW)
    assert "A" in result["plan"]["unscheduled_tasks"]
    assert result["changes"]["newly_unscheduled_task_ids"] == ["A"]
