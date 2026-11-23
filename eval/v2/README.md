# Benchmark v2

**Current status:** the comparison is interrupted: 22 reviewed results, one
provider-safeguard failure, and four unstarted assessments. See [results](RESULTS.md).
The spend-cap recovery example below does not apply to the safeguard failure.

Read [PROTOCOL.md](PROTOCOL.md) before preparing or scoring. It defines the root-cause
rubric, scope, budget and release gates. `fixtures/` contains three independent local
applications. `check.py` and `test_v2.py` are evaluator-only; never copy them to assessed
workspaces. The portal has no planted vulnerability; do not infer universal security
from that design intent or passing checks.

From the repository root, with the existing dependencies and Rust helper built:

```powershell
python -m unittest eval.v2.test_v2 eval.test_evaluation -v
python -m unittest eval.v2.test_preparation eval.v2.test_website eval.v2.test_concurrency -v
python -m unittest eval.v2.test_summarize eval.v2.test_archive -v
python eval/v2/suite.py prepare "$env:TEMP/seca-v2-NEW" --competitor C:/path/to/pinned-clean-competitor
python eval/v2/suite.py run "$env:TEMP/seca-v2-NEW" --model gpt-6-astra --seconds 180
python eval/v2/website.py "$env:TEMP/seca-website-v2-NEW" --model gpt-6-astra --seconds 180
```

These commands consume model access. Run a sandbox read/write/import preflight first,
using the same settings as `eval/run.py`. Preparation does not make model calls.
Completed and timed-out source runs may be skipped when resuming the exact same suite;
failed/interrupted attempts stop it and require inspection. Never rerun a patched copy.
Website output directories must be new. Do not mix model/budget configurations.

For the observed provider spend-cap interruption, wait until model access is available
and verify the original sandbox settings with a small preflight. Use fully resolved
Windows paths rather than a short-name TEMP alias. `replace_invalid.py` can preserve
that failed attempt and copy byte-identical inputs from an unattempted same-fixture,
same-arm donor. It records recovery without modifying the frozen manifest or protocol:

```powershell
python eval/v2/replace_invalid.py "$env:TEMP/seca-v2-NEW" documents/2-seca documents/3-seca
python eval/v2/suite.py run "$env:TEMP/seca-v2-NEW" --model gpt-6-astra --seconds 180
```

This prepares a fresh attempt; it does not change account limits, permissions or model
settings. Failed infrastructure attempts remain archived and excluded from quality
scores, while completed and timed-out assessments retain their original results.

`manifest.json` freezes initial files, prompts and evaluator hashes. `protocol.json`
records CLI settings. Each run saves execution status, transcript, token metrics and
independent patch checks. Scoring still requires human/agent review of actual command
outputs, claims and changes: mechanical checks do not establish discovery or proof.
Evaluator checks run in a separate process with a timeout; this is not an adversarial
code sandbox. Only evaluate these trusted local fixture patches in this workflow.

Use `archive.py SOURCE NEW_DESTINATION` to collect selected evidence without binary
tools, installed skill copies or provider diagnostics. Review the archive for credentials
and unsupported claims before publishing. Original transcripts stay in the external
run directory. Redaction makes some recorded commands documentary, not directly runnable.

The previous benchmark's evaluator now includes tenant reassignment. Its original
scores and evidence remain unchanged; this additional check must not be represented as
part of the old protocol. New fixtures test share lifecycle, migrated identities,
coupon consumption, failed-payment atomicity, refund lifecycle and secure portal controls.

## Supplemental concurrency evidence

The first competitor checkout run exercised two overlapping requests under an
instrumented thread schedule and added a lock. This exposed a limitation in the frozen
sequential oracle. `check_concurrency.py` independently reads saved wallet/order state
after pairs of payment, refund and coupon requests, pausing at wallet-write lines to
exercise an allowed interleaving. It uses fresh instances and at most two simultaneous
requests; it is not a load test or evidence of production exploit frequency.

```powershell
python eval/v2/check_concurrency.py C:/path/to/candidate/app.py
```

This check was added after the comparison started. Its outputs are explicitly
supplemental and must not be folded into the original frozen scores. The validator
test confirms that sequential-only guards fail while serialized reference workflows
pass. Instrumentation recognizes this fixture's wallet-write statements; an altered
implementation requires review before adapting the check.
