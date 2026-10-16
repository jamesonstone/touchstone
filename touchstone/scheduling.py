"""Synthetic capacity scheduling, exhaustive reference solver, and prompt variants."""
from dataclasses import asdict, dataclass
import json
import random

FAMILY = "capacity-scheduling-v1"
VARIANTS = {
    "control": "Scheduling constraints:",
    "invariant": "Each scheduling constraint is an invariant.",
    "never_break": "Each scheduling constraint is a rule you must never break.",
}


@dataclass(frozen=True)
class Task:
    name: str
    demand: int
    allowed: tuple[int, ...]


@dataclass(frozen=True)
class Case:
    id: str
    capacities: tuple[int, ...]
    tasks: tuple[Task, ...]

    def payload(self):
        return json.loads(json.dumps(asdict(self)))


def solve(case):
    """Return a complete feasible assignment, or None after exhaustive search."""
    remaining = list(case.capacities)
    assignment = {}

    def visit(index):
        if index == len(case.tasks):
            return dict(assignment)
        task = case.tasks[index]
        for slot in task.allowed:
            if remaining[slot] >= task.demand:
                remaining[slot] -= task.demand
                assignment[task.name] = slot
                result = visit(index + 1)
                if result is not None:
                    return result
                remaining[slot] += task.demand
                del assignment[task.name]
        return None

    return visit(0)


def generate(seed, pairs):
    """One feasible and one infeasible case per pair, with seed-local RNG."""
    rng = random.Random(seed)
    cases = []
    for index in range(pairs):
        capacities = [0, 0, 0]
        tasks = []
        for number in range(4):
            slot = rng.randrange(3)
            demand = rng.randint(1, 2)
            capacities[slot] += demand
            allowed = tuple(sorted({slot, rng.randrange(3)}))
            tasks.append(Task(f"t{number}", demand, allowed))
        capacities = tuple(max(2, load) for load in capacities)
        cases.append(Case(f"s{seed}-p{index}-feasible", capacities, tuple(tasks)))
        slot = rng.randrange(3)
        bad = (Task("t0", 2, (slot,)), Task("t1", 2, (slot,)),
               Task("t2", 1, tuple(range(3))), Task("t3", 1, tuple(range(3))))
        cases.append(Case(f"s{seed}-p{index}-infeasible", (2, 2, 2), bad))
    return cases


def prompt(case, variant):
    """Only the framing sentence changes across conditions; rules stay literal."""
    return (
        "Solve this synthetic scheduling task. Return only one JSON object.\n"
        + VARIANTS[variant] + "\n"
        "1. Assign every task exactly once to one integer slot listed in its allowed field.\n"
        "2. In each slot, the sum of assigned task demands must not exceed its capacity.\n"
        'If feasible, return {"status":"scheduled","assignment":{"task_name":0}} '
        "with all task names and their assigned slots.\n"
        'If no complete schedule exists, return {"status":"infeasible"}.\n'
        'If you cannot answer, return {"status":"abstain"}.\n'
        "Slots are zero-indexed. Task data:\n"
        + json.dumps({"capacities": case.capacities, "tasks": [asdict(t) for t in case.tasks]},
                     sort_keys=True, separators=(",", ":"))
    )
