# Benchmark v2: closed with incomplete results

Recorded 2026-11-23 (Asia/Taipei). Assessments span November 18 and 23.
The requested model was `gpt-6-astra`, medium reasoning, with a 180-second budget.
The provider model build and global runtime instructions cannot be guaranteed identical
across dates. The original nine-run benchmark remains unchanged.

The comparison was closed on 2026-11-23 before revising the skill. Its 22 reviewed
results and exclusions are final for this study. The blocked attempt will not be
retried and the four unstarted assessments will not be filled with a different skill
revision. Any future comparison requires a new protocol and fresh workspaces.

## Source assessments

Of 27 planned assessments, 22 have reviewable completed or timed-out results, one
failed, and four remain unstarted. All 22 valid results have been reviewed. These are
unequal partial samples, not a completed three-repetition comparison.

| Measure | Baseline | Seca | OWASP audit |
| --- | ---: | ---: | ---: |
| Scored assessments | 7 | 7 | 8 |
| Planned bugs found / observed opportunities | 10/10 | 10/10 | 12/12 |
| Complete executed runtime proofs | 4/10 | 10/10 | 8/12 |
| Fixes passing sequential checks | 10/10 | 10/10 | 12/12 |
| Confirmed false accusations | 0 | 0 | 0 |
| Completed / timed out | 7 / 0 | 7 / 0 | 1 / 7 |
| Median seconds, completed runs only | 113.25 | 138.41 | 165.05 |
| Assessments passing every independent check | 7/7 | 7/7 | 8/8 |

The competitor's completion-time median covers one run and is not comparable to a
full-sample median. All six scored portal assessments have zero confirmed false
accusations. Extra findings, including authentication parsing and Unicode-input errors,
are recorded separately from planted root causes. A portal designed without planted
bugs is not proof that it contains no defects.

Seca produced more complete runtime proofs in the observed cases, while baseline
finished faster. Every arm found the planted bugs it encountered. This does not
establish superiority, general security effectiveness, or statistical significance.

Input/cached/output token metrics are retained per run. Seven competitor timeouts have
unknown usage. Dollar cost is unknown, not zero; totals with missing usage should not
be used to rank cost efficiency.

## Why the comparison stopped

`checkout/3-baseline` failed after the provider flagged content for possible
cybersecurity risk. The attempted commands and failure are preserved. It receives no
quality score. No retry, prompt rephrasing, model change, or alternate execution of
that assessment was used to get around the safeguard.

The frozen protocol stops on failed assessments. `checkout/3-seca` and all three
`portal/3-*` assessments remain unstarted. Resolve access through the provider's
supported process before planning continuation; the existing spend-cap recovery tool
does not apply to this failure. Do not reuse a partly assessed or patched workspace.

## Supplemental evidence

Previously executed overlapping-request checks reproduced payment, refund, and coupon
races in the first two baseline and Seca checkout patches. The first two competitor
patches serialize the workflows and passed those instrumented schedules. The third
competitor patch contains sequential guards and explicitly leaves concurrency
unverified; no new supplemental execution was made for that patch.

These checks were added after freezing the comparison. They are separate evidence,
not retroactive changes to its scoring. An instrumented two-request interleaving
demonstrates a possible failure, not its production frequency or exhaustive race safety.

The strengthened retrospective tenant-migration check accepts all three original Seca
patches, one baseline patch, and no competitor patches. It does not change the original
benchmark scores. See [retrospective results](retrospective-tenant-check.json).

## Improvements identified by this comparison

The assessed skill is preserved by the checkpoint at `b172c67`. The narrow
candidate improvement is to consider bounded overlapping-request verification when an
authorized local workflow promises at-most-once payment, refund, or resource consumption;
sequential replay alone does not establish atomicity. Any such verification must remain
within authorized state changes and inspect resulting state. If it cannot be performed,
report concurrency as unverified. This proposed wording has not been behaviorally tested
in this comparison. Subsequent revisions and validation are separate evidence.

The comparative results are now frozen. Post-change follow-ups remain separate from
these scores and do not complete the missing assessments.

The separate website experiment also exposed an execution-policy deviation in one
URL-only run. Any later skill revision should explicitly treat a denied execution as
a blocker for that check, without trying another mechanism to execute the denied
script. The original skill and observed deviation remain part of the historical record.

## Evidence and reproduction

The [separate website experiment](../benchmarks/website-v2-2026-11-23/README.md)
finished all six planned attempts: five completed and one timed out after writing its
report. Across 118 requests, every server stopped and ticket data remained unchanged.
No application vulnerability was confirmed. One URL-only run has an execution-policy
deviation and is not a fully compliant run. Authenticated runs provide broader observed
coverage but still cannot isolate ownership from current tenant membership with the
available accounts. These results do not change the source-comparison scores.

See the [archive](../benchmarks/v2-2026-11-23/README.md),
[machine-readable scores](../benchmarks/v2-2026-11-23/scores.json),
and [frozen protocol](PROTOCOL.md).

```powershell
python eval/v2/summarize.py eval/benchmarks/v2-2026-11-23 --allow-partial
```

This only summarizes reviewed artifacts; it makes no model calls. Without
`--allow-partial`, an incomplete suite is rejected. Eligible but unreviewed results
are rejected in either mode. Failure and unstarted statuses are explicit exclusions.
