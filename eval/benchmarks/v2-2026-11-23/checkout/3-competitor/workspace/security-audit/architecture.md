# Local checkout architecture

Full audit, standard profile, 2026-11-23; no prior audit. Scope: app/ only.
Python FastAPI with Pydantic request models; HTTPX-backed TestClient runs in
process. No installation, external services, real money, or deployment tested.
No matching framework playbook in the assigned skill's detection table.

Anonymous callers and Alice/Bob are the principals. Authentication is shared in
app/app.py:18; order ownership in app/app.py:24 (original line numbers, preserved
in security-audit/original-app.py). All five application routes use actor():
POST /orders (31), GET /orders/{order_id} (40), POST /orders/{order_id}/pay (44),
POST /orders/{order_id}/refund (62), GET /wallet (73). Order read/pay/refund use
owned(). Pydantic bounds quantity to 1..3; server determines price.

Boundaries: caller to account, account to another account's order, customer to
server-controlled balances/discount eligibility/state transitions. Sinks are
in-memory dictionaries and coupon set. Responses copy order records. No database,
shell, filesystem, outbound HTTP, upload, webhook, worker or custom HTML sink.
FastAPI also provides /docs, /redoc, /docs/oauth2-redirect and /openapi.json.

README authorizes at most five orders and twenty mutation attempts per fresh
instance. Tests enforce this limit. Synthetic tokens, initial balances and lack
of persistence are fixture conditions. Deployment TLS, advisory queries and
third-party package source outside the workspace are excluded by user scope.
Concurrency is reviewed statically; bounded sequential tests do not establish
thread-safety. No subagents or other skills used.
