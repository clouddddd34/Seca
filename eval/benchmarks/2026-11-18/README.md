# Preliminary benchmark evidence ? 2026-11-18

Read the [results and limitations](../../RESULTS.md) first. This is a small local-fixture experiment, not a claim of superiority or production security.

## Protocol

- Three arms, three fresh runs each: no explicitly invoked skill, Seca, upstream OWASP audit.
- Same requested `gpt-6-astra` model, medium reasoning, Codex CLI 0.169.0-alpha.11.1, 180-second wall-clock budget, workspace-write sandbox, installed dependencies and optional Rust executable.
- Source, synthetic accounts and access rules supplied identically. Evaluator answer key and oracle excluded from assessed workspaces. No real targets tested.
- Sequential rotated order: baseline/Seca/competitor, Seca/competitor/baseline, competitor/baseline/Seca.
- Common task: [task.txt](../../task.txt). [Manifest](manifest.json) records input hashes, run order and competitor commit; [protocol](protocol.json) records execution settings. Source tests use FastAPI TestClient; these are not browser or remote deployment tests.
- [Scoring anchors](../../answer_key.md) were written before execution. Manual artifact/transcript review and independent patch checks produced [scores.json](scores.json). No weighted aggregate winner score is used.

## Evidence layout

Each original run directory contains `execution.json`, `patch-check.json`, selected completed Python/test command events in `test-executions.json`, and the generated reports, proofs, tests and patched source under `workspace/`. Competitor timeouts have partial artifacts instead of final reports. The three bug checks and three preserved-control checks passed for every patch. These narrow oracle checks do not establish that patches are flawless.

Artifacts are frozen observations; do not include their deliberately failing pre-fix tests in the main project test discovery. Use the explicitly named test modules in the project README. Fake fixture tokens are intentionally public. Text encodings were normalized to UTF-8, line endings and trailing whitespace normalized and personal Windows path prefixes redacted; provider diagnostics, complete transcripts, helper binaries and upstream skill source are not published. Some archived absolute paths are therefore documentary rather than runnable. Relative workspace scripts can be inspected and run in an isolated copy with the fixture dependencies.

Competitor-generated artifacts may follow upstream templates. Its [MIT notice](COMPETITOR-LICENSE) is retained. Upstream source remains available at the commit recorded in the manifest.

## Separate post-change checks

`follow-up/` is one fresh Seca assessment after adding independent saved-state verification to the skill. It has its own manifest/protocol and passed the oracle with independent before/after saved-price evidence. `url-only/` is one local smoke check with no source/accounts supplied; its observations record exactly one GET and zero created orders. These checks used the updated skill and are excluded from all original comparative scores.

## Interpretation

Every original run found all three real bugs and made no confirmed false accusation. Baseline was faster; Seca did not improve detection. Strict proof completeness was 4/9 baseline, 6/9 Seca and 6/9 competitor: no original run independently observed the persisted incorrect price, and one baseline run did not capture unauthorized response bodies. These are evidence gaps, not false findings. Competitor runs all reached the cutoff before a final report; partial findings and fixes still receive credit.

One easy fixture, three samples per arm, manual scoring, a fixed short budget, and imperfect isolation of global instructions limit generalization. The actual provider model revision is not independently established. The follow-up reuses the known fixture and is not a held-out test. No Claude, desktop, injection-resilience or production coverage was evaluated.
