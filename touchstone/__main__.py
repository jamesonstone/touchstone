"""Offline commands. Run with python3 -m touchstone."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
from .experiment import Config, Oracle, canonical, plan, run
from .report import markdown, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "oracle"))
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
    manifest, rows = run(config, Oracle(), args.out, revision)
    report = summary(manifest, rows)
    (args.out / "report.json").write_text(canonical(report) + "\n")
    (args.out / "report.md").write_text(markdown(report))
    print(f"Oracle plumbing only: {len(rows)} trials; evidence at {args.out}")


if __name__ == "__main__":
    main()
