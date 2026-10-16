"""Provider-independent experiment construction and append-only run evidence."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import time
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


def run(config, provider, directory, revision="unknown"):
    directory = Path(directory)
    # Do not overwrite any prior experiment, even after a partial failure.
    directory.mkdir(parents=True, exist_ok=False)
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
    (directory / "manifest.json").write_text(canonical(manifest) + "\n")
    (directory / "plan.json").write_text(canonical(trials) + "\n")
    rows = []
    with (directory / "trials.jsonl").open("x") as stream:
        for sequence, trial in enumerate(trials):
            start = time.perf_counter()
            try:
                response = provider.complete(trial, by_id[trial["case_id"]])
                scored = score(by_id[trial["case_id"]], response["output"])
            except Exception as exc:
                # Exception messages can contain credentials or request headers.
                response = {"output": None, "usage": None, "response_id": None,
                            "error_type": type(exc).__name__}
                scored = result("provider_error")
            row = {**trial, "sequence": sequence, "response": response,
                   "latency_seconds": time.perf_counter() - start, "score": scored}
            stream.write(canonical(row) + "\n")
            stream.flush()
            rows.append(row)
    return manifest, rows
