---
kit_metadata_version: 1
artifact: "spec"
workflow_version: 3
phase: "blocked"
feature:
  id: "0001"
  slug: "constraint-wording"
  dir: "0001-constraint-wording"
---
# SPEC

## PURPOSE

Measure whether equivalent constraint framing changes task completion in one synthetic scheduling experiment. Touchstone is a collection of unrelated benchmarks authored by Jameson, not a single leaderboard.

## CONTEXT

The repository contained only a README. Kit v3.0.45 initialized the canonical contract and rules. User requires the existing clone, no worktrees, and authorizes a feature branch and PR but no merge. No existing work was changed. The requested exact AWS profile foundary-dev is absent; foundry-dev must not be substituted.

## REQUIREMENTS

Use deterministic seeded feasible/infeasible scheduling cases and an exhaustive reference solver. Pair all wording variants and repeats on identical cases, randomize trial order, record explicit provenance, prompt/config/source hashes, outputs, scores, latency and token usage when supplied. Separate completion, violation, format error, abstention, false infeasibility and provider error. Refusal is never success. Keep paid calls out of CI. A genuine live pilot requires authorized model access.

## ACCEPTED PLAN

Implement a standard-library Python package with task generation, reference solver, strict scorer, provider-independent runner, descriptive per-condition reports and paired case-cluster bootstrap intervals. Exercise invalid outputs and end-to-end evidence with native unittest. Keep oracle controls clearly marked as plumbing tests. Initialize Kit, document commands and limitations, then validate and deliver the requested PR.

## DECISIONS

Use one small task family first. Vary only the introductory framing sentence; retain all operative constraints verbatim. Count every attempted trial in denominators, including provider errors. Use case clusters for repeated-trial uncertainty. Do not infer a universal wording effect or combine independent benchmarks. Do not modify canonical Kit rules to accommodate task-specific exceptions.

## DISCOVERIES

The exact AWS profile foundary-dev is not configured. An ambient OpenAI key is present, but reuse versus creation remains a required decision before API work. No cloud resource, upload, IAM change or persistent compute is needed for offline evaluation.

## VALIDATION

PASS: 12 unittest tests, including independent exhaustive solver/scorer validation across 80 cases; make check (unit tests plus kit check --project and kit check --all); make help; plan export of 24 trials; 24-trial oracle CLI integration. Local Python 3.9.6 and Homebrew Python 3.13 were exercised. Oracle evidence is retained under ignored tmp/2026-10-16/oracle-1/ and oracle-py313/. GitHub Actions runtime remains PENDING before PR publication.

## OUTCOME

Offline first version is implemented and locally validated. The genuine model baseline remains BLOCKED on the credential decision; AWS verification remains BLOCKED on exact foundary-dev configuration and target confirmation. No paid calls or AWS operations ran. Oracle outputs are plumbing evidence only. Repository settings were independently re-read: automatic merged-head deletion true; main allow_deletions false and allow_force_pushes false, enforced for administrators, public visibility unchanged. Feature branch initial-benchmark follows the explicit no-issue/no-worktree task instructions; no merge is authorized.

## REPOSITORY MEMORY

Created this feature spec. Updated README and testing reference for commands, evidence and limits. Retained Kit-generated contract and contextual rules unchanged.
