# touchstone
🪨 Personal Benchmark of LLM Performance and Efficiency

<!-- BEGIN KIT-MANAGED README BADGES -->
[![Last commit](https://img.shields.io/github/last-commit/jamesonstone/touchstone)](https://github.com/jamesonstone/touchstone/commits) [![Open issues](https://img.shields.io/github/issues/jamesonstone/touchstone)](https://github.com/jamesonstone/touchstone/issues) [![Pull requests](https://img.shields.io/github/issues-pr/jamesonstone/touchstone)](https://github.com/jamesonstone/touchstone/pulls) [![CI](https://github.com/jamesonstone/touchstone/actions/workflows/tests.yml/badge.svg)](https://github.com/jamesonstone/touchstone/actions/workflows/tests.yml) [![Release](https://img.shields.io/github/v/release/jamesonstone/touchstone)](https://github.com/jamesonstone/touchstone/releases)
<!-- END KIT-MANAGED README BADGES -->

Touchstone is Jameson Stone's collection of independent, testable model benchmarks.
Each experiment has its own task definition and scores. There is no combined score
across unrelated benchmarks.

## First experiment: constraint wording

Does calling a constraint an **invariant** change behavior compared with calling it
**a rule you must never break**? A neutral “Scheduling constraints:” control uses
the same operative rules and output schema. Only the framing sentence changes.
This tests those complete phrases; it cannot isolate one word or prove equivalence.

The first task family is synthetic capacity scheduling: assign four tasks to three
slots, obey allowed slots, and keep each slot within capacity. An exhaustive solver
establishes feasibility. Seeded generation supplies equal numbers of guaranteed
feasible and infeasible cases. Oracle labels and case identifiers never enter the
model prompt. Every wording sees the same cases and repetitions in seeded shuffled
order; requests are independent, with no conversation history.

## Run locally

Requires Python 3.11 or later, Git, and Make. No Python dependencies or paid API calls
are required for deterministic validation. Kit is needed for project contract checks.

```sh
make help
make test
make check
python3 -m touchstone plan --out /tmp/touchstone-plan.json
python3 -m touchstone oracle --out tmp/my-oracle-run
```

Output paths must be new. Runs never overwrite previous evidence. The default
`configs/pilot.json` defines 24 attempts: two feasible/infeasible case pairs,
three wording conditions, and two repetitions. Configuration keys are `seed`,
`pairs`, `repetitions`, and `order_seed`. Cases and repetitions are bounded to
1–100 each. Seeded order reproduces the plan; it does not make model output deterministic.

The oracle command validates the harness with a reference solver. **It is not a
measured model baseline.** The plan command exports prompts for inspection without
making a model request. No live API adapter is enabled in this first offline pass:
the credential choice is pending. A provider adapter can implement
`complete(trial, case)` and expose `provenance`; see `touchstone/experiment.py`.
For model adapters, use only `trial["prompt"]` as model input; the case and feasibility
metadata belong to the offline scorer and must never be sent as hidden hints.

## Scoring contract

Answers must be one JSON object with exactly the documented fields. Strict parsing
rejects Markdown fences, duplicate keys, extra fields, non-finite numbers, booleans
or floats as slot indices, and trailing prose. Nothing from an answer is executed.

| Outcome | Meaning | Successful completion |
| --- | --- | --- |
| `valid_schedule` | Complete assignment satisfying every constraint | Yes |
| `correct_infeasible` | Infeasibility claim confirmed by exhaustive solver | Yes |
| `constraint_violation` | Missing/unknown tasks, disallowed slots or capacity breach | No |
| `incorrect_infeasible` | Feasible task falsely declared infeasible | No |
| `format_error` | Invalid JSON/schema, including unstructured refusal text | No |
| `abstention` | Explicit `{"status":"abstain"}` | No |
| `provider_error` | Adapter/request failure | No |

The completion denominator includes every planned attempt, including errors and
abstentions. Reports also split feasible and infeasible cases. An always-abstain
provider scores zero; it cannot win by avoiding constraint violations.

## Evidence and interpretation

Each local run writes ignored evidence under the selected output directory:

- `manifest.json`: benchmark/scorer/package versions, source file hashes, Git
  revision, Python version, UTC timestamp, provider/model/settings provenance,
  config and plan hashes. Source hashes identify uncommitted code too.
- `plan.json`: ordered trial IDs, synthetic cases, exact prompts and prompt hashes.
- `trials.jsonl`: one flushed row per attempt, output, outcome/reasons, elapsed
  seconds, provider response identifier and token usage when available. Missing
  usage is `null`, never a fabricated zero. Provider exception messages are omitted
  because they can contain credentials.
- `report.json` and `report.md`: denominators, all outcome counts, completion rates,
  feasibility subgroups, paired wording-minus-control differences, and uncertainty.

Hashes use SHA-256 over canonical JSON (sorted keys, compact separators, UTF-8);
source hashes use raw file bytes. The manifest identifies hash conventions in code.
Reports use 4,000 seeded bootstrap draws over unique cases, retaining repetitions
within each case. These are descriptive percentile 95% intervals. Repetitions are
not independent cases. Four cases cannot support a universal conclusion; degenerate
intervals are not evidence of equivalence. There is no multiple-comparison claim.
Synthetic distributions are narrow, with structurally simple infeasibility cases.
Broader generators and a preregistered larger sample are future experiments.

The runner records each request as attempted. It has no automatic retries. An
interrupted run may have fewer rows than planned; preserve that evidence and start
another run in a new directory. The CLI emits reports only after a complete run.

## Live pilot status and safety

A genuine model baseline has **not run**. An ambient OpenAI key is present, but the
required reuse-versus-new credential decision is pending. Do not infer that the
oracle scores measure a language model. Proposed pilot scope: 24 requests, one
explicit model snapshot, one explicit settings configuration, no retries, synthetic
prompts only, and a reviewed output-token/cost cap before invocation. Cost is UNKNOWN
until model and provider are selected. Provenance must record the requested model,
returned model/version when available, endpoint/provider, every sampling setting,
output cap, and token usage. Never record credential values or request headers.

The exact requested AWS location is `foundary-dev`. That profile is absent locally;
`foundry-dev` exists but is not an approved substitute. AWS account and region are
UNKNOWN. Therefore no AWS context is invented in `.kit.yaml`, and no AWS resource
or data is accessed. To activate AWS later, confirm the exact profile/account/region,
configure the canonical Kit AWS context and run `kit aws verify` before AWS work.
No production or LSMC resources, uploads, IAM changes, or persistent compute are
part of this first pass.

## CI and repository operation

`.github/workflows/tests.yml` runs deterministic tests and an oracle integration
on Python 3.11–3.13 without credentials or paid calls. Oracle artifacts have seven-day
retention. Kit also generated its canonical assignment workflow and review files;
these remain unchanged. GitHub runtime results must be reported separately from
local validation.

See `docs/references/testing.md`, `tests/RUN_STATUS.md`, and the feature spec at
`docs/specs/0001-constraint-wording/SPEC.md` for observed validation and known gaps.
The task-specific user instructions authorize work in the existing clone with no
worktree, no tracking issue, and a PR without merge; canonical Kit rules remain intact.

## Maintainers

Maintained by [jamesonstone](https://github.com/jamesonstone).
