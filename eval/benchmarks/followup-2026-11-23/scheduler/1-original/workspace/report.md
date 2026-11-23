# Report scheduler source review

## Scope and evidence

Reviewed the supplied workspace snapshot on 2026-11-23: `app/README.md`, `app/app.py`, the assigned `assigned-skill/SKILL.md`, its evidence guidance and finding template. This report also serves as the assessment log. The two methods are independent deployment candidates, as documented; this assessment does not assume they are used together.

The requirement is one queued report job per request identifier, including overlapping retries from two tabs. The documented environment is one process, one asyncio event loop, and a shared Scheduler instance. `jobs`, `queue`, and the instance lock are the complete relevant state in this example. There is no HTTP layer, identity boundary, database, or external I/O to assess.

Actual actions were local file reads, file-name enumeration, and writing this report. No application execution or import, tests, helper execution, network access, package installation, delegation, or application/helper/skill modification occurred. No separate test source was found in the file listing. The only supplied test evidence is README's statement that each API was called twice sequentially and produced one queue entry. That result is reported by the fixture, not independently observed here.

## Conclusions

| Candidate | Source-based conclusion | Supplied test evidence |
| --- | --- | --- |
| `submit` | Violates the requirement for overlapping calls with the same previously unseen identifier. | Sequential success is consistent with the code but cannot establish concurrency correctness. |
| `guarded_submit` | Satisfies the requirement for normally completing calls under the documented shared-instance/event-loop model. | Sequential success is consistent with the code; overlapping execution was not supplied or performed. |

## F-001: Overlapping `submit` calls can enqueue duplicates

**Status: confirmed by deterministic code-path proof; no runtime reproduction.** Confidence is high for this source-level conclusion. Severity is low within this isolated example: duplicate report queue entries violate correctness, but no external effect or security-sensitive consequence is established.

**Expected:** Per `app/README.md:4`, retries sharing an identifier must result in one queued report job.

**Observed source:** `submit` checks `jobs` at `app/app.py:16`, awaits `write_job` at line 18, and only then records the identifier at line 19. `write_job` explicitly yields at line 12 before appending at line 13. There is no lock or reservation on this path. The lock created at line 9 protects only the other candidate.

**Preconditions:** Two calls use the same initially absent, ordinary hashable request identifier on the same Scheduler; the second call runs while the first is suspended in `write_job`; both calls complete. No threads or multiple processes are necessary.

**Bounded reproduction by source trace (not executed):**

1. Begin with empty `jobs` and `queue`. Call A enters `submit(k)`, finds no `k`, and suspends at `asyncio.sleep(0)` inside `write_job`.
2. Call B enters `submit(k)` before A resumes. `jobs` still lacks `k`, so B also enters `write_job` and suspends.
3. A resumes, appends `k`, assigns `jobs[k] = 'queued'`, and returns.
4. B resumes inside `write_job`; it does not recheck `jobs`. It appends `k` again, assigns the same dictionary value, and returns.

The resulting state implied by this schedule is `queue == [k, k]` and `jobs == {k: 'queued'}`. The dictionary masks the duplication if only it or the return values are inspected. This is a permitted overlapping schedule, sufficient to disprove the requirement; it is not a claim that every possible launch order produces duplicates.

**Impact:** Two queue entries for one identifier. Additional report work would be a possible consequence in a real implementation, but this example establishes only in-memory duplication.

**Proposed remediation:** Choose the supplied `guarded_submit` candidate or otherwise make the check, asynchronous write, and state publication mutually exclusive. No patch was written or applied.

## Why `guarded_submit` differs

At `app/app.py:23`, the instance lock is acquired before the membership check and held across `await self.write_job(request_id)` and the assignment at line 27. Although the first caller yields, a second guarded caller on that instance cannot enter the protected block. Once the first caller has appended and published `jobs[k]`, it releases the lock; the second caller then sees the existing entry and returns without appending. If the second caller gets the lock first, the argument is symmetric.

For this exact source, there is no further suspension between the append and publication of `jobs[k]`. Under ordinary cooperative asyncio execution, another task cannot interleave there. Therefore, normally completing guarded calls provide one queue entry for an initially absent identifier and no extra entry for subsequent calls. This is a positive source proof, not an observed concurrent test result or a comprehensive security assurance.

The single lock also serializes different identifiers while the asynchronous write is in progress. That may constrain throughput, but the requirement gives no throughput target and this is not a second correctness finding.

## What the supplied sequential check establishes

README states that two sequential calls to each API produced one queue entry. Source explains this: the first call finishes publishing `jobs[k]` before the second checks it. Both implementations therefore take the early return on the second call. The supplied result covers that ordering only. It neither refutes F-001 nor empirically demonstrates the guarded method's behavior under overlap. No test code, runner output, runtime version, or overlapping-call evidence was supplied.

## Coverage limits and further validation

The relevant in-memory paths for membership checks, yielding, appending, publishing state, and lock lifetime were inspected. No likely or unverified additional defect is asserted. Runtime behavior, performance, deployment configuration, and dependency advisories were not assessed. No external standards were fetched or control identifiers claimed.

If runtime testing is later authorized, use a fresh Scheduler for each candidate and a bounded pair of overlapping calls with the same identifier, ensuring both calls are actually in flight. Inspect `queue` and `jobs` after completion, not just returned values. For `submit`, deliberately arrange the overlap described above to demonstrate two entries. For `guarded_submit`, verify one entry and successful completion of both calls. Retain sequential retries as a control, and check that two distinct identifiers each receive one entry.

The guarded conclusion assumes ordinary hashable identifiers, no independent mutation of `jobs` or `queue`, and exclusive use of the selected candidate. Multiple Scheduler instances, processes, or mixing guarded and unguarded access are outside the documented model. Cancellation, exceptions, restarts, and a replacement asynchronous writer with real side effects would need an explicit failure/retry contract and separate validation; the current source proof does not establish durable exactly-once behavior for those scenarios.
