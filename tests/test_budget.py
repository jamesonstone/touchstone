import json
from pathlib import Path
import tempfile
import unittest
from touchstone.budget import Budget, BudgetError, locked_file
from touchstone.experiment import Config, Oracle, run


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "budget.jsonl"

    def test_reserve_before_call_and_persist_usage_without_refund(self):
        budget = Budget(self.path, max_requests=1)
        identifier = budget.reserve("trial", "hello")
        records = [json.loads(line) for line in self.path.read_text().splitlines()]
        self.assertEqual(records[1]["input_token_bound"], 1029)
        self.assertEqual(records[1]["reserved_micro_usd"], 1026)
        budget.finish(identifier, {"input_tokens": 2, "output_tokens": 3,
                                   "total_tokens": 5, "secret": "discard"})
        self.assertNotIn("discard", self.path.read_text())
        # A restarted process cannot recover/refund an already spent request slot.
        with self.assertRaises(BudgetError):
            Budget(self.path, max_requests=1).reserve("retry", "hello")

    def test_worst_case_dollars_bound_and_unknown_outcomes_stay_reserved(self):
        budget = Budget(self.path, budget_cents=1)
        for i in range(3):
            budget.reserve(str(i), "x" * 4096)
        with self.assertRaises(BudgetError):
            Budget(self.path, budget_cents=1).reserve("fourth", "x" * 4096)
        records = [json.loads(line) for line in self.path.read_text().splitlines()]
        self.assertEqual(sum(r.get("reserved_micro_usd", 0) for r in records), 7989)
        with self.assertRaises(BudgetError):
            Budget(self.path, budget_cents=2)  # No policy increase on resume.

    def test_terminal_authentication_stop_survives_restart(self):
        budget = Budget(self.path)
        identifier = budget.reserve("trial", "hello")
        budget.finish(identifier, http_status=401)
        with self.assertRaises(BudgetError):
            Budget(self.path).reserve("remaining", "hello")

    def test_unknown_price_and_excessive_bounds_rejected(self):
        for kwargs in ({"model": "unpriced-model"}, {"budget_cents": 101},
                       {"budget_cents": 0}, {"max_requests": 25}, {"output_cap": 385}):
            with self.subTest(kwargs=kwargs), self.assertRaises(BudgetError):
                Budget(self.path, **kwargs)
        self.assertFalse(self.path.exists())

    def test_damaged_ledger_and_concurrent_writer_fail_closed(self):
        Budget(self.path)
        with locked_file(self.path):
            with self.assertRaises(BudgetError):
                Budget(self.path)
        with self.path.open("a") as stream:
            stream.write("corrupt-partial-record")
        with self.assertRaises(BudgetError):
            Budget(self.path)

    def test_resume_retains_evidence_and_same_budget_after_lost_response(self):
        target = Path(self.tmp.name) / "run"

        class Interrupted(Oracle):
            def bind_budget(self, directory):
                self.budget = Budget(directory / "budget.jsonl", max_requests=1)

            def complete(self, trial, case):
                self.budget.reserve(trial["trial_id"], trial["prompt"])
                raise KeyboardInterrupt()  # Crash after reserve, before evidence append.

        class Resumed(Interrupted):
            def complete(self, trial, case):
                self.budget.reserve(trial["trial_id"], trial["prompt"])
                self.fail_if_called = True
                return super().complete(trial, case)

        with self.assertRaises(KeyboardInterrupt):
            run(Config(pairs=1, repetitions=1), Interrupted(), target)
        _, rows = run(Config(pairs=1, repetitions=1), Resumed(), target, resume=True)
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r["score"]["provider_error"] for r in rows))
        self.assertTrue(all(r["response"]["request_attempted"] is False for r in rows))
        self.assertEqual(len([r for r in map(json.loads, (target / "budget.jsonl").read_text().splitlines())
                              if r["kind"] == "reservation"]), 1)
        with self.assertRaises(ValueError):
            run(Config(pairs=1, repetitions=2), Resumed(), target, resume=True)

    def test_resume_requires_original_budget(self):
        class Bound(Oracle):
            def bind_budget(self, directory):
                self.budget = Budget(directory / "budget.jsonl")

        target = Path(self.tmp.name) / "run"
        run(Config(pairs=1, repetitions=1), Oracle(), target)
        with self.assertRaises(ValueError):
            run(Config(pairs=1, repetitions=1), Bound(), target, resume=True)


if __name__ == "__main__":
    unittest.main()
