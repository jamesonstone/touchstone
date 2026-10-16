"""Provider-independent experiment construction and append-only run evidence."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import time
import os
from .budget import locked_file
from . import __version__
from .scheduling import FAMILY, VARIANTS, generate, prompt, solve
from .scoring import SCORER_VERSION, result, score


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


@dataclass(frozen=True)
class Config:
    seed: int = 1729
    pairs: int = 2
    repetitions: int = 2
    order_seed: int = 2718

    def __post_init__(self):
        if any(type(value) is not int for value in asdict(self).values()):
            raise ValueError("configuration values must be integers")
        if not 1 <= self.pairs <= 100 or not 1 <= self.repetitions <= 100:
            raise ValueError("pairs and repetitions must be between 1 and 100")


def plan(config):
    cases = generate(config.seed, config.pairs)
    trials = []
    for case in cases:
        for repetition in range(config.repetitions):
            for variant in VARIANTS:
                text = prompt(case, variant)
                trials.append({
                    "trial_id": f"{case.id}/{repetition}/{variant}",
                    "case_id": case.id, "case": case.payload(),
                    "feasible": solve(case) is not None,
                    "repetition": repetition, "variant": variant,
                    "prompt": text, "prompt_sha256": digest(text),
                })
    random.Random(config.order_seed).shuffle(trials)
    return cases, trials


class Oracle:
    """Plumbing control only. Never a measured model baseline."""
    provenance = {"provider": "oracle", "model": "exhaustive-reference-v1",
                  "settings": {}, "measured_model": False}

    def complete(self, trial, case):
        assignment = solve(case)
        output = {"status": "infeasible"} if assignment is None else {
            "status": "scheduled", "assignment": assignment}
        return {"output": canonical(output), "usage": None, "response_id": None}


def run(config, provider, directory, revision="unknown", resume=False):
    directory = Path(directory)
    # Do not overwrite any prior experiment, even after a partial failure.
    directory.mkdir(parents=True, exist_ok=resume)
    with locked_file(directory / "run.lock"):
        return run_locked(config, provider, directory, revision, resume)


def run_locked(config, provider, directory, revision, resume):
    cases, trials = plan(config)
    by_id = {case.id: case for case in cases}
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(Path(__file__).parent.glob("*.py"))}
    manifest = {
        "schema_version": 1, "benchmark": FAMILY, "scorer": SCORER_VERSION,
        "touchstone_version": __version__, "revision": revision,
        "source_sha256": source_hashes, "python": platform.python_version(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config), "provider": provider.provenance,
        "trial_count": len(trials), "plan_sha256": digest(trials),
    }
    manifest["config_sha256"] = digest({"config": manifest["config"],
                                        "provider": manifest["provider"],
                                        "benchmark": FAMILY, "scorer": SCORER_VERSION})
    rows = []
    if resume:
        saved = json.loads((directory / "manifest.json").read_text())
        for key in ("config_sha256", "plan_sha256", "source_sha256"):
            if saved[key] != manifest[key]:
                raise ValueError("resume configuration, plan or source differs")
        manifest = saved
        rows = [json.loads(line) for line in (directory / "trials.jsonl").read_text().splitlines()]
        if len(rows) > len(trials) or any(
                row["trial_id"] != trial["trial_id"] or row["sequence"] != i
                for i, (row, trial) in enumerate(zip(rows, trials))):
            raise ValueError("resume evidence is not a valid plan prefix")
    else:
        (directory / "manifest.json").write_text(canonical(manifest) + "\n")
        (directory / "plan.json").write_text(canonical(trials) + "\n")
    if hasattr(provider, "bind_budget"):
        if resume and not (directory / "budget.jsonl").is_file():
            raise ValueError("resume requires the original budget ledger")
        provider.bind_budget(directory)
    with (directory / "trials.jsonl").open("a" if resume else "x") as stream:
        for sequence in range(len(rows), len(trials)):
            trial = trials[sequence]
            start = time.perf_counter()
            try:
                response = provider.complete(trial, by_id[trial["case_id"]])
                scored = (result("abstention", ["provider refusal"])
                          if response.get("provider_refusal") else
                          score(by_id[trial["case_id"]], response["output"]))
            except Exception as exc:
                # Exception messages can contain credentials or request headers.
                response = {"output": None, "usage": None, "response_id": None,
                            "error_type": type(exc).__name__}
                if type(getattr(exc, "http_status", None)) is int:
                    response["http_status"] = exc.http_status
                if type(getattr(exc, "request_attempted", None)) is bool:
                    response["request_attempted"] = exc.request_attempted
                for key in ("provider_error_code", "provider_error_type", "request_id"):
                    if isinstance(getattr(exc, key, None), str):
                        response[key] = getattr(exc, key)
                scored = result("provider_error")
            row = {**trial, "sequence": sequence, "response": response,
                   "latency_seconds": time.perf_counter() - start, "score": scored}
            stream.write(canonical(row) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            rows.append(row)
    return manifest, rows
