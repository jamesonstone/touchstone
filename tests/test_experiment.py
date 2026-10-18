from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from touchstone.experiment import Config, Oracle, canonical, digest, plan, run
from touchstone.report import cluster_interval, markdown, summary


class ExperimentTests(unittest.TestCase):
    def test_pairing_repetition_and_order(self):
        config = Config()
        cases, trials = plan(config)
        self.assertEqual(len(cases), 4)
        self.assertEqual(len(trials), 24)
        self.assertEqual(len({t["trial_id"] for t in trials}), 24)
        self.assertEqual(plan(config), plan(config))
        other = plan(replace(config, order_seed=42))[1]
        self.assertNotEqual(trials, other)
        self.assertEqual({t["trial_id"] for t in trials}, {t["trial_id"] for t in other})
        for trial in trials:
            self.assertEqual(trial["prompt_sha256"], digest(trial["prompt"]))
        for case in cases:
            group = [t for t in trials if t["case_id"] == case.id]
            self.assertEqual(len(group), 6)
            self.assertEqual(len({canonical(t["case"]) for t in group}), 1)

    def test_bounded_config(self):
        for kwargs in ({"pairs": 0}, {"pairs": 101}, {"repetitions": -1},
                       {"seed": True}, {"repetitions": 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Config(**kwargs)

    def test_oracle_run_evidence_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "oracle"
            manifest, rows = run(Config(), Oracle(), target, "test-revision")
            self.assertEqual(len(rows), 24)
            self.assertFalse(manifest["provider"]["measured_model"])
            self.assertIn("scheduling.py", manifest["source_sha256"])
            saved = [json.loads(line) for line in (target / "trials.jsonl").read_text().splitlines()]
            self.assertEqual(saved, rows)
            self.assertEqual(json.loads((target / "manifest.json").read_text()), manifest)
            self.assertEqual(digest(json.loads((target / "plan.json").read_text())),
                             manifest["plan_sha256"])
            self.assertTrue(all(r["latency_seconds"] >= 0 for r in rows))
            with self.assertRaises(FileExistsError):
                run(Config(), Oracle(), target)
            report = summary(manifest, rows)
            self.assertIn("not a model baseline", markdown(report))
            self.assertEqual(report["attempted_requests"], 0)
            for condition in report["conditions"].values():
                self.assertEqual(condition["denominator"], 8)
                self.assertEqual(condition["valid_completions"], 8)
                self.assertEqual(condition["unique_cases"], 4)

    def test_provider_failures_do_not_leak_or_disappear(self):
        class Broken:
            provenance = {"provider": "test", "model": "test", "settings": {},
                          "measured_model": True}

            def complete(self, trial, case):
                raise RuntimeError("secret-like message must not be logged")

        with tempfile.TemporaryDirectory() as tmp:
            manifest, rows = run(Config(pairs=1, repetitions=1), Broken(), Path(tmp) / "run")
            self.assertEqual(len(rows), 6)
            self.assertNotIn("secret-like", canonical(rows))
            report = summary(manifest, rows)
            self.assertEqual(report["baseline_status"], "BLOCKED_NO_MODEL_OUTPUT")
            self.assertIsNone(report["usage"])
            self.assertIn("no measured model baseline", markdown(report))
            for condition in report["conditions"].values():
                self.assertEqual(condition["denominator"], 2)
                self.assertEqual(condition["valid_completions"], 0)
                self.assertEqual(condition["outcomes"]["provider_error"], 2)

    def test_refuse_everything_never_succeeds(self):
        class Refuse(Oracle):
            def complete(self, trial, case):
                return {"output": '{"status":"abstain"}', "usage": None}

        with tempfile.TemporaryDirectory() as tmp:
            manifest, rows = run(Config(), Refuse(), Path(tmp) / "run")
            for condition in summary(manifest, rows)["conditions"].values():
                self.assertEqual(condition["completion_rate"], 0)
                self.assertEqual(condition["outcomes"]["abstention"], 8)

    def test_provider_declared_failure_is_not_model_format_error(self):
        from touchstone.openai_provider import parse_response

        class Failed(Oracle):
            provenance = dict(Oracle.provenance, measured_model=True)

            def complete(self, trial, case):
                return parse_response({"model": "fixture-model", "status": "failed", "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": "partial model text"}]}],
                                       "error": {"code": "server_error", "message": "not retained"}}, None)

        with tempfile.TemporaryDirectory() as tmp:
            manifest, rows = run(Config(pairs=1, repetitions=1), Failed(), Path(tmp)/"run")
            self.assertEqual(summary(manifest, rows)["baseline_status"], "BLOCKED_NO_MODEL_OUTPUT")
            self.assertTrue(all(r["score"]["provider_error"] for r in rows))
            self.assertFalse(any(r["score"]["format_error"] for r in rows))
            self.assertNotIn("not retained", canonical(rows))

    def test_paired_uncertainty_uses_case_clusters(self):
        self.assertIsNone(cluster_interval([1]))
        self.assertEqual(cluster_interval([0, 0, 0]), [0, 0])
        self.assertEqual(cluster_interval([-1, 1]), [-1, 1])
        self.assertEqual(cluster_interval([0, 1, 0]), cluster_interval([0, 1, 0]))
        with tempfile.TemporaryDirectory() as tmp:
            manifest, rows = run(Config(), Oracle(), Path(tmp) / "run")
            for row in rows:
                if row["variant"] == "invariant" and row["feasible"]:
                    row["score"]["valid_completion"] = False
            paired = summary(manifest, rows)["paired"]["invariant"]
            self.assertEqual(paired["unique_case_pairs"], 4)
            self.assertEqual(paired["completion_delta_vs_control"], -.5)
            self.assertEqual(paired["paired_case_bootstrap_95"], [-1, 0])


if __name__ == "__main__":
    unittest.main()
