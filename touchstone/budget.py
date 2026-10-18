"""Durable per-pilot reservations. Unknown outcomes retain their worst-case charge."""
from contextlib import contextmanager
from fractions import Fraction
import fcntl
import json
import math
import os
import uuid
from pathlib import Path

MODEL = "gpt-4.1-mini-2025-04-14"
# Standard text rates, USD per million tokens, verified in official docs 2026-10-18.
PRICES = {MODEL: (Fraction(2, 5), Fraction(8, 5)),
          "claude-haiku-4-5-20251001": (Fraction(1), Fraction(5))}
PRICING_URL = "https://developers.openai.com/api/docs/models/gpt-4.1-mini"
PRICING_SOURCES = {MODEL: PRICING_URL, "claude-haiku-4-5-20251001":
                   "https://platform.claude.com/docs/en/about-claude/pricing"}
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
    def __init__(self, path, model=MODEL, budget_cents=10, max_requests=24, output_cap=384, aggregate=False):
        if model not in PRICES:
            raise BudgetError("model has no verified price")
        if type(budget_cents) is not int or not 1 <= budget_cents <= 500:
            raise BudgetError("pilot budget must be 1–500 cents")
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
                       "pricing_source": PRICING_SOURCES[model], "pricing_verified": "2026-10-18"}
        if aggregate:
            self.policy.update(model="shared-priced-models-v1", input_usd_per_million=None,
                               output_usd_per_million=None, pricing_source=PRICING_SOURCES,
                               model_prices={k: [str(v) for v in rates] for k, rates in PRICES.items()})
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            created = False
        else:
            os.close(descriptor)
            created = True
        with locked_file(self.path) as stream:
            records = self.read(stream, allow_empty=created)
            if not records:
                self.identity = str(uuid.uuid4())
                self.append(stream, dict(self.policy, ledger_id=self.identity))
            else:
                self.identity = records[0]["ledger_id"]

    def read(self, stream, allow_empty=False):
        stream.seek(0)
        try:
            records = [json.loads(line) for line in stream]
        except (ValueError, TypeError):
            raise BudgetError("budget ledger is damaged; fail closed") from None
        if not records and not allow_empty:
            raise BudgetError("existing budget ledger is empty; refusing reset")
        if records:
            if not isinstance(records[0], dict):
                raise BudgetError("budget policy is damaged")
            stored = {k: v for k, v in records[0].items() if k != "ledger_id"}
            if stored != self.policy:
                raise BudgetError("existing budget policy differs; refusing reset")
            identity = records[0].get("ledger_id")
            try:
                uuid.UUID(identity)
            except (ValueError, TypeError, AttributeError):
                raise BudgetError("budget ledger identity missing or damaged") from None
            if identity != getattr(self, "identity", identity):
                raise BudgetError("budget ledger identity changed")
        self.validate_records(records[1:])
        return records

    def validate_records(self, records):
        reservations = []
        for record in records:
            if not isinstance(record, dict):
                raise BudgetError("damaged ledger record")
            kind = record.get("kind")
            if kind == "reservation":
                identifier, bound, model = (record.get(k) for k in ("id", "input_token_bound", "model"))
                if (type(identifier) is not int or identifier != len(reservations)
                        or type(bound) is not int or not OVERHEAD_TOKENS <= bound <= 4096 + OVERHEAD_TOKENS
                        or not isinstance(model, str) or model not in PRICES
                        or (self.policy["model"] != "shared-priced-models-v1" and model != self.model)
                        or not isinstance(record.get("trial_id"), str) or not record["trial_id"]):
                    raise BudgetError("damaged reservation record")
                expected = math.ceil(bound * PRICES[model][0] + self.policy["output_cap"] * PRICES[model][1])
                if type(record.get("reserved_micro_usd")) is not int or record["reserved_micro_usd"] != expected:
                    raise BudgetError("damaged reservation cost")
                reservations.append(record)
            elif kind == "usage":
                identifier, usage, status = (record.get(k) for k in ("reservation_id", "usage", "http_status"))
                if (type(identifier) is not int or not 0 <= identifier < len(reservations)
                        or (status is not None and (type(status) is not int or not 100 <= status <= 599))
                        or (usage is not None and (not isinstance(usage, dict)
                            or any(k not in ("input_tokens", "output_tokens", "total_tokens")
                                   or type(v) is not int or v < 0 for k, v in usage.items())))):
                    raise BudgetError("damaged usage record")
            elif kind == "terminal":
                if record.get("http_status") not in (401, 403):
                    raise BudgetError("damaged terminal record")
            else:
                raise BudgetError("unknown ledger record kind")
        if (len(reservations) > self.policy["max_requests"]
                or sum(r["reserved_micro_usd"] for r in reservations) > self.policy["budget_micro_usd"]):
            raise BudgetError("ledger exceeds original limits")

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
            if any(record.get("kind") == "terminal" or record.get("http_status") in (401, 403)
                   for record in records):
                raise BudgetError("pilot stopped after terminal authentication error")
            reservations = [r for r in records if r.get("kind") == "reservation"]
            if len(reservations) >= self.policy["max_requests"]:
                raise BudgetError("pilot request cap exhausted")
            if sum(r["reserved_micro_usd"] for r in reservations) + cost > self.policy["budget_micro_usd"]:
                raise BudgetError("insufficient remaining worst-case budget")
            identifier = len(reservations)
            self.append(stream, {"kind": "reservation", "id": identifier, "trial_id": trial_id,
                                 "input_token_bound": input_tokens, "model": self.model,
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
