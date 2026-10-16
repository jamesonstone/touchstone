"""Within-experiment descriptive counts and case-cluster paired uncertainty."""
from collections import Counter, defaultdict
import random
from .scheduling import VARIANTS
from .scoring import OUTCOMES


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def cluster_interval(values, seed=12345, samples=4000):
    """Resample cases, retaining all repetitions and paired wording outcomes."""
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = [sum(rng.choices(values, k=len(values))) / len(values)
             for _ in range(samples)]
    return [percentile(means, .025), percentile(means, .975)]


def summary(manifest, rows):
    conditions = {}
    rates = {}
    for variant in VARIANTS:
        selected = [row for row in rows if row["variant"] == variant]
        counts = Counter(row["score"]["outcome"] for row in selected)
        by_case = defaultdict(list)
        for row in selected:
            by_case[row["case_id"]].append(int(row["score"]["valid_completion"]))
        rates[variant] = {key: sum(v) / len(v) for key, v in by_case.items()}
        successes = sum(row["score"]["valid_completion"] for row in selected)
        subgroups = {}
        for feasible in (True, False):
            group = [row for row in selected if row["feasible"] == feasible]
            subgroups["feasible" if feasible else "infeasible"] = {
                "denominator": len(group),
                "valid_completions": sum(r["score"]["valid_completion"] for r in group)}
        conditions[variant] = {
            "denominator": len(selected), "unique_cases": len(by_case),
            "valid_completions": successes,
            "completion_rate": successes / len(selected) if selected else None,
            "completion_case_bootstrap_95": cluster_interval(list(rates[variant].values())),
            "outcomes": {key: counts[key] for key in OUTCOMES}, "by_feasibility": subgroups,
        }
    paired = {}
    for variant in VARIANTS:
        if variant == "control":
            continue
        common = sorted(rates[variant].keys() & rates["control"].keys())
        differences = [rates[variant][key] - rates["control"][key] for key in common]
        paired[variant] = {
            "unique_case_pairs": len(common),
            "completion_delta_vs_control": sum(differences) / len(common) if common else None,
            "paired_case_bootstrap_95": cluster_interval(differences),
        }
    return {
        "benchmark": manifest["benchmark"], "measured_model": manifest["provider"]["measured_model"],
        "planned_trials": manifest["trial_count"], "recorded_trials": len(rows),
        "conditions": conditions, "paired": paired,
        "uncertainty": "Percentile case-cluster bootstrap, 4000 draws, seed 12345. "
        "Repeats are not independent cases. Tiny samples and degenerate intervals "
        "cannot establish equivalence or a population effect. No multiple-comparison inference.",
    }


def markdown(report):
    kind = "Model pilot" if report["measured_model"] else "Oracle plumbing test (not a model baseline)"
    lines = [f"# {kind}", "", f"Benchmark: `{report['benchmark']}`.", "",
             "| Wording | Completed / attempts | Unique cases | Case-bootstrap 95% interval |",
             "| --- | --- | --- | --- |"]
    for name, condition in report["conditions"].items():
        lines.append(f"| {name} | {condition['valid_completions']} / {condition['denominator']} | "
                     f"{condition['unique_cases']} | {condition['completion_case_bootstrap_95']} |")
    lines.extend(["", report["uncertainty"], "", "## Paired completion differences versus control", ""])
    for name, paired in report["paired"].items():
        lines.append(f"- {name}: {paired['completion_delta_vs_control']}; "
                     f"95% interval {paired['paired_case_bootstrap_95']}; "
                     f"{paired['unique_case_pairs']} paired cases.")
    lines.extend(["", "See report.json for every outcome count and feasibility denominator.",
                  "All planned attempts, including provider errors, remain in the denominator.",
                  "No overall score combines unrelated benchmarks.", ""])
    return "\n".join(lines)
