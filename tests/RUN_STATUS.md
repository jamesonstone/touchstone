# Portable refactor status — 2026-10-18

- PASS: 35 deterministic tests and both Kit checks on Python 3.13.
- PASS: clean virtual-environment package install; installed CLI outside checkout.
- PASS: local Docker build and offline demo; artifacts match source demo byte-for-byte.
- PASS: SVG rendered and visually inspected; oracle-demo label is prominent.
- PASS: tests cover Anthropic request schema/headers/usage, no-live opt-in, shared
  budget accounting across models, and resume rejection of substituted ledgers.
- PASS: independent re-review confirmed ledger substitution fix; reviewer ran all 32 tests.
- PASS: original draft-head hosted Python 3.11–3.13 and portability/container CI
  (run 39122271698). Post-review head CI remains PENDING before ready-for-review.
- PASS: review fixes reject semantically damaged ledger records, classify provider-
  declared failures separately from model format errors, preserve attempted-request
  metadata after ledger errors, and report zero oracle network requests.
- PASS: independent re-review confirmed all fixes; reviewer independently ran 35 tests.
- PENDING: final-head hosted CI, then ready-for-review transition. No merge authorized.
- BLOCKED: genuine baseline; secure OpenAI key setup is parent-owned and pending.
  Seven saved runs were inspected: six oracle runs and one failed OpenAI attempt;
  zero actual model outputs. No live calls were made during the refactor.
- BLOCKED: Anthropic API key absent; organization-linked API credits not verified.

## Historical validation — 2026-10-16

- PASS: 26 native unittest tests, including solver/scorer enumeration over 80 cases.
- PASS: 24-attempt oracle integration, four unique cases, three wordings, two repeats.
  Each condition completed 8/8 (four feasible, four infeasible); this is plumbing
  evidence only, not a model score. Local evidence: tmp/2026-10-16/oracle-1/.
- PASS: kit check --project; kit check --all.
- PASS: final make check after documentation updates (system Python 3.9.6).
- PASS: make check with Homebrew Python 3.13 and oracle CLI on Python 3.13.
- PASS: GitHub Actions Python 3.11–3.13 on head 3738712, run 38965322688.
  A changed head must pass its own CI before merge.
- PASS: independent correctness review; both ledger recovery findings fixed
  (empty existing ledger reset and authentication-stop crash window). Reviewer
  independently reran all 26 tests and found no remaining blocker.
- PASS: durable budget tests: reserve before call, crash/restart without refund,
  same-budget resume, terminal-auth persistence, unknown-price rejection and locks.
- PASS: oracle CLI integration and explicit resume at tmp/2026-10-16/oracle-budget/.
- BLOCKED: genuine model baseline. Existing-key reuse was approved, but 24/24
  bounded OpenAI requests returned HTTP 401. There were zero model outputs and no
  reported token usage. This is access-failure evidence, not a model score.
  A subsequent single approved diagnostic identified invalid_api_key /
  invalid_request_error (HTTP 401); no further requests followed. New secure key
  setup is managed separately and remains PENDING.
  Evidence: tmp/2026-10-16/openai-pilot-1/. No requests repeated.
- PASS: adapter tests prove prompt-only requests, token/request limits, fixed
  endpoint, no retries, redacted errors and stop-after-authentication-failure.
- PASS: explicit provider refusal scores as abstention and never as completion.
- BLOCKED: AWS identity; exact profile foundary-dev absent, account/region UNKNOWN.

Oracle interval [1, 1] and paired differences 0 are deterministic reference behavior.
They are not empirical evidence of language-model equivalence. Raw ignored run
artifacts remain on this Mac. No secrets, real user inputs, or customer data were used.
