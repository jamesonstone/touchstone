import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from touchstone.openai_provider import (ENDPOINT, MAX_REQUESTS, MODEL, OpenAIProvider,
                                       ProviderHTTPError, parse_response)
from touchstone.experiment import Config, Oracle, plan, run


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_text_usage_model_and_refusal_parsing(self):
        raw = {"id": "response-test", "model": MODEL, "status": "completed",
               "usage": {"input_tokens": 300, "output_tokens": 40},
               "output": [{"type": "reasoning"}, {"type": "message", "content": [
                   {"type": "output_text", "text": '{"status":"infeasible"}'}]}]}
        response = parse_response(raw, "request-test")
        self.assertEqual(response["output"], '{"status":"infeasible"}')
        self.assertEqual(response["usage"]["input_tokens"], 300)
        self.assertEqual(response["returned_model"], MODEL)
        self.assertFalse(response["provider_refusal"])
        raw["output"] = [{"type": "message", "content": [
            {"type": "refusal", "refusal": "cannot answer"}]}]
        self.assertTrue(parse_response(raw, None)["provider_refusal"])
        self.assertEqual(parse_response({"status": "incomplete"}, None)["output"], "")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-placeholder", "OPENAI_BASE_URL": ""})
    def test_only_prompt_sent_and_request_limits(self):
        provider = OpenAIProvider()
        provider.bind_budget(Path(self.tmp.name))
        observed = []

        class Response(io.BytesIO):
            headers = {"x-request-id": "request-test"}

        def fake_open(request, timeout):
            self.assertEqual(request.full_url, ENDPOINT)
            self.assertEqual(timeout, 30)
            observed.append(json.loads(request.data))
            return Response(b'{"output":[],"status":"completed"}')

        provider.opener.open = fake_open
        case, trials = plan(Config())
        provider.complete(trials[0], case[0])
        self.assertEqual(observed[0]["input"], [{"role": "user", "content": trials[0]["prompt"]}])
        self.assertEqual(observed[0]["max_output_tokens"], 384)
        self.assertFalse(observed[0]["store"])
        self.assertEqual(observed[0]["tools"], [])
        self.assertEqual(observed[0]["temperature"], .7)
        self.assertNotIn("unit-test-placeholder", json.dumps(provider.provenance))
        with self.assertRaises(ValueError):
            provider.complete({"prompt": "x" * 4097}, None)
        provider.requests = MAX_REQUESTS
        with self.assertRaises(ValueError):
            provider.complete(trials[0], None)
        self.assertEqual(len(observed), 1)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-placeholder", "OPENAI_BASE_URL": ""})
    def test_http_errors_are_redacted_and_not_retried(self):
        import urllib.error
        provider = OpenAIProvider()
        provider.bind_budget(Path(self.tmp.name))
        calls = []

        def fail(*args, **kwargs):
            calls.append(1)
            raise urllib.error.HTTPError(ENDPOINT, 401, "sensitive body", {"x-request-id": "req_test"},
                                         io.BytesIO(b'{"error":{"code":"invalid_api_key","type":"invalid_request_error","message":"secret"}}'))

        provider.opener.open = fail
        with self.assertRaises(ProviderHTTPError) as context:
            provider.complete({"prompt": "synthetic", "trial_id": "synthetic"}, None)
        self.assertEqual(context.exception.http_status, 401)
        self.assertNotIn("sensitive", str(context.exception))
        self.assertEqual(context.exception.provider_error_code, "invalid_api_key")
        self.assertEqual(context.exception.request_id, "req_test")
        self.assertNotIn("secret", str(vars(context.exception)))
        with self.assertRaises(ProviderHTTPError) as blocked:
            provider.complete({"prompt": "another synthetic trial", "trial_id": "another"}, None)
        self.assertFalse(blocked.exception.request_attempted)
        self.assertEqual(len(calls), 1)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-placeholder",
                             "OPENAI_BASE_URL": "https://example.invalid"})
    def test_custom_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            OpenAIProvider()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-placeholder", "OPENAI_BASE_URL": ""})
    def test_ledger_failure_after_response_preserves_attempted_flag(self):
        from touchstone.budget import BudgetError
        provider = OpenAIProvider()
        provider.bind_budget(Path(self.tmp.name))

        class Response(io.BytesIO):
            headers = {}

        provider.opener.open = lambda *args, **kwargs: Response(b'{"output":[],"status":"completed"}')
        provider.budget.finish = lambda *args, **kwargs: (_ for _ in ()).throw(BudgetError("locked"))
        with self.assertRaises(BudgetError) as context:
            provider.complete({"trial_id": "fixture", "prompt": "synthetic"}, None)
        self.assertTrue(context.exception.request_attempted)

    def test_explicit_provider_refusal_is_abstention(self):
        class Refused(Oracle):
            def complete(self, trial, case):
                return {"output": "cannot answer", "provider_refusal": True, "usage": None}

        with tempfile.TemporaryDirectory() as tmp:
            _, rows = run(Config(pairs=1, repetitions=1), Refused(), Path(tmp) / "run")
            self.assertTrue(all(row["score"]["abstention"] for row in rows))
            self.assertFalse(any(row["score"]["valid_completion"] for row in rows))
