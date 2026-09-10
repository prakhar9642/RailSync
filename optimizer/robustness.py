"""Extra candidate-boundary margin in minutes, not predicted reliability."""

try:
    from .time_utils import datetime_to_minutes
except ImportError:
    from time_utils import datetime_to_minutes


def add_boundary_slack(model, blocks, windows_by_section, origin, horizon):
    effective_slacks = []
    for index, block in enumerate(blocks):
        before = model.NewIntVar(0, horizon, f"block_{index}_before_slack")
        after = model.NewIntVar(0, horizon, f"block_{index}_after_slack")
        slack = model.NewIntVar(0, horizon, f"block_{index}_boundary_slack")
        choices = []
        block["slack_choices"] = []
        block["before_slack"], block["after_slack"] = before, after
        window_key = block.get("footprint_id", block["section_id"])
        for window in windows_by_section.get(window_key, []):
            chosen = model.NewBoolVar(f"block_{index}_{window.window_id}_slack")
            choices.append(chosen)
            block["slack_choices"].append((window, chosen))
            start = datetime_to_minutes(window.usable_start, origin)
            end = datetime_to_minutes(window.usable_end, origin)
            model.Add(before == block["start"] - start).OnlyEnforceIf(chosen)
            model.Add(after == end - block["end"]).OnlyEnforceIf(chosen)
        model.Add(sum(choices) == block["present"])
        model.Add(before == 0).OnlyEnforceIf(block["present"].Not())
        model.Add(after == 0).OnlyEnforceIf(block["present"].Not())
        model.AddMinEquality(slack, [before, after])
        block["boundary_slack"] = slack
        # Absent anchors must not drag the minimum of scheduled blocks to zero.
        effective = model.NewIntVar(0, horizon, f"block_{index}_effective_slack")
        model.Add(effective == slack).OnlyEnforceIf(block["present"])
        model.Add(effective == horizon).OnlyEnforceIf(block["present"].Not())
        effective_slacks.append(effective)
    if not blocks:
        return 0, 0
    active = model.NewBoolVar("has_possessions")
    model.AddMaxEquality(active, [b["present"] for b in blocks])
    raw_minimum = model.NewIntVar(0, horizon, "raw_minimum_boundary_slack")
    model.AddMinEquality(raw_minimum, effective_slacks)
    minimum = model.NewIntVar(0, horizon, "minimum_boundary_slack")
    model.Add(minimum == raw_minimum).OnlyEnforceIf(active)
    model.Add(minimum == 0).OnlyEnforceIf(active.Not())
    return minimum, sum(b["boundary_slack"] for b in blocks)


def measure_boundary_slack(block, windows):
    """Independently measure the full public possession against usable bounds."""
    for window in windows:
        if "footprint_id" in block:
            if (window.footprint_id or window.section_id) != block["footprint_id"]:
                continue
        elif window.section_id != block["section_id"]:
            continue
        before = datetime_to_minutes(block["start_time"], window.usable_start)
        after = datetime_to_minutes(window.usable_end, block["end_time"])
        if before >= 0 and after >= 0:
            return dict(block_id=block["block_id"], window_id=window.window_id,
                        before_boundary_slack_minutes=before,
                        after_boundary_slack_minutes=after,
                        boundary_slack_minutes=min(before, after))
    raise ValueError(f"Possession {block['block_id']} has no containing usable window.")
