"""Configurable prototype eligibility, not railway activity compatibility facts."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class CompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    CONDITIONAL = "CONDITIONAL"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CompatibilityPolicy:
    allow_same_group: bool = True
    disabled_groups: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CompatibilityResult:
    eligible: bool
    status: CompatibilityStatus
    reason: str


def evaluate_compatibility(
    first: Mapping[str, Any], second: Mapping[str, Any],
    policy: CompatibilityPolicy = CompatibilityPolicy(),
) -> CompatibilityResult:
    first_footprint = first.get("_footprint_id")
    second_footprint = second.get("_footprint_id")
    if first_footprint or second_footprint:
        if first_footprint != second_footprint:
            return CompatibilityResult(False, CompatibilityStatus.INCOMPATIBLE, "DIFFERENT_POSSESSION_FOOTPRINT")
    elif first["section_id"] != second["section_id"]:
        return CompatibilityResult(False, CompatibilityStatus.INCOMPATIBLE, "WRONG_SECTION")
    a, b = first.get("compatibility_group"), second.get("compatibility_group")
    if not isinstance(a, str) or not a.strip() or not isinstance(b, str) or not b.strip():
        return CompatibilityResult(False, CompatibilityStatus.UNKNOWN, "UNKNOWN_COMPATIBILITY")
    eligible = a == b and policy.allow_same_group and a not in policy.disabled_groups
    return CompatibilityResult(
        # Legacy group equality is a prototype condition, not a validated
        # railway rule, so it remains CONDITIONAL. Explicit future rules may
        # use COMPATIBLE without changing this backward-compatible mechanism.
        eligible, CompatibilityStatus.CONDITIONAL if eligible else CompatibilityStatus.INCOMPATIBLE,
        "COMPATIBLE_GROUP" if eligible else "INCOMPATIBLE_GROUP",
    )
