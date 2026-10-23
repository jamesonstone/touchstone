"""Claude Messages API over the same no-retry, reserved-budget transport."""
import os
from .openai_provider import OpenAIProvider

MODEL = "claude-haiku-4-5-20251001"
ENDPOINT = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(OpenAIProvider):
    credential_env = "ANTHROPIC_API_KEY"
    base_url_env = "ANTHROPIC_BASE_URL"
    endpoint = ENDPOINT
    model = MODEL
    request_id_header = "request-id"
    provenance = {
        "provider": "anthropic", "model": MODEL, "endpoint": ENDPOINT,
        "transport": "python-stdlib-urllib", "measured_model": True,
        "settings": {"max_tokens": 384, "temperature": .7, "thinking": {"type": "disabled"},
                     "stream": False, "history": "none", "tools": "not sent",
                     "timeout_seconds": 30, "max_retries": 0, "anthropic_version": "2023-06-01"},
        "limits": {"max_requests": 24, "max_prompt_utf8_bytes": 4096,
                   "estimated_max_usd": .10, "budget_scope": "one pilot directory",
                   "pricing_input_usd_per_million": 1, "pricing_output_usd_per_million": 5,
                   "pricing_source": "https://platform.claude.com/docs/en/about-claude/pricing",
                   "pricing_checked_utc_date": "2026-10-18"},
    }

    def request_body(self, text):
        return {"model": self.model, "max_tokens": 384, "temperature": .7,
                "thinking": {"type": "disabled"}, "stream": False,
                "messages": [{"role": "user", "content": text}]}

    def request_headers(self):
        headers = {"Content-Type": "application/json", "anthropic-version": "2023-06-01",
                   "x-api-key": os.environ[self.credential_env]}
        if os.environ.get("ANTHROPIC_WORKSPACE_ID"):
            headers["anthropic-workspace-id"] = os.environ["ANTHROPIC_WORKSPACE_ID"]
        return headers

    @staticmethod
    def parse_response(raw, request_id):
        usage = raw.get("usage")
        if isinstance(usage, dict):
            usage = {**usage, "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)}
        return {"output": "".join(c["text"] for c in raw.get("content", []) if c.get("type") == "text"),
                "provider_refusal": raw.get("stop_reason") == "refusal", "request_attempted": True,
                "provider_failure": raw.get("type") == "error",
                "usage": usage, "response_id": raw.get("id"), "request_id": request_id,
                "returned_model": raw.get("model"), "response_status": raw.get("stop_reason")}
