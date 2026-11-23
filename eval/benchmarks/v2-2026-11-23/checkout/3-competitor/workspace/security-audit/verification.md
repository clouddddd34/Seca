# Sequential refutation and post-fix review

No delegation, other skills, external traffic, package installation or source
reads outside the workspace. The authorized installed runtime was used normally.

Each candidate was re-derived from the original app/app.py, retained verbatim in
original-app.py, after hunting and before fixes. No independent-agent review is
claimed.

* Authentication: original lines 18-22 use account membership, the strongest
  control here, but removeprefix leaves `alice` unchanged. GET /wallet reaches
  lines 71-74 with no bearer token. Confirmed by baseline tests and probe.
  Known fixture bearer tokens are intentional; accepting an account name instead
  of the documented credential is the separate parser bug.
* Coupon: original lines 43-58 authenticate, check ownership, draft state,
  allowlisted coupon and funds. None consult the used-coupon set. A second
  draft receives a second 500-cent discount. Recorded redemption alone cannot
  enforce eligibility. Confirmed via independently read wallet and order state.
* Refund: original lines 61-68 enforce ownership and deny draft. A refunded order
  passes and credits its saved paid amount again. Correct discounted refund
  arithmetic does not enforce at-most-once credit. Confirmed balance 10000 to
  12500 on the second refund; not merely a misleading response.
* Cross-account IDOR: rejected. owned(), original lines 24-28, denies both absent
  and foreign orders with 404 before each read/pay/refund sink. Runtime tests
  confirm Bob cannot read or mutate Alice's draft, and saved state is unchanged.

Post-fix adversarial pass: the new guards precede mutations. Invalid coupons
still produce 422, repeated coupons 409, and coupon use is recorded only after
funds validation. Refund leaves redemption history intact and credits saved paid
rather than list total. Authentication changes preserve the documented bearer
format. All eight regression tests pass, including Bob's independent coupon and
successful retry after an insufficient-funds failure. No new external sink or
authentication exemption was introduced.

Coverage critic: all five application routes and the four automatic schema/docs
routes are mapped; no uploads, jobs, webhooks, SQL, shell, or custom HTML sinks.
Concurrency remains unverified: synchronous handlers share mutable state without
locks, so sequential guard tests must not be represented as proof of atomicity.
No concurrent exploit was demonstrated or speculative concurrency fix shipped.
Dependency advisory review and deployed configuration are outside authorized
local verification. A09 has a logging hardening note, not a demonstrated finding.
