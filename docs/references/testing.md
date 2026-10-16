# Testing Reference

## Code-Level Validation

| Layer | Command | Automation | Required |
| --- | --- | --- | --- |
| Python unit/integration | `make test` | Deterministic tests / test, Python 3.11–3.13 | Yes |
| Kit project contract | `kit check --project` | Local `make check` | Yes |
| Kit feature memory | `kit check --all` | Local `make check` | Yes |

`make help` lists real commands. `make check` runs all three checks. No third-party
Python dependencies, server, database, credentials or network access are needed.
The scorer suite independently enumerates 81 candidate assignments for each of
80 generated cases (20 seeds, two pairs each), in addition to malformed JSON,
duplicate keys, schema and type errors, every outcome and refusal/error controls.

## High-Level Suites

Run `python3 -m touchstone oracle --out tmp/<UTC-date>/oracle-<number>`.
This validates full evidence generation and reporting; it is an oracle plumbing test,
not a measured model baseline. New run paths must not exist; --resume verifies the original plan/configuration/source
and budget, then appends only missing trials. CI runs the same command
under `tmp/ci-oracle` and uploads oracle artifacts for seven days.

## Environment Preflights

Local tests need Python 3.11+, Make and Git. Kit checks need Kit v3.0.45 or a
compatible release. No deployed environment applies: this is a local harness.
Production and LSMC resources/data are out of scope. AWS is blocked because the
exact requested profile foundary-dev is absent; account/region remain UNKNOWN.
Never substitute foundry-dev. Configure verified Kit AWS context before any AWS work.

## Credentials And Test Data

Only synthetic scheduling inputs are used. Existing OPENAI_API_KEY reuse was approved. The bounded historical OpenAI adapter
was exercised for 24 requests; all returned HTTP 401, with no model outputs or token
usage. Credentials were used in memory only. The model is fixed to
gpt-4.1-mini-2025-04-14, temperature 0.7, top-p 1, max_output_tokens 384, no tools,
no history, store=false and no retries. Default local budget is $0.10 (CLI maximum $1), reserving worst-case costs
before every request using verified pricing. Unknown prices fail closed. Persistent
reservations survive restart and are never refunded; retries default to zero.
Tests cover interrupted requests, concurrency locks, corrupted/missing ledgers and
authentication stops. This is not a key-level spending cap. No secret values belong in source or evidence.

## Evidence And Retention

Local evidence is retained in ignored tmp/ directories; do not commit raw generated
runs. Unit tests use temporary directories. tests/RUN_STATUS.md tracks milestones.
The manifest records source hashes as well as Git revision so dirty code is identifiable.
Provider usage is null when unavailable. Errors stay in planned denominators.

## Automation And Fallbacks

GitHub Actions uses no provider credentials and no paid model calls. Kit checks run
locally; the workflow does not download an unpinned Kit binary. A live pilot is manual
only with explicit --allow-live and authorized credentials. Never label a mock/oracle as baseline.

## Known Gaps

Live model baseline: BLOCKED by HTTP 401 authentication failure. AWS verification: BLOCKED on
exact target. Python 3.11–3.13 hosted CI passed on PR #1 head 3738712;
any subsequent head must pass its own run before merge. No production
validation is applicable. Tiny-case bootstrap intervals do not establish equivalence.
