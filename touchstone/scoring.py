"""Strict, deterministic scoring. Model text is data, never executable code."""
import json
from .scheduling import solve

SCORER_VERSION = "scheduling-strict-v1"
OUTCOMES = ("valid_schedule", "correct_infeasible", "constraint_violation",
            "incorrect_infeasible", "format_error", "abstention", "provider_error")


def result(outcome, reasons=()):
    return {
        "outcome": outcome,
        "valid_completion": outcome in ("valid_schedule", "correct_infeasible"),
        "constraint_violation": outcome == "constraint_violation",
        "format_error": outcome == "format_error",
        "abstention": outcome == "abstention",
        "provider_error": outcome == "provider_error",
        "reasons": list(reasons),
    }


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate key")
        obj[key] = value
    return obj


def reject_constant(value):
    raise ValueError("non-finite JSON constant")


def score(case, output):
    if not isinstance(output, str) or len(output) > 100_000:
        return result("format_error", ["expected bounded JSON text"])
    try:
        obj = json.loads(output, object_pairs_hook=unique_object,
                         parse_constant=reject_constant)
    except (ValueError, RecursionError):
        return result("format_error", ["invalid JSON or duplicate keys"])
    if not isinstance(obj, dict) or not isinstance(obj.get("status"), str):
        return result("format_error", ["expected object with status"])
    status = obj["status"]
    if status in ("abstain", "infeasible"):
        if set(obj) != {"status"}:
            return result("format_error", ["unexpected fields"])
        if status == "abstain":
            return result("abstention")
        return result("correct_infeasible" if solve(case) is None
                      else "incorrect_infeasible")
    if status != "scheduled" or set(obj) != {"status", "assignment"}:
        return result("format_error", ["unknown status or unexpected fields"])
    assignment = obj["assignment"]
    if not isinstance(assignment, dict):
        return result("format_error", ["assignment must be an object"])
    if any(type(slot) is not int for slot in assignment.values()):
        return result("format_error", ["slot must be an integer, not boolean or float"])
    reasons = []
    names = {task.name for task in case.tasks}
    if set(assignment) != names:
        reasons.append("missing or unknown tasks")
    loads = [0] * len(case.capacities)
    for task in case.tasks:
        if task.name not in assignment:
            continue
        slot = assignment[task.name]
        if slot not in task.allowed:
            reasons.append(f"{task.name}: disallowed slot")
        if 0 <= slot < len(loads):
            loads[slot] += task.demand
        else:
            reasons.append(f"{task.name}: slot out of range")
    for slot, (load, capacity) in enumerate(zip(loads, case.capacities)):
        if load > capacity:
            reasons.append(f"slot {slot}: capacity exceeded")
    return result("constraint_violation", reasons) if reasons else result("valid_schedule")
