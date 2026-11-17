# Validation results

Recorded 2026-11-18 on Windows with Python 3.11, Rust 1.93.0, FastAPI 0.115.6, Uvicorn 0.34.0, and HTTPX 0.26.0.

## Local implementation checks

- Seven fixture tests reproduce the three planted failures, preserve the protected decoy, check authentication and input validation, and verify reset behavior.
- Nine CLI integration tests exercise credential separation, output redaction, redirect suppression, truncation handling, stop-on-failure without retry, required scope declaration, scope mismatch rejection, preflight credential validation, output preservation, and findings-log validation (some tests cover multiple properties).
- Three Rust unit tests check finding evidence requirements, duplicate rejection, and URL/transport restrictions.
- One evaluator test checks that the original fixture fails and a minimally corrected application passes the patch oracle.
- One end-to-end test runs the Rust helper against the actual FastAPI application over loopback and checks owner, peer, and anonymous observations.
- Rust compilation, formatting, and Clippy validation are part of the release checks.
- The evaluator patch checker correctly rejects the three unfixed bugs while accepting the preserved admin, authentication, and quantity controls.

These are implementation tests, not proof that the skill improves an AI agent's security work.

## Comparative benchmark

Nine valid assessment runs completed on 2026-11-18: three per arm, requested model `gpt-6-astra`, medium reasoning, Codex CLI 0.169.0-alpha.11.1, 180-second limit each. All used fresh copies of the same small fixture, supplied source/accounts/access rules, and the same optional helper. The order rotated between arms. The competitor was `briiirussell/cybersecurity-skills` at `18642b272e9fe57ed6bdf3fd96614915e8a4d71d`.

| Measure across three runs | No invoked skill | Seca | Upstream OWASP audit |
| --- | ---: | ---: | ---: |
| Real bugs found / opportunities | 9/9 | 9/9 | 9/9 |
| Confirmed false accusations | 0 | 0 | 0 |
| Complete runtime proofs / opportunities | 4/9 | 6/9 | 6/9 |
| Fixes passing current fixture oracle | 9/9 | 9/9 | 9/9 |
| Final reports delivered | 3/3 | 3/3 | 0/3 |
| Median completion time | 107.69 s | 150.80 s | Not observed: all timed out |

**This study does not establish a detection advantage for Seca.** Baseline completed faster. All arms avoided the middleware-protected decoy. Competitor runs produced useful evidence, fixes and tests, but reached the 180-second cutoff before delivering the requested final report; their partial work is scored rather than discarded.

Proof scores are deliberately stricter than discovery scores. No original run independently inspected the saved incorrect price: an order-creation response establishes the returned price, but does not by itself prove the saved effect. One baseline run also recorded denial-test status failures without observing the unauthorized response bodies. These gaps reduce proof completeness, not discovery credit for the true bugs. All runs followed the supplied access rules and local scope. Coverage honesty scored 2/2 for baseline and Seca, and 1/2 for the competitor's accurate but incomplete notes.

All patches passed the narrow evaluator oracle. Manual review additionally found that Seca retained the explicit invoice tenant guard in all three patches, compared with one baseline and no competitor patches. Owner-only replacement passes this fixture; removing the tenant guard is not scored as a newly demonstrated vulnerability. The fixture cannot establish general patch quality or behavior under tenant reassignment.

The earlier 20.31-second baseline attempt was invalid: ignoring user configuration omitted the Windows sandbox implementation, blocking the first file read. Explicitly selecting the already-provisioned sandbox passed read/write/import preflight checks. No policy bypass was used. That attempt is excluded from the nine-run results.

See the [frozen evidence and methodology](benchmarks/2026-11-18/README.md) and [per-run scores](benchmarks/2026-11-18/scores.json). Three runs on one easy fixture are preliminary; global agent instructions and skill metadata were not fully isolated, and only the requested model identifier is recorded. No Claude, desktop, real deployment, advisory lookup, or prompt-injection resilience claim follows from these results.

## Changes and separate follow-up checks

After freezing the nine results, one sentence was added to the skill: independently inspect resulting state before and after fixing state-changing issues, or limit the claim if that is unavailable.

A single fresh follow-up using the same task, model, fixture and budget completed in 153.45 seconds. It found all three bugs, preserved the decoy and existing tenant guard, passed all six patch-oracle checks, and independently read saved order totals before (2 cents) and after (2,000 cents) remediation. This is a targeted check on the same fixture, not held-out evidence or a new comparative benchmark. [Follow-up report](benchmarks/2026-11-18/follow-up/workspace/report.md).

A separate URL-only smoke run used the updated skill, with no supplied source, accounts or private access rules. It completed in 61.97 seconds, made exactly one `GET /`, created no orders, and reported no demonstrated vulnerability while identifying blocked checks. Authorization and bounded read-only scope were supplied upfront, so this does not test the initial-question limit or richer URL flows. The local server stopped successfully. [Observed requests](benchmarks/2026-11-18/url-only/observations.json), [report](benchmarks/2026-11-18/url-only/workspace/report.md).
