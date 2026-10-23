import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from touchstone.anthropic_provider import AnthropicProvider, MODEL
from touchstone.budget import BudgetError
from touchstone.experiment import Config
from touchstone.publish import chart, demo


class PortableTests(unittest.TestCase):
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "offline-placeholder", "ANTHROPIC_BASE_URL": "",
                             "ANTHROPIC_WORKSPACE_ID": "workspace-offline"})
    def test_anthropic_uses_same_durable_budget_and_prompt_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = AnthropicProvider()
            provider.bind_budget(Path(tmp))
            observed = []

            class Response(io.BytesIO):
                headers = {"request-id": "req_fixture"}

            def fake_open(request, timeout):
                observed.append(request)
                return Response(json.dumps({"id": "msg_fixture", "model": MODEL,
                    "content": [{"type": "text", "text": '{"status":"abstain"}'}],
                    "stop_reason": "end_turn", "usage": {"input_tokens": 20, "output_tokens": 6}}).encode())

            provider.opener.open = fake_open
            response = provider.complete({"trial_id": "fixture", "prompt": "synthetic"}, None)
            body = json.loads(observed[0].data)
            self.assertEqual(body["max_tokens"], 384)
            self.assertEqual(body["thinking"], {"type": "disabled"})
            self.assertEqual(body["messages"], [{"role": "user", "content": "synthetic"}])
            self.assertEqual(observed[0].get_header("Anthropic-version"), "2023-06-01")
            self.assertEqual(observed[0].get_header("X-api-key"), "offline-placeholder")
            self.assertEqual(response["usage"]["total_tokens"], 26)
            ledger = (Path(tmp) / "budget.jsonl").read_text()
            self.assertIn(MODEL, ledger)
            self.assertNotIn("offline-placeholder", ledger)
            self.assertFalse(response["provider_refusal"])
            self.assertTrue(provider.parse_response({"stop_reason": "refusal"}, None)["provider_refusal"])

    def test_reproducible_demo_is_visibly_not_model_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            demo(Config(), target)
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            demo(Config(), target)
            self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
            report = json.loads((target / "demo.json").read_text())
            self.assertFalse(report["measured_model"])
            self.assertEqual(report["observed_model_outputs"], 0)
            self.assertIsNone(report["total_latency_seconds"])
            ET.fromstring(chart(report))
            self.assertIn("NOT MODEL RESULTS", chart(report))
            report.update(measured_model=True, baseline_status="BLOCKED_NO_MODEL_OUTPUT")
            self.assertIn("NO MODEL OUTPUTS", chart(report))

    def test_cli_uses_defaults_and_no_git_from_another_directory(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=str(root), PATH="")
            result = subprocess.run([sys.executable, "-m", "touchstone", "oracle", "--out", str(Path(tmp)/"run")],
                                    cwd=tmp, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((Path(tmp)/"run/manifest.json").read_text())
            self.assertEqual(manifest["revision"], "unknown")
            self.assertTrue((Path(tmp)/"run/results.svg").is_file())
            denied = subprocess.run([sys.executable, "-m", "touchstone", "anthropic", "--out", str(Path(tmp)/"paid")],
                                    cwd=tmp, env=env, capture_output=True, text=True)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn("--allow-live", denied.stderr)
            self.assertFalse((Path(tmp)/"paid").exists())

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "offline-placeholder", "ANTHROPIC_BASE_URL": ""})
    def test_five_dollar_scope_requires_shared_ledger(self):
        with self.assertRaises(BudgetError):
            AnthropicProvider(budget_cents=500)
