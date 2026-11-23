# Seca project phases

Updated 2026-11-23 (Asia/Taipei).

| Phase | Deliverable | Status |
| --- | --- | --- |
| 1. Prototype | Portable skill, Rust replay/ledger helpers, local Python fixtures | Complete |
| 2. Comparative evaluation | Original benchmark and stronger v2 evidence | Closed; v2 is incomplete with 22 reviewed results, one blocked attempt and four unstarted runs |
| 3. Targeted hardening | Concurrency reasoning and execution-denial instructions, separate follow-up assessments | Closed with limited follow-up evidence; no demonstrated improvement |
| 4. Release candidate | Reviewed merge, Windows/skill packages, checksums, version tag and GitHub prerelease | Preparing experimental prerelease with documented evaluation gaps |

The provider-blocked checkout assessment is not a dependency for further development.
It remains excluded, with no bypass or replacement run. Closing v2 does not turn its
partial results into a completed comparison. Historical evidence remains unchanged.

Phase 3 tests use a new source-only report scheduler and a harmless simulated execution
denial. They evaluate reasoning and whether the agent respects the denial, not dynamic
checkout race testing or general security effectiveness. See
[follow-up protocol](../eval/followup/PROTOCOL.md).

After the release candidate, collect user feedback and independently authored cases
before making broader effectiveness claims or a stable release. Desktop support,
additional scanners and new Rust helper features remain deferred.

Follow-up: three completed assessments, one spending-cap failure with a partial report,
and four unstarted attempts. See [results](../eval/followup/RESULTS.md).
