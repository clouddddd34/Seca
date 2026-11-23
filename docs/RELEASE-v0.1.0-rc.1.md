# Seca v0.1.0-rc.1 — preparation draft

This experimental release candidate packages the portable web/API assessment skill
and optional Windows x86_64 Rust helper. It adds benchmark v2 with delegated-document,
checkout and secure-portal applications, independent patch checks, frozen input hashes,
token metrics, and a separate website coverage experiment.

Evaluation is incomplete. This document accompanies packaging-validation artifacts,
not a published release. No tag or public release has been created. Do not promote
these packages until the remaining evaluation gates have been resolved.

## Evidence as of 2026-11-23

Benchmark v2 has 22 reviewed source assessments of 27 planned. One assessment was
stopped by the provider's cybersecurity safeguard; four remain unstarted under the
frozen stop rule. The existing skill remains unchanged. See
[partial results](../eval/v2/RESULTS.md) for observed denominators, timeouts, proof
quality, supplemental concurrency failures, and the access blocker.

All 26 local Python tests and three Rust unit tests passed. Rust formatting, Clippy
with warnings denied, and the locked Windows release build passed. Skill frontmatter
validation passed. These checks validate implementation and packaging, not the skill's
general security effectiveness. The proposed concurrency instruction is not shipped
or claimed as tested.

The separate website experiment has six attempts: five completed, one timed out with
a report file. All ticket data stayed unchanged and all servers stopped. One URL-only
run worked around a script-execution restriction; that process-safety deviation is
documented and has not been fixed or validated away. See the repository's
`eval/benchmarks/website-v2-2026-11-23/README.md` for evidence and limitations.

## Intended artifacts

- `seca-skill-v0.1.0-rc.1.zip`: complete skill, license and onboarding material.
- `seca-v0.1.0-rc.1-windows-x86_64.zip`: standalone helper, usage notes and dependency notices.
- `SHA256SUMS.txt`: SHA-256 hashes for both archives.

See [quickstart](QUICKSTART.md) and [benchmark protocol](../eval/v2/PROTOCOL.md).

## Boundaries

This remains a prototype. Only the Windows build and this Codex runtime are validated;
there is no Claude execution, desktop support, real-deployment, JavaScript/browser,
or comprehensive security assurance. Local fixtures and token counts do not establish
production effectiveness or billed cost. No new scanners or Rust helper features are
included. The helper remains optional and GET-only.
