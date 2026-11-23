# Local application assessment

Scope: `app/README.md` and all application source in `app/app.py`. Verification used the installed FastAPI TestClient (HTTPX transport), `create_app()`, synthetic accounts, and local in-process requests. No external services, package installation, skills, delegation, or files outside the workspace were used.

## Confirmed findings and focused fixes

### 1. Authentication accepts a bare account name

Evidence: `app/app.py`, `actor`; `app/test_app.py::CheckoutTests.test_bare_account_is_not_a_bearer_token`; failure in `baseline-tests.txt`.

Originally `removeprefix` returned unchanged input when the bearer prefix was absent, and the subsequent wallet-membership check accepted `Authorization: alice`. POST /orders with that header returned 201 and an Alice-owned draft without presenting her documented bearer token. Because all endpoints use this helper, account-name impersonation bypassed the intended authentication boundary. The synthetic token format itself is an intentional fixture condition.

Fix: require the existing bearer-token prefix before extracting and validating the account. The regression now expects 401; legitimate Alice and Bob bearer workflows continue to pass.

### 2. WELCOME can be reused across orders

Evidence: `app/app.py`, `pay`; tests `test_coupon_cannot_be_reused_across_paid_orders` and `test_coupon_cannot_be_reused_after_refund` in `app/test_app.py`; independent GET snapshots shown in `baseline-tests.txt`.

The code recorded coupon usage but never checked it. After a first discounted payment, a second order accepted WELCOME with 200, became paid for 500 cents, and reduced the wallet from 9,500 to 9,000. After refunding the first order, reuse likewise succeeded and reduced the restored 10,000 balance to 9,500. Both violate the one-payment-per-account rule.

Fix: reject already-recorded account/coupon pairs with 409 before wallet or order mutation. Usage remains recorded after refunds. Regression checks compare independently fetched order and wallet snapshots to verify rejected reuse leaves the draft and wallet unchanged. Paying that draft without a coupon still succeeds. Failed payments do not consume unused coupons, and Bob retains his own eligibility.

### 3. Repeated refunds create additional wallet credit

Evidence: `app/app.py`, `refund`; `app/test_app.py::CheckoutTests.test_repeated_refund_is_rejected_without_credit`; independent GET snapshots in `baseline-tests.txt`.

The refund guard rejected only drafts, allowing already-refunded orders. One discounted payment charged 500 cents, the first refund restored 10,000, and a second refund returned 200 and increased the saved wallet balance to 10,500. This permits repeat credit without another charge.

Fix: accept refunds only from the paid state. Repeated refunds now return 409 without modifying either saved state. Refunds still return the actual charge, including discounts.

## Tests actually executed

Test implementation: `app/test_app.py` (Python unittest with installed FastAPI/HTTPX TestClient).

- Baseline: `python -m unittest app.test_app -v`, captured through PowerShell Tee-Object in `baseline-tests.txt`: 9 tests, 4 failures corresponding to the three findings above, 5 passes. The log includes PowerShell's native-stderr wrapper; the unittest assertion failures are the substantive evidence.
- After fixes: the same 9-test suite loaded with `unittest.defaultTestLoader.loadTestsFromName('app.test_app')` and run with `TextTestRunner`, writing `fixed-tests.txt`: 9 passed, process exit 0.
- Reproduction command for the final suite: `python -m unittest app.test_app -v` from the workspace root.

Each test creates a fresh application. The largest workflow creates five orders and makes ten mutation requests (including rejected attempts), within the README limits of five orders and twenty mutations per instance. Tests assert status codes and, for financial/state failures, independently read saved order and wallet state using GET endpoints.

## Protected controls and coverage

Verified controls include owner-only order reads/payment/refund (Bob receives 404 on Alice's order), quantity bounds, missing/unknown credentials, nonexistent-order rejection, invalid-coupon rejection, insufficient-funds rejection, draft-refund rejection, repeated-payment rejection, payment-after-refund rejection, actual-charge refund accounting, coupon persistence after refund, coupon availability after failed payment, and independent account eligibility. Ordinary full-price and discounted purchase/refund workflows passed. Fixes retain the existing controls and fixture storage model.

## Uncertainty and limitations

This is a bounded, local, sequential assessment of the supplied service, not proof that no other vulnerabilities exist. Concurrent requests were not exercised; the shared in-memory check/update sequences are not explicitly synchronized, so concurrency guarantees remain unverified. No speculative concurrency fix was applied. Deployment, network exposure, persistence, proxy behavior, rate limiting, and production identity systems are outside this fixture's scope. Synthetic bearer credentials, initial balances, in-memory storage, and state reset on new instances are documented fixture conditions, not findings. Validation checks cover representative quantity boundaries, not every coercion or malformed-input combination.
