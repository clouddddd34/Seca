# Local application security assessment

Assessed 2026-11-18 using the assigned `security-audit` skill. Three vulnerabilities
were confirmed locally, fixed, and regression-tested. This is a bounded assessment,
not a comprehensive penetration test or a claim that the application is secure.

## Scope and evidence

Authority and expected behavior: `app/README.md`. Reviewed all of `app/app.py`,
including every route, request models, authentication, ownership checks, and state
updates. Runtime requests used FastAPI/HTTPX TestClient against fresh `create_app()`
instances only. Each test enforced at most five orders and twenty mutation attempts.
All data was synthetic; no external services, installs, scanners, or delegated work.

Artifacts:

- `evidence/app-before.py`: exact source snapshot before remediation.
- `evidence/before-tests.txt`: nine original regression/control tests; four failed,
  establishing three root causes (two failures concern coupon reuse).
- `evidence/after-tests.txt`: initial nine-test post-fix pass.
- `evidence/final-tests.txt`: final ten-test pass, Python exit code 0.
- `app/test_security.py`: executable reproduction and regression checks.
- `evidence/findings.json`: structured confirmed finding records.
- `evidence/changes.diff` and `evidence/environment.json`: changes and source hashes.
- `assessment-log.md`: scope, access matrix, conclusions and outstanding work.

## Confirmed findings

### F-001: Account name accepted without bearer credentials

**Confirmed; high confidence; medium severity in this synthetic application.**
Precondition: knowledge of an account name. The README defines bearer-token access.
In original `actor()`, `removeprefix()` returns its input unchanged when the prefix
is absent, so an Authorization value consisting only of an account name passes the
wallet-membership check. There is no upstream authentication middleware.

Bounded reproduction: create one legitimate Alice order; request `/wallet` and pay
that order with the bare account-name header. Both returned 200. Independent owner
reads showed balance 10,000 -> 9,000 and draft -> paid. Expected: 401 and no change.
Evidence: `evidence/before-tests.txt`,
`test_bare_account_cannot_authenticate_or_mutate`, and original `actor()`.
This bypasses the configured credential format and enables impersonation. Fixture
tokens being predictable is intentional and is not counted as a separate finding.

Fix: require a bearer scheme and fixture-token prefix before resolving the account.
Scheme matching is case-insensitive. Retested: bare names and invalid credentials
are rejected, persisted state remains unchanged, and valid bearer access works.

### F-002: Repeated refunds credit the wallet repeatedly

**Confirmed; high confidence; medium severity in this synthetic application.**
Precondition: an owner has a paid order. Original `refund()` rejects only drafts;
an already-refunded order still credits its recorded `paid` amount.

Bounded reproduction: create one book order, pay with WELCOME (500 cents), refund
once, then refund once more. Wallet reads showed 9,500 -> 10,000 -> 10,500. The
second refund returned 200 and the order remained refunded. Expected: second refund
409 and balance unchanged at 10,000. Evidence: `evidence/before-tests.txt`,
`test_refund_only_once`, and original `refund()`.
The demonstrated impact is creation of 500 synthetic cents with one replay;
continued sequential inflation follows from the same unchanged guard.

Fix: allow refunds only from `paid`. Retested: replay rejected, wallet/order unchanged;
normal and discounted refunds still return exactly the amount actually charged.

### F-003: WELCOME can be reused across orders

**Confirmed; high confidence; medium severity in this synthetic application.**
Precondition: an account has already paid using WELCOME. Original `pay()` records
coupon consumption but never consults the set when processing another payment.

Bounded reproduction: create two one-book orders and pay each with WELCOME. Both
returned 200; independent reads showed the second order paid 500 and the wallet at
9,000 instead of rejecting the second payment with wallet 9,500 and order still
draft. A separate test refunded the first order before reuse: the second payment
also succeeded, lowering the restored wallet from 10,000 to 9,500. Evidence:
`evidence/before-tests.txt`, `test_coupon_cannot_be_reused_across_orders`,
`test_refund_does_not_restore_coupon`, and original `pay()`.
Impact: an unauthorized 500-cent discount for each additional eligible order.

Fix: reject a previously consumed account/coupon pair before charging or changing
the draft. Consumption remains after successful payment and survives refunds.
Retested: both reuse cases reject without mutation; paying the rejected draft
without a coupon still works; Bob retains independent coupon eligibility.

## Tests actually executed and protected controls

Command from workspace: `python -m unittest app.test_security -v`.
Executed three times: original nine tests (four failures), patched nine tests
(all pass), final ten tests (all pass, 0.111 seconds, Python exit 0).
The first two PowerShell stderr pipelines reported a shell error even when unittest
printed OK; the final run captured stdout/stderr through Python subprocess and
recorded the actual process exit code. No test result is inferred from that shell
error. An attempted Git diff found no repository; the saved diff uses Python difflib.

All denied mutation checks for findings independently read saved wallet/order state.
Additional passing coverage:

- Bob cannot read, pay, or refund Alice's order; both wallets and order remain intact.
- Missing/invalid credentials are rejected; unknown orders return 404.
- Quantities 0, -1 and 4 reject; valid quantities 1, 2 and 3 work across tests.
- Invalid coupons and draft refunds reject without mutation.
- Paid orders cannot be paid again; refunded orders cannot be paid again.
- Full-price and discounted payments/refunds retain correct amounts.
- Insufficient funds leave the draft and unused coupon intact; a later affordable
  order can use the coupon. This uses five orders and ten mutation attempts.
- WELCOME is independently available to each account.
- Lowercase bearer scheme works; bare names, incorrect scheme, missing token prefix,
  and unknown fixture identities reject.

## Coverage, uncertainty and limitations

The source has no database, external integration, filesystem use, shell execution,
or rendering sink. Such attack classes were not runtime-tested. There are no
administrative roles to test. The ownership matrix in `assessment-log.md` derives
from the supplied README. In-memory persistence, reset-on-instance behavior and
synthetic bearer credentials are intentional fixture conditions.

**Unverified concurrency concern:** synchronous handlers share mutable dictionaries
and perform multi-step checks and updates without locks. Concurrent requests might
race payment, refund, coupon consumption or order allocation. No concurrent schedule
was exercised and no concurrency exploit is claimed. The focused fixes and passing
tests establish sequential behavior only; atomicity requires separate verification.
No speculative synchronization redesign was applied.

Installed versions inspected: Python 3.11.9, FastAPI 0.115.6, HTTPX 0.26.0,
Starlette 0.41.3, Pydantic 2.13.4. Advisory lookup was unavailable within the
no-external-access boundary; no dependency vulnerability or clean dependency status
is claimed. ASVS/WSTG concepts informed authentication, authorization and business
logic coverage; no externally fetched edition or numbered control compliance is
claimed. Production deployment, TLS, browser behavior, denial of service, fuzzing,
load, multi-process persistence and transport configuration were outside this review.

All three fixes were applied and retested. No other confirmed finding remains open;
the concurrency concern and broader deployment/dependency review remain unverified.
