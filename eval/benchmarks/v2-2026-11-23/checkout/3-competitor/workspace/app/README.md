# Local checkout and returns

Use FastAPI TestClient and `create_app()` from app.py. Alice and Bob have bearer
tokens `fixture-alice` / `fixture-bob`, each starting with 10,000 synthetic cents.
Only an order's owner can read, pay, or refund it. A book costs 1,000 cents; quantities
1–3 are allowed. Orders progress from draft to paid to refunded. Payment and refund
must each affect the wallet at most once. Reject invalid transitions without changing
state. Refund the amount actually charged, including discounts.

WELCOME gives 500 cents off ONE payment per account, across all orders. A refund
does not restore eligibility. Reject attempts to reuse a coupon without charging or
changing the draft. An unused coupon remains available after a failed payment.
GET /wallet and GET /orders/{id} expose independently readable saved state.

Source inspection, fixes, local tests and all fake workflows are authorized: at most
five orders and twenty mutations per fresh instance. No external services, packages,
real purchases or credentials. In-memory wallets and synthetic bearer tokens are
intentional fixture conditions, not findings. Instances reset all state.
