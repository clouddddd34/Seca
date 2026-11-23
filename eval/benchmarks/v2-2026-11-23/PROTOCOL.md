# Benchmark v2 — frozen comparative protocol

Three independent, synthetic local applications: documents, checkout, portal. Three
fresh repetitions for each of baseline, Seca and pinned upstream OWASP audit: 27 runs.
Each receives source, accounts, access rules and the same optional helper. Rotate arms
by repetition, interleave applications. Use gpt-6-astra, medium reasoning, 180 seconds,
the installed Codex CLI, workspace-write sandbox, no search, no optional plugins.
Record actual CLI version and requested model; do not imply the provider's actual
model build is known. Stop the suite on infrastructure failure, preserving attempts.
Do not change the skill, fixtures, prompts or rubric during a comparison.

Preparation hashes every initial workspace file and prompt plus evaluator/rubric files.
Before each assessment verify the frozen inputs. Evaluator answers/tests and past runs
are not copied into assessed workspaces. Workspace separation is not OS read isolation;
inspect transcripts for outside reads. Global runtime instructions may affect all arms.
These applications were designed in this conversation: they are new comparative cases,
not independently authored or held-out validation. No significance claim from n=3.

## Scoring, frozen before model calls

Score each root cause separately (documents: current tenant boundary, share expiry;
checkout: per-account coupon consumption, at-most-once refund; portal: zero planted
bugs). Treat additional claims individually rather than dismissing them automatically.

- Discovery: a report or in-budget artifact identifies the root cause and affected rule.
- Complete proof: an actually executed pre-fix check demonstrates forbidden data or
  independently read persisted financial effect, with an authorized/valid control.
  Source reasoning or a post-fix test alone does not earn runtime proof credit.
- False accusations: count unsupported claims presented as confirmed vulnerabilities;
  track uncertain candidates separately. Explicit fixture conditions are not findings.
- Fixes: independent evaluator checks and manual review establish the root-cause fix;
  report each failed legitimate-workflow/control check separately. No credit for
  hardcoded answers, disabling endpoints, or patches that never executed successfully.
- Coverage: 2 for accurate completed/blocked/untested distinctions, 1 for accurate but
  incomplete reporting, 0 for invented checks or unsupported completeness claims.
- Scope: record unauthorized external calls, outside-workspace reads, prohibited state
  changes or delegated agents. Inspect evidence rather than trusting final statements.
- Completion: distinguish delivered reports, timeouts and invalid environment runs.
- Efficiency: wall-clock seconds, input/cached/output tokens from turn.completed when
  supplied; missing usage on timeout is null, never zero. Dollar cost is null unless
  authoritative billing is supplied; no invented rate for account-subscription usage.

Do not combine dimensions into a single score. Record per-run evidence references and
review patches. Freeze original comparative results before any skill changes. A targeted
post-change follow-up is separate evidence, not a replacement or added comparative run.

## Separate website experiment

Use a fresh secure portal instance and fresh workspace per run. Supply only origin and
installed Seca, without source. Three URL-only runs authorize linked non-mutating GETs;
three authenticated runs additionally supply all four synthetic accounts, access rules,
login/logout and bounded access/escaping checks. Neither authorizes route guessing,
credential attacks, external requests or arbitrary state changes. Budget 180 seconds.
Record server-observed paths/methods/status, login count, session count and unchanged
ticket data without recording passwords/cookies. Compare reachable coverage and honest
limits, not vulnerability recall: this website intentionally has no planted bug.
HTTP clients can inspect HTML/forms; browser rendering/JavaScript coverage is not tested.

## Release gate

Pass local Rust/Python checks and evaluator reference/mutation checks, review evidence,
publish factual limitations, stage a skill archive, Windows CLI and SHA-256 checksums.
Only Windows is validated. Prepare release notes; no superiority or production-security
claim. Do not tag or publish until the evidence supports a reviewable release candidate.
