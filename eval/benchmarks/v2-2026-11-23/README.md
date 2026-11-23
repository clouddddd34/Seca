# Benchmark v2 evidence snapshot

This archive preserves the interrupted comparison as of 2026-11-23: 22 scored
assessments, one provider-blocked assessment, four unstarted assessments, and an earlier
spend-cap attempt preserved under `invalid-attempts/`. See the
[results and limitations](../../v2/RESULTS.md).

`manifest.json` and `PROTOCOL.md` preserve the original frozen inputs/rubric.
`protocol.json` records execution settings; `resume-20261123.json` records the date
change. `review.json` contains manual evidence reviews, while `scores.json` combines
them with mechanical checks. `completion-status.json` records unfinished work.

Per-run directories contain execution/usage records, independent checks, candidate
source, reports and executed actions. `executed-actions.json` extracts completed
commands and file changes from original `events.jsonl`; review references to that raw
transcript can be checked against this extraction. Raw transcripts and installed tools
remain outside the repository. `failure.json` retains failure messages, including the
provider safeguard that stopped the comparison. Failed-attempt artifacts are evidence,
not scored findings or instructions to execute them.

Personal filesystem paths and opaque session/CSRF tokens are redacted. Synthetic
fixture credentials are intentional public test data. Redacted commands are documentary
and may not be directly runnable. Initial manifests hash the original input files, not
redacted candidate outputs. Competitor source is not vendored; its MIT notice is retained.

Supplemental concurrency and Unicode checks and the retrospective tenant checks were
not part of the frozen root-cause rubric. Do not combine them into its score totals.
