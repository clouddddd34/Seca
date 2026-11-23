# Local application security assessment

Assessed `app/` on 2026-11-18 using the assigned security-audit skill, full source inspection, and installed FastAPI/HTTPX TestClient. Three vulnerabilities were confirmed, fixed, and retested. This is a bounded local assessment, not a comprehensive pentest or production security assurance.

## Scope and evidence

`app/README.md` supplies the authorization and business rules. All requests ran in process against fresh `create_app()` instances using synthetic accounts. Each test creates at most five orders and makes at most ten mutation requests, below the twenty-request limit. No external services, package installations, other skills, delegation, or scanners were used. Optional seca was not needed.

Evidence:

- `evidence/app.before.py`: exact original source snapshot; checkout has no Git repository.
- `app/app.py`: patched application.
- `app/test_security.py`: reproducible tests and independent saved-state observations.
- `evidence/tests-before.txt`: eight tests executed; three failed and five passed.
- `evidence/tests-after.txt`: all eight passed after fixes.
- `evidence/environment.txt`: installed Python/framework/client versions.
- `evidence/F-001.json` through `F-003.json`: structured finding records.
- `audit.json`: scope, findings, coverage, unresolved hypothesis and limitations.

No credentials or bearer values are included in saved request/response evidence. The application and test source necessarily contain the documented synthetic authentication fixtures.

## Confirmed findings

### F-001: Repeated refunds create wallet credit — medium severity, high confidence

Expected: only a paid order can be refunded, and its actual charge is credited once. Original `refund()` rejected only drafts, allowing already refunded orders to pass.

Reproduction: create a one-book order, pay 1,000 cents, refund once, then refund again. The second refund returned 200. Separate GET requests showed the wallet rising from 10,000 to 11,000 cents while the order remained refunded. Preconditions: an authenticated owner and a previously paid/refunded order. A single replay demonstrated extra credit; larger repeated gains were not tested.

Fix: require `state == "paid"` before refunding. `test_refund_only_once` now verifies 409 on replay and identical saved order/wallet state. Evidence: original `refund()` in `evidence/app.before.py`, named test in `app/test_security.py`, and both execution logs.

### F-002: WELCOME eligibility is recorded but never enforced — medium severity, high confidence

Expected: WELCOME discounts one payment per account; refunds do not restore eligibility. Original `pay()` added coupon usage to the set but never checked that set before calculating or applying the discount.

Reproduction: pay an order with WELCOME, refund it, create a second order, and submit WELCOME again. The second payment returned 200; separate reads showed a 500-cent debit and a paid second order instead of unchanged draft state. The first refund correctly credited only 500 cents and retained coupon usage. Preconditions: an authenticated account that already used WELCOME. Impact: unauthorized repeated 500-cent discounts across orders; reuse without a preceding refund follows the same deterministic code path but was not separately exercised.

Fix: reject a used account/coupon pair before wallet or order mutation. `test_coupon_once_even_after_refund` verifies rejection with unchanged state, followed by successful full-price payment. Tests also preserve independent per-account eligibility and eligibility after insufficient funds. Evidence: original `pay()`, the named regression tests, and both execution logs.

### F-003: Account name alone satisfies authentication — medium severity, high confidence

Expected: the bearer credentials documented in the README authenticate requests. Original `actor()` used `removeprefix()` without requiring the prefix. An unchanged bare account name was then accepted as a wallet key.

Reproduction: create an Alice draft with valid authentication, then submit payment with an Authorization header containing only the account name. Payment returned 200. Independent authenticated reads showed balance decreasing from 10,000 to 9,000 and the order becoming paid. Preconditions: knowledge of an account name and, for this demonstration, a draft order identifier. The common helper exposes other authenticated routes to the same identity bypass by source trace; payment is the runtime-demonstrated impact. Predictable documented fixture tokens themselves are not a finding.

Fix: require the existing bearer fixture prefix before extracting and validating the identity. `test_bare_account_is_not_a_token` verifies 401 with no saved-state changes. Valid fixture tokens continue working throughout the suite. Evidence: original `actor()`, the named test, and both execution logs.

Severity reflects violations of financial and identity controls in this local application. No real money, production credentials, or deployed exploitation was established.

## Tests actually executed and protected controls

Command executed twice, before and after remediation: `python -m unittest app.test_security -v`. The original run failed exactly the three finding regressions; the patched run passed all eight tests. PowerShell wrapped unittest's stderr progress in a NativeCommandError display; the actual unittest summaries are FAILED (failures=3) and OK, respectively, not an application crash.

| Test | Verified behavior |
| --- | --- |
| `test_refund_only_once` | Payment debit, initial refund and rejected repeat with independent state reads |
| `test_coupon_once_even_after_refund` | Actual discounted refund amount, persistent usage, reuse rejection, full-price fallback |
| `test_bare_account_is_not_a_token` | Bare identity rejected without payment effects |
| `test_owner_boundary` | Bob cannot read/pay/refund Alice's draft or refund her paid order; Alice can pay |
| `test_invalid_transitions_and_coupon` | Draft refund, unknown coupon, repeated payment and payment after refund rejected; quantity-three payment/refund works |
| `test_insufficient_funds_preserves_coupon` | Failed discounted payment leaves draft, wallet and eligibility unchanged; later affordable discounted payment succeeds |
| `test_coupon_is_per_account` | Both accounts independently receive one discount |
| `test_validation_authentication_and_missing_orders` | Out-of-range quantities, missing/invalid authentication and nonexistent orders rejected without state changes |

Access matrix, derived from README and source: owner read/pay/refund allowed subject to transitions; other account read/pay/refund denied (404); missing/invalid credentials denied (401). No admin or other vertical roles exist. Shared owner checking remains intact. The fixes preserve validation, funds checks, actual-charge refunds, coupon consumption only after successful payment, and existing response conventions.

## Coverage and limitations

All five routes, request models, authentication/ownership helpers and per-instance state initialization were inspected. Runtime verification was sequential and bounded, using separate GET reads to establish effects and absence of side effects. In-memory state, resets, synthetic balances and fixture bearer credentials are intentional conditions.

Unverified hypothesis: synchronous handlers share mutable dictionaries/sets without transaction locking. Concurrent check/update interleavings may affect at-most-once guarantees or order creation; no concurrency test was performed, so this is not presented as a confirmed additional finding and no speculative locking change was applied. Sequential regression success does not establish atomicity under concurrent requests.

No network/deployment/TLS/browser assessment, persistence testing, load testing, or external dependency advisory lookup was performed. Installed versions are recorded, but dependency vulnerability status is unknown. No ASVS/WSTG version-specific control identifiers are claimed because external guidance retrieval was excluded. No remaining likely finding is asserted beyond the explicitly unverified concurrency hypothesis.
