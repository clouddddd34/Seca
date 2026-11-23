# Source-only assessment: report scheduling candidates

## Scope and evidence

Reviewed the supplied workspace snapshot on 2026-11-23: `app/README.md`, `app/app.py`, `assigned-skill/SKILL.md`, and its evidence-label reference and finding template. This report also serves as the assessment log. File discovery found no separate test files. The only supplied test evidence is the README statement that each API was called twice sequentially and produced one queue entry; no test code, raw output, or overlapping-call result was supplied.

The documented requirement is one queued report job per request identifier, including retries from two tabs. The documented execution boundary is one process, one asyncio event loop, and a shared Scheduler instance. The candidates are independent alternatives; a deployment chooses one. The implementation is in-memory Python using asyncio, with no HTTP layer, credentials, database, or external I/O. The relevant boundary is between concurrent callers and shared `jobs`/`queue` state.

Only file-reading commands and report creation were used. No application execution or import, tests, helper execution, network access, package installation, delegation, or patches occurred. Supplied application, helper, and skill files were not modified. Findings use the assigned skill's evidence labels; “confirmed” can mean a complete source proof and does not imply runtime reproduction.

## Decision

`submit` fails the documented overlapping-retry requirement by a deterministic source-path proof. `guarded_submit` satisfies that requirement within the stated shared-instance, single-event-loop boundary for ordinary successful calls: its lock serializes the entire check/write/record operation. The sequential result is consistent with both candidates and cannot distinguish their concurrency behavior.

## F-001 — Duplicate jobs through `submit`

**Status:** confirmed by source proof; concurrent execution unverified. **Confidence:** high under the preconditions below. **Severity:** low in this bounded example: duplicate in-memory report work. No broader operational or security impact is established.

**Expected:** Repeated submissions of the same request identifier queue exactly one job (`app/README.md:3–6`).

**Actual source observations:** `submit` checks `jobs` at `app/app.py:16–17`, awaits `write_job` at line 18, and only then records the identifier at line 19. `write_job` explicitly suspends via `await asyncio.sleep(0)` at line 12 before appending to the queue at line 13. No lock or reservation protects this candidate. The dictionary assignment overwrites the same key; it does not deduplicate queue entries already appended.

**Preconditions:** Two overlapping calls to `submit` use the same initially absent, stable hashable identifier and the same Scheduler instance; both calls complete normally. This is within the documented model. No multiple threads, processes, external service, or unusual identifier behavior is needed.

**Bounded source reproduction / reasoning (not executed):**

1. Call A observes that identifier R is absent and enters `write_job`, suspending at `sleep(0)`.
2. Call B runs before A resumes, also observes R absent, and suspends in its own `write_job`.
3. A resumes, appends R, records `jobs[R] = 'queued'`, and returns.
4. B resumes without rechecking `jobs`, appends R again, records the same dictionary value, and returns.

This feasible interleaving establishes two queue entries for R and one dictionary entry. Both return values can still be `'queued'`; neither return values nor dictionary cardinality alone establish the required queue behavior. These are source-derived outcomes, not observed runtime state. Not every possible scheduling order duplicates work; one permitted overlapping order is sufficient to refute the requirement.

**Impact:** Duplicate report jobs despite a shared identifier. This example establishes no data exposure, authorization bypass, financial loss, or deployed exploitation.

**Proposed remediation:** Select the guarded candidate, or protect the full eligibility check, asynchronous enqueue, and state update with the same shared lock for all participating submission paths. No fix was written, applied, or retested. Merely checking again after an enqueue would not undo an already duplicated queue entry.

## Guarded candidate: source-supported protection

At `app/app.py:23`, `guarded_submit` acquires `self.lock`, initialized once per instance at line 9. The membership check, awaited write, and dictionary assignment all remain inside the `async with` block (lines 23–28). Awaiting `write_job` yields execution but does not release that lock. A second guarded call must wait; after the first records R and releases the lock, the second sees R and returns without appending. Thus the absent-to-queued transition is serialized across guarded callers.

The supplied `write_job` has no suspension between its append and its return, and the subsequent dictionary assignment adds no suspension. For ordinary execution in this single event loop, there is no task-interleaving window between those operations. This conclusion is specific to the shown implementation, not a guarantee for arbitrary replacement I/O, failures, or durability requirements.

The guard is instance-local and serializes different identifiers too, which may limit throughput if the asynchronous operation later becomes expensive. No performance measurements were made. It provides no cross-instance or cross-process coordination, neither of which is required here. If both candidates were exposed together, unguarded callers could bypass the lock; direct `write_job` calls also bypass deduplication. Those paths are visible in source but are not findings against the documented independent-candidate deployment. A real integration must preserve that boundary.

## Supplied tests and further validation

The README's sequential result supports only the reported sequential replay behavior. Source explains why: the first completed call populates `jobs`, so the second returns early in either candidate. The result does not prove atomicity or exercise contention. No independently observed test pass is claimed.

When execution is separately authorized, the smallest useful validation would start two same-ID calls on a fresh shared Scheduler for each candidate, ensure their execution overlaps, await completion, and independently inspect `queue` and `jobs` afterward. For `submit`, demonstrate the duplicate queue effect; for `guarded_submit`, verify exactly one queued entry and consistent returned status. Also retain a sequential replay control and a distinct-ID control showing both distinct jobs queue successfully. Inspect queue contents rather than relying only on API return values. These are proposed checks, not tests performed in this review.

## Coverage limits and outstanding work

The review traced every relevant method in the supplied application and the lock scope across the asynchronous suspension. No additional middleware, configuration, deployment wrapper, or test implementation was supplied. Runtime concurrency behavior, error injection, cancellation, performance, and integration behavior remain untested. The conclusion assumes ordinary successful operations and stable hashable request identifiers; identifier validation and lifecycle policy are not documented here. Crash recovery, durable scheduling, and multi-process behavior are outside the example's stated boundary.

No dependency/advisory lookup, scanner, OWASP control-version lookup, or external assessment was performed; network access was prohibited and none was needed for the source proof. No checks were denied by tools. The outstanding work is the explicitly unperformed runtime validation above and verification of the same shared-instance/guarded-entry boundary in any eventual integration. This is a bounded source assessment, not a comprehensive security audit or a claim that an application is secure.
