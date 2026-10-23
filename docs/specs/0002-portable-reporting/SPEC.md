---
kit_metadata_version: 1
artifact: "spec"
workflow_version: 3
phase: "deliver"
feature:
  id: "0002"
  slug: "portable-reporting"
  dir: "0002-portable-reporting"
---
# SPEC

## PURPOSE

Reduce the README to a short entrypoint with honest results visuals, package the harness for identical local/cloud commands, and add minimal Anthropic support without weakening spending controls.

## CONTEXT

Clean main at e3aa255. Seven saved runs contain oracle demonstrations and an OpenAI authentication failure, with zero genuine model outputs. No active PRs or other changes. No .agents directory exists. User requires a focused draft PR without merge and no account linking, billing changes, cloud provisioning or credential transmission.

## REQUIREMENTS

Keep README purpose, quickstart, results and references, with Maintainers last. Generate Markdown-compatible result visuals reproducibly from offline evidence and label oracle fixtures as demonstrations. Work from a clean checkout or installed package outside the repo. Preserve 24-request, 384-output-token, zero-retry and durable budget safeguards; ordinary default remains $0.10. User separately authorizes a $5 total baseline effort across runs, not per-run resets; live execution waits for secure credentials.

## ACCEPTED PLAN

Use Python packaging with zero runtime dependencies and a small optional container recipe. Keep the same CLI for local/cloud execution, bundle/default the experiment config, and make Git optional. Share bounded HTTP transport for OpenAI and Anthropic Messages. Add a deterministic oracle fixture/export command producing JSON, Markdown tables and SVG charts. Add a shared budget-ledger option for aggregate baseline accounting. Validate existing tests plus focused provider/portability/report tests and CI; obtain fresh read-only review; open draft PR, no merge.

## DECISIONS

Use raw official REST APIs through the existing standard-library transport to avoid SDK installation/retry defaults. Use a fixed priced Claude Haiku 4.5 snapshot with thinking disabled. Keep demo and measured results visibly distinct. Do not claim subscriber credits are linked/claimed or that local limits cap a key.

## DISCOVERIES

ANTHROPIC_API_KEY is absent. API-credit screenshot state does not establish usable API access. Anthropic pricing and Messages/authentication docs were read; no account action or live call is needed for implementation.

## VALIDATION

PASS: 35 tests; both Kit checks; clean virtual-environment install and CLI from /tmp without repo-relative config; local Docker build/run with exact demo artifact regeneration; SVG rendered and inspected. Fresh reviewer found a shared-ledger substitution flaw; fixed with persistent ledger identity and a regression test. Independent re-review confirmed the fix and reran all 32 tests successfully. Fresh explicit user approval resolves the prior commit/push restriction. Draft PR #2 is published; original-head CI passed (run 39122271698). Comprehensive review added semantic ledger validation, correct provider-declared-failure classification and zero oracle network-request reporting. Local regression suite and independent re-review pass all 35 tests with no remaining blocker. Final-head CI is pending before the user-authorized ready-for-review transition. No merge is authorized.

## OUTCOME

Portable offline refactor is implemented. README reduced from 188 to 44 lines; deterministic oracle artifacts clearly state NOT MODEL RESULTS. Both provider transports use runtime credentials and the same durable spend controls. User explicitly authorized a $5 total effort ceiling; ordinary defaults remain $0.10, 24 requests, 384 output tokens and zero retries. Shared ledger identity prevents budget reset on resume. Genuine baseline remains blocked on secure key readiness; parent owns provisioning. Anthropic credits/linking remain unverified. User now explicitly requests ready-for-review after clean code review and final-head checks; no merge.

## REPOSITORY MEMORY

Create this feature spec and one concise usage/reference document; preserve Kit-owned contract/rules and keep prior benchmark memory as history.
