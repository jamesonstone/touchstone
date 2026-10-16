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
not a measured model baseline. Run paths must not exist. CI runs the same command
under `tmp/ci-oracle` and uploads oracle artifacts for seven days.

## Environment Preflights

Local tests need Python 3.11+, Make and Git. Kit checks need Kit v3.0.45 or a
compatible release. No deployed environment applies: this is a local harness.
Production and LSMC resources/data are out of scope. AWS is blocked because the
exact requested profile foundary-dev is absent; account/region remain UNKNOWN.
Never substitute foundry-dev. Configure verified Kit AWS context before any AWS work.

## Credentials And Test Data

Only synthetic scheduling inputs are used. OPENAI_API_KEY presence was checked
without reading its value. Reuse versus creation is PENDING, so no live API adapter
or model call is authorized yet. Proposed live pilot: 24 independent requests on
one selected model/settings configuration, no retries, reviewed token/cost bounds.
Cost remains UNKNOWN until model choice. No secret values belong in source or evidence.

## Evidence And Retention

Local evidence is retained in ignored tmp/ directories; do not commit raw generated
runs. Unit tests use temporary directories. tests/RUN_STATUS.md tracks milestones.
The manifest records source hashes as well as Git revision so dirty code is identifiable.
Provider usage is null when unavailable. Errors stay in planned denominators.

## Automation And Fallbacks

GitHub Actions uses no provider credentials and no paid model calls. Kit checks run
locally; the workflow does not download an unpinned Kit binary. A live pilot is manual
only after credential and model/cost decisions. Never label a mock/oracle as baseline.

## Known Gaps

Live model baseline: BLOCKED on credential choice. AWS verification: BLOCKED on
exact target. Python 3.11–3.13 CI runtime: PENDING until GitHub runs. No production
validation is applicable. Tiny-case bootstrap intervals do not establish equivalence.
