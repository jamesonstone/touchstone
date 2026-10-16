"""Benchmark commands. Run with python3 -m touchstone."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
from .experiment import Config, Oracle, canonical, plan, run
from .report import markdown, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "oracle", "openai"))
    parser.add_argument("--allow-live", action="store_true", help="Explicitly permit paid pilot calls")
    parser.add_argument("--resume", action="store_true", help="Resume the same plan and persistent budget")
    parser.add_argument("--budget-cents", type=int, choices=range(1, 101), default=10)
    parser.add_argument("--config", type=Path, default=Path("configs/pilot.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = Config(**json.loads(args.config.read_text()))
    if args.command == "plan":
        _, trials = plan(config)
        with args.out.open("x") as stream:
            stream.write(canonical({"config": asdict(config), "trials": trials}) + "\n")
        print(f"Exported {len(trials)} paired trials to {args.out}")
        return
    revision = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    provider = Oracle()
    if args.command == "openai":
        from .openai_provider import MAX_INPUT_BYTES, MAX_REQUESTS, OpenAIProvider
        _, trials = plan(config)
        if not args.allow_live:
            parser.error("openai requires --allow-live; at most 24 paid requests")
        if len(trials) > MAX_REQUESTS or any(
                len(t["prompt"].encode()) > MAX_INPUT_BYTES for t in trials):
            parser.error("pilot exceeds request or input bounds")
        provider = OpenAIProvider(budget_cents=args.budget_cents)
    manifest, rows = run(config, provider, args.out, revision, resume=args.resume)
    report = summary(manifest, rows)
    (args.out / "report.json").write_text(canonical(report) + "\n")
    (args.out / "report.md").write_text(markdown(report))
    label = ("Live-access failure; no measured baseline"
             if report["baseline_status"] == "BLOCKED_NO_MODEL_OUTPUT" else
             "Model pilot" if provider.provenance["measured_model"] else "Oracle plumbing only")
    print(f"{label}: {len(rows)} trials; evidence at {args.out}")


if __name__ == "__main__":
    main()
