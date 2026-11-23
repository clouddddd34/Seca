# Local application assessment

Three confirmed bugs were reproduced and fixed. Assessment and execution were limited to this workspace and the synthetic application described in `app/README.md`. No external services, package installation, skills, delegation, or seca execution were used.

## Confirmed findings and focused fixes

| Finding | Demonstrated evidence before fixes | Fix in `app/app.py` | Regression in `app/test_app.py` |
| --- | --- | --- | --- |
| Authentication accepts bare account names | `Authorization: alice` returned 200 and Alice's wallet; the Bob subtest also returned 200. `actor()` removed the bearer prefix if present but accepted names without it. All routes share this authenticator. | Require the fixture bearer prefix before validating the account. | `test_exact_bearer_required`: rejects bare names, empty and malformed credentials, and unknown tokens; valid fixture bearer still works. |
| WELCOME can be used repeatedly | Two one-book orders both accepted WELCOME, each charging 500; saved wallet was 9,000 instead of rejecting the second attempt. The used-coupon set was written but never checked. | Check account/coupon membership before any wallet or order mutation; return 409 on reuse. | `test_coupon_once_across_orders_even_after_refund`: reuse rejected with identical saved state both before and after refund, ordinary payment still succeeds, and Bob retains independent eligibility. |
| Repeated refunds mint wallet credit | A discounted one-book purchase followed by two refunds returned 200 twice and left a saved wallet balance of 10,500. Refund rejected only draft orders. | Require state `paid` before refunding; return 409 for other states. | `test_refund_only_once_and_net_charge`: refunds the charged 500 once, rejects replay without changing saved state, and rejects payment after refund. |

These are violations of the documented local access and financial-state rules. Authentication impact here is acceptance of unauthorized credential syntax; fixture tokens are deliberately public, so no real credential compromise is claimed.

## Evidence and tests actually executed

- `app/evidence-before.json`: original-code HTTP reproduction results, including independently read saved orders and wallets. First fresh instance: two orders/four mutations; second: one order/four mutations.
- `app/test-before.txt`: `python -m unittest app.test_app -v` against original code. Six test methods; four assertion failures across three methods (authentication has two failing subtests). Three methods passed. Failed methods stopped at their failing assertions, so later assertions were not exercised in this run.
- `app/test-after.txt`: all six test methods pass against fixed code. The initial post-fix invocation also passed, but Windows PowerShell wrapped unittest's stderr output as a native-command error. A subsequent Python unittest runner wrote directly to this file and returned process exit code 0, confirming the result without that shell artifact.
- Tests use installed FastAPI TestClient/HTTPX in-process, with a fresh `create_app()` per method. Each instance stays below five orders and twenty mutations (maximum four created orders and ten mutation requests). Saved-state checks use GET endpoints rather than direct state manipulation.

Reproduce with `python -m unittest app.test_app -v` from the workspace root. Standard unittest status output goes to stderr.

## Protected controls and coverage

Owner-only order reads, payments and refunds remain enforced with 404 responses, including unknown orders. Tests cover Bob's attempts against Alice's order and confirm Alice's saved state is unchanged. Quantity bounds (0, -1 and 4 rejected; 1, 2 and 3 exercised), unknown coupons, draft refund rejection, duplicate payment rejection, and payment after refund are covered. Ordinary payments, discounted payments and net-charge refunds succeed. Insufficient funds leave both wallet and draft unchanged and do not consume WELCOME: a later refund funds a successful discounted retry. Used coupons survive refunds and remain scoped to the account.

The fixes preserve ownership checks, price calculation, quantity limits, insufficient-funds checks, stored charged amounts, and response structure. No unrelated refactoring was performed.

## Fixture conditions, uncertainty and limitations

In-memory state, resets on new app instances, synthetic balances, public fixture bearer tokens, and sequential IDs are intentional fixture conditions, not findings. No deployment, real purchases, persistent database or external integrations were assessed.

Verification is bounded and sequential. Concurrent payment/refund/coupon requests were not tested; shared mutable state and synchronous endpoints warrant separate concurrency assessment, but no race vulnerability is claimed as confirmed or fixed here. Exhaustive schema coercion, malformed input fuzzing, load testing and deployment-level controls were outside this verification. Passing tests establish the covered workflows, not the absence of all possible vulnerabilities.
