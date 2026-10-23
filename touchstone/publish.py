"""Deterministic, dependency-free Markdown/SVG views of benchmark evidence."""
from dataclasses import asdict
from html import escape
from pathlib import Path
from .experiment import Oracle, canonical, digest, plan
from .report import markdown, summary
from .scheduling import FAMILY
from .scoring import SCORER_VERSION, score


def chart(report):
    if not report["measured_model"]:
        title = "ORACLE DEMO — NOT MODEL RESULTS"
    elif report["baseline_status"] == "BLOCKED_NO_MODEL_OUTPUT":
        title = "BASELINE BLOCKED — NO MODEL OUTPUTS"
    else:
        title = "Model pilot — descriptive task completion"
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="860" height="340" viewBox="0 0 860 340" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        '<desc id="desc">Completed tasks by wording, with planned trial denominators. Oracle fixtures are not measured model scores.</desc>',
        '<rect width="860" height="340" rx="16" fill="#111827"/>',
        '<g font-family="Arial, sans-serif" fill="#f9fafb">',
        f'<text x="28" y="42" font-size="22" font-weight="bold">{escape(title)}</text>',
        '<text x="28" y="70" font-size="14" fill="#cbd5e1">Capacity scheduling · same cases across three wording conditions</text>',
    ]
    for index, (name, condition) in enumerate(report["conditions"].items()):
        y = 108 + index * 58
        total = condition["denominator"]
        complete = condition["valid_completions"]
        errors = condition["outcomes"]["provider_error"]
        width = 400 * complete / total if total else 0
        parts.extend([
            f'<text x="28" y="{y + 20}" font-size="16">{escape(name)}</text>',
            f'<rect x="170" y="{y}" width="400" height="28" rx="4" fill="#475569"/>',
            f'<rect x="170" y="{y}" width="{width:g}" height="28" rx="4" fill="#34d399"/>',
            f'<text x="590" y="{y + 20}" font-size="16">{complete} / {total} complete · {errors} errors</text>',
        ])
    footer = ("Reference-solver fixture only. No language-model inference or equivalence claim."
              if not report["measured_model"] else
              "Tiny pilot: report includes paired case-cluster intervals; no universal conclusion.")
    parts.extend([f'<text x="28" y="300" font-size="14" fill="#cbd5e1">{escape(footer)}</text>',
                  '<text x="28" y="322" font-size="12" fill="#94a3b8">Green: valid completion. Gray: remaining planned trials, including failures and abstentions.</text>',
                  '</g></svg>'])
    return "\n".join(parts) + "\n"


def demo(config, directory):
    """Regenerate a reference fixture, never a model baseline or measured latency."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    cases, trials = plan(config)
    by_id = {case.id: case for case in cases}
    oracle = Oracle()
    rows = [{**trial, "response": oracle.complete(trial, by_id[trial["case_id"]]),
             "latency_seconds": None} for trial in trials]
    for row in rows:
        row["score"] = score(by_id[row["case_id"]], row["response"]["output"])
    manifest = {"benchmark": FAMILY, "scorer": SCORER_VERSION,
                "provider": oracle.provenance, "trial_count": len(trials)}
    report = summary(manifest, rows)
    report["fixture"] = {"kind": "deterministic-reference-demo", "config": asdict(config),
                         "plan_sha256": digest(trials), "measured_latency": False}
    (directory / "demo.json").write_text(canonical(report) + "\n", encoding="utf-8")
    (directory / "demo.md").write_text(markdown(report), encoding="utf-8")
    (directory / "demo.svg").write_text(chart(report), encoding="utf-8")
    print(f"Oracle demonstration only: {len(rows)} fixture trials at {directory}")
