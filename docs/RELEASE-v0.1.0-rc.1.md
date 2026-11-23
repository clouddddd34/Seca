# Seca v0.1.0-rc.1 ? experimental prerelease

Portable web/API assessment skill and optional Windows x86_64 Rust helper. This
candidate adds benchmark v2 evidence, a separate website experiment, and focused
skill instructions for concurrency reasoning and respecting execution restrictions.
The helper remains optional and GET-only; no new scanners or Rust features are added.

## Evidence and limitations

Benchmark v2 is closed incomplete: 22 reviewed source assessments out of 27 planned,
one provider-blocked attempt, and four unstarted assessments. The frozen original
skill and historical results remain preserved. See [v2 results](../eval/v2/RESULTS.md).
The denied checkout assessment was not retried or routed through another provider.

The revised skill requires checking atomicity for at-most-once operations, distinguishing
sequential checks from concurrent evidence, and matching lock claims to the deployment
boundary. It also requires stopping a denied check and continuing only independent
permitted work, without alternative execution routes.

The separate follow-up planned eight assessments: three completed, one failed at the
workspace spending cap after writing a report, and four were unstarted. The original
and revised scheduler reviews tied on all five criteria. The original denial review
completed successfully; the revised partial trace also stopped after one helper
invocation, but is not a completed assessment. No effectiveness improvement is
established. See [follow-up results](../eval/followup/RESULTS.md).

The six-attempt website experiment had five completions and one timeout with a report.
An original-skill run bypassed a script-execution restriction; that historical failure
remains documented. A simulated-denial follow-up does not establish that this failure
is fixed across real tools. See [website evidence](../eval/benchmarks/website-v2-2026-11-23/README.md).

## Local validation

All 29 Python tests and three Rust unit tests passed, along with Rust formatting,
Clippy with warnings denied, the locked release build, and skill frontmatter
validation. A regression test verifies that timeout/failure/incomplete results stop
the follow-up sequence. These checks do not call an evaluator model.

## Artifacts

- `seca-skill-v0.1.0-rc.1.zip`: skill, license, and onboarding material.
- `seca-v0.1.0-rc.1-windows-x86_64.zip`: helper, usage notes, and dependency notices.
- `SHA256SUMS.txt`: archive hashes.

Each archive includes `SOURCE.json` with source commit, working-tree status, binary
hash, and skill-file hashes. See [quickstart](QUICKSTART.md).

## Release scope

This is an experimental candidate, not a stable release or evidence of superiority.
Only Windows and the recorded Codex runtime have been exercised. There is no Claude,
desktop, production, or comprehensive browser/security assurance. Local tests validate
implementation and packaging, not agent effectiveness. See [project phases](ROADMAP.md).
