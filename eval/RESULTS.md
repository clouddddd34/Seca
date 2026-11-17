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

Prepared nine workspaces: three each for baseline, Seca, and the competitor at commit `18642b272e9fe57ed6bdf3fd96614915e8a4d71d`. Every arm receives identical fixture inputs and the same optional helper executable. Evaluator answers and tests are excluded.

The first baseline attempt used Codex CLI 0.169.0-alpha.11.1, requested `gpt-6-astra` with medium reasoning and a 180-second wall-clock limit. The environment rejected its initial PowerShell command to read the local fixture with **blocked by policy**. The agent exited after 20.31 seconds without inspecting source or producing the requested report. This attempt is invalid for measuring assessment quality even though the CLI returned exit code zero. The runner now labels a zero-exit run without `report.md` as incomplete. Other arms were not run against this broken setup.

| Arm | Valid scored runs | Comparative result |
| --- | --- | --- |
| No explicitly invoked skill | 0 | Not established |
| Seca | 0 | Not established |
| Upstream OWASP audit | 0 | Not established |

No win rate, detection improvement, or reduction in false positives is claimed. Rerun in fresh prepared workspaces once an approved agent environment can read and test the fixture. Do not bypass the execution policy. Logs remain local rather than publishing provider/account diagnostics.
