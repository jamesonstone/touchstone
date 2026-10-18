# Running Touchstone

The package has no runtime dependencies. It needs Python 3.11+ on macOS or Linux
(POSIX locks). Kit and Make are development tools only. Install with `pip install .`;
the build backend is pinned in pyproject.toml. An installed `touchstone` command works
outside the checkout, without Git. Unknown Git revision is explicit; source hashes
still identify the code. Default configuration is built in; `--config path.json`
accepts seed, pairs, repetitions, order_seed (example: configs/pilot.json).

## Local and cloud

Use the same commands in a local virtual environment or an existing cloud runner:

```sh
touchstone plan --out plan.json
touchstone oracle --out runs/oracle
touchstone demo --out results
```

The optional Dockerfile packages the same command, with no credentials in the image:

```sh
docker build -t touchstone .
mkdir -p runs
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/runs:/runs" touchstone oracle --out /runs/oracle
```

Use a persistent volume containing **both run evidence and the shared budget ledger**
when moving/resuming work in cloud. An ephemeral filesystem can lose spending history.
No cloud provisioning or AWS account is required. GitHub CI builds/runs the same
container offline and tests an installed package outside its checkout.

## Live providers and credits

Only after credentials, billing/credit readiness and the run budget are approved:

```sh
touchstone openai --allow-live --out runs/openai-pilot
touchstone anthropic --allow-live --out runs/claude-pilot
```

Inject OPENAI_API_KEY or ANTHROPIC_API_KEY through the runtime's existing secure
secret/environment mechanism. Do not pass secret values in commands or commit env
files. For multi-workspace Anthropic keys, inject ANTHROPIC_WORKSPACE_ID too.
Custom endpoint overrides are rejected. No key creation, account linking, credit
claim, secret upload or billing changes are performed by this harness.

The local inventory has no genuine model results: six oracle runs and one failed
OpenAI attempt, 24 HTTP 401s. A later authorized diagnostic returned invalid_api_key.
ANTHROPIC_API_KEY was absent on 2026-10-18. The provided screenshots show Max 20x
API-credit eligibility with “Link organization” still present; they do not establish
credits claimed, API authentication or the billing organization. Purchased credits
and auto-reload are separate. Do not assume subscription usage pays for API calls.

| Adapter | Fixed model | Input / output USD per million | API settings |
| --- | --- | --- | --- |
| OpenAI Responses | gpt-4.1-mini-2025-04-14 | $0.40 / $1.60 | temperature .7, top-p 1, store=false |
| Anthropic Messages | claude-haiku-4-5-20251001 | $1 / $5 | temperature .7, thinking disabled, no tools/cache |

Both use 384 output tokens, a 30-second timeout and zero retries. These are historical
snapshots, not claims about latest models. Anthropic is legacy but currently documented
as available. Access is unverified. Verify pricing/availability before live execution.
The REST adapters avoid SDK retry defaults and additional dependencies.
[Messages/authentication](https://platform.claude.com/docs/en/api/overview),
[Haiku snapshot](https://platform.claude.com/docs/en/models/haiku-4-5/overview),
[Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing),
[OpenAI pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

## Budget, resume and the approved $5 effort

Ordinary pilots default to $0.10. Up to $1 may be explicitly selected with
`--budget-cents`; larger budgets up to the separately authorized $5 ceiling require
`--budget-ledger`. All runs in **this baseline effort**, including retries, reruns and
provider changes, must point at the same ledger and use the same policy:

```sh
# Plan first; do not execute live until secure key setup is confirmed.
touchstone openai --allow-live --config configs/smoke.json --budget-cents 500 \
  --budget-ledger runs/baseline-effort/budget.jsonl --out runs/pilot-1
# Resume preserves evidence and budget, never granting another $5:
touchstone openai --allow-live --resume --config configs/smoke.json --budget-cents 500 \
  --budget-ledger runs/baseline-effort/budget.jsonl --out runs/pilot-1
```

A conservative staged plan: first 6 requests (one pair, one repetition), inspect
outputs/scoring, then up to 18 requests using configs/expand.json on a different seed (three pairs, one
repetition) only if useful. The shared effort ledger conservatively keeps the
24-request ceiling across stages, so this plan does not need to spend all $5.
Estimated OpenAI reservations for 24 maximum-size prompts are below $0.064;
Anthropic's corresponding bound is below $0.169. Smaller prompts cost less, but
reservations never refund savings. No new live execution occurred in this refactor.

Before every request, the locked, fsynced ledger reserves UTF-8 prompt bytes plus
1,024 input overhead tokens, plus the full output cap, at verified uncached rates.
Unknown prices, damaged/missing/empty ledgers, mismatched policies, concurrent writers
and terminal authentication failures fail closed. Lost responses remain reserved.
Both providers share this accounting. Each ledger has a persistent UUID bound into
the run manifest: resume rejects a different ledger, even with identical settings,
while moving the original evidence and ledger together preserves identity. No retries run automatically; a resumed trial
consumes another reservation if its earlier response was lost. The ledger retains
usage and authentication-stop state across process restarts.

**This is a local estimate, not a key-level cap.** Other clients, different ledger
paths, deliberate ledger changes/deletion, pricing changes, taxes or server billing
are outside these controls. Reservations from parallel processes using the same ledger are serialized or
rejected; other clients cannot be governed by this package. Run this baseline
effort sequentially. Never run concurrent copies of a ledger. Never split the
approved effort across ledgers to reset its budget.

## Method and result artifacts

Capacity scheduling assigns four tasks to three slots under allowed-slot/capacity
constraints. An exhaustive solver supplies feasibility. Cases are seeded and paired
across the control, invariant and never_break wordings; only the framing sentence
changes. Oracle labels never enter prompts. Default: four cases × three wordings ×
two repeats = 24 trials. This tests full phrases, not one isolated word.

The strict scorer separates valid_schedule, correct_infeasible, constraint_violation,
incorrect_infeasible, format_error, abstention and provider_error. Only the first two
are completion. Duplicate keys, trailing prose, malformed JSON/schema and booleans
as slot indices are rejected. Refusing everything scores zero. Every planned trial,
including errors, stays in the denominator; reports split feasibility subgroups.

Runs write manifest.json (config/provider/source hashes), plan.json (prompts/order),
trials.jsonl (outputs/scores/latency/usage), report.json, report.md and results.svg.
No credentials or raw provider error messages are retained. Model outputs, errors,
refusals and usage are not fabricated when absent. `--resume` appends missing trials
only for the same config/plan/source and original ledger. It rejects corrupt evidence.
Raw run evidence stays ignored. The committed results/demo.* files are reproducible
reference fixtures, with no measured latency or model outputs; regenerate with
`touchstone demo --out results`. GitHub CI checks exact regeneration.

Reports use 4,000 seeded case-cluster bootstrap draws, retaining repetitions within
cases, for completion rates and paired deltas. Four cases cannot support universal
conclusions; degenerate oracle intervals do not establish model equivalence. No
multiple-comparison claim or combined score across unrelated benchmarks is made.
