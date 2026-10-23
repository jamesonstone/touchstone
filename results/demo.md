# Oracle plumbing test (not a model baseline)

Benchmark: `capacity-scheduling-v1`.

| Wording | Completed / planned trials | Unique cases | Case-bootstrap 95% interval |
| --- | --- | --- | --- |
| control | 8 / 8 | 4 | [1.0, 1.0] |
| invariant | 8 / 8 | 4 | [1.0, 1.0] |
| never_break | 8 / 8 | 4 | [1.0, 1.0] |

Percentile case-cluster bootstrap, 4000 draws, seed 12345. Repeats are not independent cases. Tiny samples and degenerate intervals cannot establish equivalence or a population effect. No multiple-comparison inference.

## Paired completion differences versus control

- invariant: 0.0; 95% interval [0.0, 0.0]; 4 paired cases.
- never_break: 0.0; 95% interval [0.0, 0.0]; 4 paired cases.

Observed model outputs: 0; token usage: None.
Zero completions caused entirely by provider errors do not measure model ability.
See report.json for every outcome count and feasibility denominator.
All planned attempts, including provider errors, remain in the denominator.
No overall score combines unrelated benchmarks.
