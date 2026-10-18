"""Bounded historical OpenAI pilot; the existing environment supplies credentials."""
import copy
import json
import os
import re
import urllib.error
import urllib.request
from .budget import Budget, BudgetError

ENDPOINT = "https://api.openai.com/v1/responses"
MODEL = "gpt-4.1-mini-2025-04-14"
MAX_REQUESTS = 24
MAX_INPUT_BYTES = 4096
MAX_OUTPUT_TOKENS = 384


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", {}, None)


class ProviderHTTPError(RuntimeError):
    def __init__(self, status, request_attempted=True, code=None, error_type=None, request_id=None):
        super().__init__("Provider request failed; response body omitted")
        self.http_status = status
        self.request_attempted = request_attempted
        self.provider_error_code = code
        self.provider_error_type = error_type
        self.request_id = request_id


class OpenAIProvider:
    provenance = {
        "provider": "openai", "model": MODEL, "endpoint": ENDPOINT,
        "transport": "python-stdlib-urllib", "measured_model": True,
        "settings": {"temperature": .7, "top_p": 1, "max_output_tokens": MAX_OUTPUT_TOKENS,
                     "store": False, "stream": False, "tools": [], "tool_choice": "none",
                     "text": {"format": {"type": "text"}}, "truncation": "disabled",
                     "seed": None, "seed_support": "not sent; Responses has no seed parameter",
                     "history": "none", "timeout_seconds": 30, "max_retries": 0,
                     "service_tier": "default"},
        "limits": {"max_requests": MAX_REQUESTS, "max_prompt_utf8_bytes": MAX_INPUT_BYTES,
                   "estimated_max_usd": .10,
                   "budget_scope": "one pilot directory; no key-level hard cap",
                   "pricing_input_usd_per_million": .4, "pricing_output_usd_per_million": 1.6,
                   "pricing_source": "https://developers.openai.com/api/docs/models/gpt-4.1-mini",
                   "pricing_checked_utc_date": "2026-10-18"},
    }

    credential_env = "OPENAI_API_KEY"
    base_url_env = "OPENAI_BASE_URL"
    endpoint = ENDPOINT
    model = MODEL
    request_id_header = "x-request-id"

    def __init__(self, budget_cents=10, ledger_path=None):
        if not os.environ.get(self.credential_env):
            raise ValueError(f"{self.credential_env} is unavailable")
        if os.environ.get(self.base_url_env):
            raise ValueError("Custom endpoints are not allowed for this bounded pilot")
        self.provenance = copy.deepcopy(type(self).provenance)
        self.provenance["limits"]["estimated_max_usd"] = budget_cents / 100
        if budget_cents > 100 and ledger_path is None:
            raise BudgetError("budgets above $1 require a shared effort ledger")
        self.ledger_path = ledger_path
        if ledger_path is not None:
            self.provenance["limits"]["budget_scope"] = "shared effort ledger"
        self.budget_cents = budget_cents
        self.budget = None
        self.requests = 0
        self.terminal_http_status = None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def budget_path(self, directory):
        return self.ledger_path if self.ledger_path is not None else directory / "budget.jsonl"

    def bind_budget(self, directory):
        path = self.budget_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.budget = Budget(path, model=self.model, budget_cents=self.budget_cents,
                             aggregate=self.ledger_path is not None)

    def request_body(self, text):
        settings = self.provenance["settings"]
        body = {key: settings[key] for key in (
            "temperature", "top_p", "max_output_tokens", "store", "stream", "tools",
            "tool_choice", "text", "truncation", "service_tier")}
        return dict(body, model=self.model, input=[{"role": "user", "content": text}])

    def request_headers(self):
        return {"Content-Type": "application/json",
                "Authorization": "Bearer " + os.environ[self.credential_env]}

    parse_response = staticmethod(lambda raw, request_id: parse_response(raw, request_id))

    def complete(self, trial, case):
        if self.budget is None:
            raise BudgetError("live requests require a persistent pilot budget")
        if self.terminal_http_status is not None:
            raise ProviderHTTPError(self.terminal_http_status, request_attempted=False)
        if self.requests >= MAX_REQUESTS:
            raise ValueError("pilot request limit exceeded")
        text = trial["prompt"]
        if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
            raise ValueError("pilot input limit exceeded")
        reservation = self.budget.reserve(trial["trial_id"], text)
        self.requests += 1
        request = urllib.request.Request(
            self.endpoint, data=json.dumps(self.request_body(text)).encode(), method="POST",
            headers=self.request_headers())
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = json.loads(response.read(1_000_000))
                request_id = response.headers.get(self.request_id_header)
        except urllib.error.HTTPError as exc:
            status = exc.code
            request_id = safe_token(exc.headers.get(self.request_id_header)) if exc.headers else None
            try:
                error = json.loads(exc.read(65536)).get("error", {})
                code = safe_token(error.get("code")) if isinstance(error, dict) else None
                error_type = safe_token(error.get("type")) if isinstance(error, dict) else None
            except (ValueError, AttributeError):
                code = error_type = None
            finally:
                exc.close()
            if status in (401, 403):
                self.terminal_http_status = status
            self.budget.finish(reservation, http_status=status)
            raise ProviderHTTPError(status, code=code, error_type=error_type,
                                    request_id=request_id) from None
        parsed = self.parse_response(raw, request_id)
        self.budget.finish(reservation, usage=parsed.get("usage"))
        return parsed


def safe_token(value):
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) else None


def parse_response(raw, request_id):
    text = []
    refused = False
    for item in raw.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text.append(content["text"])
            elif content.get("type") == "refusal":
                refused = True
                text.append(content.get("refusal", ""))
    return {"output": "".join(text), "provider_refusal": refused, "request_attempted": True,
            "usage": raw.get("usage"), "response_id": raw.get("id"),
            "request_id": request_id, "returned_model": raw.get("model"),
            "response_status": raw.get("status"),
            "incomplete_details": raw.get("incomplete_details")}
