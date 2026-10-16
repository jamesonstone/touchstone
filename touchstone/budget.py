"""Durable per-pilot reservations. Unknown outcomes retain their worst-case charge."""
from contextlib import contextmanager
from fractions import Fraction
import fcntl
import json
import math
import os
from pathlib import Path

MODEL = "gpt-4.1-mini-2025-04-14"
# Standard text rates, USD per million tokens, verified in official docs 2026-10-16.
PRICES = {MODEL: (Fraction(2, 5), Fraction(8, 5))}
PRICING_URL = "https://developers.openai.com/api/docs/models/gpt-4.1-mini"
OVERHEAD_TOKENS = 1024


class BudgetError(RuntimeError):
    request_attempted = False


@contextmanager
def locked_file(path):
    """Stable inode + flock: serialize readers/writers without a replace race."""
    with Path(path).open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BudgetError("another process holds this pilot lock") from None
        try:
            yield stream
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class Budget:
    def __init__(self, path, model=MODEL, budget_cents=10, max_requests=24, output_cap=384):
        if model not in PRICES:
            raise BudgetError("model has no verified price")
        if type(budget_cents) is not int or not 1 <= budget_cents <= 100:
            raise BudgetError("pilot budget must be 1–100 cents")
        if type(max_requests) is not int or not 1 <= max_requests <= 24:
            raise BudgetError("pilot request cap must be 1–24")
        if type(output_cap) is not int or not 1 <= output_cap <= 384:
            raise BudgetError("output cap must be 1–384 tokens")
        self.path = Path(path)
        self.model = model
        self.policy = {"kind": "policy", "schema_version": 1, "model": model,
                       "budget_micro_usd": budget_cents * 10000,
                       "max_requests": max_requests, "output_cap": output_cap,
                       "input_overhead_tokens": OVERHEAD_TOKENS,
                       "input_usd_per_million": str(PRICES[model][0]),
                       "output_usd_per_million": str(PRICES[model][1]),
                       "pricing_source": PRICING_URL, "pricing_verified": "2026-10-16"}
        with locked_file(self.path) as stream:
            records = self.read(stream)
            if not records:
                self.append(stream, self.policy)
            elif records[0] != self.policy:
                raise BudgetError("existing budget policy differs; refusing reset")

    def read(self, stream):
        stream.seek(0)
        try:
            records = [json.loads(line) for line in stream]
        except (ValueError, TypeError):
            raise BudgetError("budget ledger is damaged; fail closed") from None
        if records and records[0] != self.policy:
            raise BudgetError("existing budget policy differs; refusing reset")
        return records

    @staticmethod
    def append(stream, record):
        stream.seek(0, 2)
        stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())

    def reserve(self, trial_id, prompt):
        byte_count = len(prompt.encode("utf-8"))
        if byte_count > 4096:
            raise BudgetError("prompt exceeds 4096 UTF-8 bytes")
        input_tokens = byte_count + OVERHEAD_TOKENS
        input_rate, output_rate = PRICES[self.model]
        cost = math.ceil(input_tokens * input_rate + self.policy["output_cap"] * output_rate)
        with locked_file(self.path) as stream:
            records = self.read(stream)
            if any(record.get("kind") == "terminal" for record in records):
                raise BudgetError("pilot stopped after terminal authentication error")
            reservations = [r for r in records if r.get("kind") == "reservation"]
            if len(reservations) >= self.policy["max_requests"]:
                raise BudgetError("pilot request cap exhausted")
            if sum(r["reserved_micro_usd"] for r in reservations) + cost > self.policy["budget_micro_usd"]:
                raise BudgetError("insufficient remaining worst-case budget")
            identifier = len(reservations)
            self.append(stream, {"kind": "reservation", "id": identifier, "trial_id": trial_id,
                                 "input_token_bound": input_tokens,
                                 "reserved_micro_usd": cost})
            return identifier

    def finish(self, identifier, usage=None, http_status=None):
        # Never refund reservations: timeouts, lost responses and resumes remain bounded.
        with locked_file(self.path) as stream:
            self.read(stream)
            safe_usage = None
            if isinstance(usage, dict):
                safe_usage = {k: v for k, v in usage.items() if k in (
                    "input_tokens", "output_tokens", "total_tokens") and type(v) is int and v >= 0}
            self.append(stream, {"kind": "usage", "reservation_id": identifier,
                                 "usage": safe_usage, "http_status": http_status})
            if http_status in (401, 403):
                self.append(stream, {"kind": "terminal", "http_status": http_status})
