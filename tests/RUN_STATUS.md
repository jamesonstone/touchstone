# Run status — 2026-10-16

- PASS: 24 native unittest tests, including solver/scorer enumeration over 80 cases.
- PASS: 24-attempt oracle integration, four unique cases, three wordings, two repeats.
  Each condition completed 8/8 (four feasible, four infeasible); this is plumbing
  evidence only, not a model score. Local evidence: tmp/2026-10-16/oracle-1/.
- PASS: kit check --project; kit check --all.
- PASS: final make check after documentation updates (system Python 3.9.6).
- PASS: make check with Homebrew Python 3.13 and oracle CLI on Python 3.13.
- PENDING: GitHub Actions runtime on Python 3.11–3.13.
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
