# Assessment log

Scope: app/ source and local FastAPI/HTTPX TestClient only. Rules: app/README.md.
No external requests, packages, delegated work, or unassigned skills.
Each test uses a fresh instance, at most five orders and twenty mutations.

Source reviewed: all app/app.py routes, authentication, ownership, validation,
wallet and coupon state. Candidates: bare account authentication; repeated
refund; coupon reuse. Runtime verification pending. Threaded atomicity remains
a review concern; no production/concurrent behavior claim yet.

Access matrix (documented fixture rules): authenticated Alice/Bob may create,
read their wallet, read/pay/refund their own orders subject to state; another
account cannot read/pay/refund; missing/invalid bearer credentials cannot access.
No administrative roles exist. Intentional in-memory state and fixture tokens
are excluded as findings.

Completed: nine pre-fix tests established F-001 bare-name authentication, F-002
refund replay, F-003 coupon reuse (four failing tests). Applied minimal guards.
Nine post-fix tests passed, followed by ten final tests including credential-format
coverage; actual Python exit 0. See evidence/final-tests.txt and report.md.
Protected ownership, transition, quantity, insufficient-funds, per-account coupon,
and exact-refund controls passed. Every test used fresh state and enforced bounds.
No outstanding confirmed findings. Concurrent atomicity remains unverified;
dependency advisory lookup and deployment review were excluded by scope.
