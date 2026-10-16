import itertools
import json
import unittest
from touchstone.scheduling import Case, Task, generate, prompt, solve, VARIANTS
from touchstone.scoring import score


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.case = Case("example", (2, 2), (Task("a", 2, (0, 1)), Task("b", 1, (1,))))
        self.impossible = Case("impossible", (2, 2),
                               (Task("a", 2, (0,)), Task("b", 1, (0,))))

    def check(self, output, outcome, case=None):
        actual = score(case or self.case, output)
        self.assertEqual(actual["outcome"], outcome)
        self.assertEqual(actual["valid_completion"],
                         outcome in ("valid_schedule", "correct_infeasible"))
        for name in ("constraint_violation", "format_error", "abstention", "provider_error"):
            self.assertEqual(actual[name], name == outcome)

    def test_valid_completion(self):
        self.check('{"status":"scheduled","assignment":{"a":0,"b":1}}', "valid_schedule")
        self.check('{"status":"infeasible"}', "correct_infeasible", self.impossible)

    def test_false_infeasible_and_abstention_are_not_success(self):
        self.check('{"status":"infeasible"}', "incorrect_infeasible")
        for case in (self.case, self.impossible):
            self.check('{"status":"abstain"}', "abstention", case)

    def test_constraint_violations(self):
        assignments = [{}, {"a": 0}, {"a": 0, "b": 1, "extra": 0},
                       {"a": 1, "b": 1}, {"a": 0, "b": 0},
                       {"a": -1, "b": 1}, {"a": 999999999999999999, "b": 1}]
        for assignment in assignments:
            with self.subTest(assignment=assignment):
                self.check(json.dumps({"status": "scheduled", "assignment": assignment}),
                           "constraint_violation")
        self.check('{"status":"scheduled","assignment":{"a":0,"b":0}}',
                   "constraint_violation", self.impossible)

    def test_invalid_outputs(self):
        outputs = [None, "", "I refuse.", "[]", "null", '"scheduled"', "1", "true",
                   '{"status":1}', '{"status":[]}', '{"status":"unknown"}',
                   '{"status":"infeasible","assignment":{}}',
                   '{"status":"scheduled"}', '{"status":"abstain","reason":"x"}',
                   '{"status":"scheduled","assignment":[]}',
                   '{"status":"scheduled","assignment":{"a":true,"b":1}}',
                   '{"status":"scheduled","assignment":{"a":0.0,"b":1}}',
                   '{"status":"scheduled","assignment":{"a":"0","b":1}}',
                   '{"status":"scheduled","assignment":{"a":null,"b":1}}',
                   '{"status":"abstain","status":"infeasible"}',
                   '{"status":"scheduled","assignment":{"a":0,"a":1,"b":1}}',
                   '{"status":"scheduled","assignment":{"a":NaN,"b":1}}',
                   '{"status":"scheduled","assignment":{"a":Infinity,"b":1}}',
                   '```json\n{"status":"abstain"}\n```',
                   '{"status":"abstain"} trailing', "[" * 2000, "x" * 100001]
        for output in outputs:
            with self.subTest(output=str(output)[:80]):
                self.check(output, "format_error")

    def test_exhaustive_independent_oracle_and_scorer(self):
        for seed in range(20):
            for case in generate(seed, 2):
                found = False
                for slots in itertools.product(range(3), repeat=len(case.tasks)):
                    allowed = all(slot in task.allowed for task, slot in zip(case.tasks, slots))
                    capacity = all(sum(t.demand for t, s in zip(case.tasks, slots) if s == slot)
                                   <= cap for slot, cap in enumerate(case.capacities))
                    valid = allowed and capacity
                    output = json.dumps({"status": "scheduled", "assignment":
                                         dict(zip((t.name for t in case.tasks), slots))})
                    self.assertEqual(score(case, output)["valid_completion"], valid)
                    found |= valid
                self.assertEqual(solve(case) is not None, found)
                self.assertEqual(found, case.id.endswith("-feasible"))

    def test_generation_and_prompt_equivalence(self):
        self.assertEqual(generate(17, 2), generate(17, 2))
        self.assertNotEqual(generate(17, 2), generate(18, 2))
        for case in generate(17, 2):
            texts = [prompt(case, variant) for variant in VARIANTS]
            self.assertEqual(len({text.split("\n", 2)[2] for text in texts}), 1)
            for text in texts:
                self.assertNotIn(case.id, text)  # Never leak oracle labels into prompts.


if __name__ == "__main__":
    unittest.main()
