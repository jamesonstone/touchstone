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
    parser.add_argument("command", choices=("plan", "oracle", "openai", "anthropic", "demo"))
    parser.add_argument("--allow-live", action="store_true", help="Explicitly permit paid pilot calls")
    parser.add_argument("--resume", action="store_true", help="Resume the same plan and persistent budget")
    parser.add_argument("--budget-cents", type=int, choices=range(1, 501), default=10)
    parser.add_argument("--budget-ledger", type=Path, help="Shared durable ledger across pilot directories")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = Config(**json.loads(args.config.read_text())) if args.config else Config()
    if args.command == "plan":
        _, trials = plan(config)
        with args.out.open("x") as stream:
            stream.write(canonical({"config": asdict(config), "trials": trials}) + "\n")
        print(f"Exported {len(trials)} paired trials to {args.out}")
        return
    if args.command == "demo":
        from .publish import demo
        demo(config, args.out)
        return
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent,
                                capture_output=True, text=True, check=False)
        revision = result.stdout.strip() if result.returncode == 0 else "unknown"
    except FileNotFoundError:
        revision = "unknown"
    provider = Oracle()
    if args.command in ("openai", "anthropic"):
        from .openai_provider import MAX_INPUT_BYTES, MAX_REQUESTS, OpenAIProvider
        _, trials = plan(config)
        if not args.allow_live:
            parser.error("live providers require --allow-live; at most 24 paid requests")
        if len(trials) > MAX_REQUESTS or any(
                len(t["prompt"].encode()) > MAX_INPUT_BYTES for t in trials):
            parser.error("pilot exceeds request or input bounds")
        if args.budget_cents > 100 and args.budget_ledger is None:
            parser.error("budgets above $1 require --budget-ledger for the whole effort")
        provider_type = OpenAIProvider
        if args.command == "anthropic":
            from .anthropic_provider import AnthropicProvider
            provider_type = AnthropicProvider
        provider = provider_type(budget_cents=args.budget_cents, ledger_path=args.budget_ledger)
    manifest, rows = run(config, provider, args.out, revision, resume=args.resume)
    report = summary(manifest, rows)
    (args.out / "report.json").write_text(canonical(report) + "\n")
    (args.out / "report.md").write_text(markdown(report))
    from .publish import chart
    (args.out / "results.svg").write_text(chart(report))
    label = ("Live-access failure; no measured baseline"
             if report["baseline_status"] == "BLOCKED_NO_MODEL_OUTPUT" else
             "Model pilot" if provider.provenance["measured_model"] else "Oracle plumbing only")
    print(f"{label}: {len(rows)} trials; evidence at {args.out}")


if __name__ == "__main__":
    main()
