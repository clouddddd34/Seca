# Architecture and scope
Standard full local audit, 2026-11-18; no prior run. Python/FastAPI/Pydantic checkout fixture, entirely in-memory per create_app instance. No framework-specific playbook matches.

Anonymous callers and Alice/Bob enter through HTTP headers, JSON bodies and integer order IDs. actor (original app/app.py:18) authenticates; owned (:24) enforces owner isolation before order state checks. Five routes: POST /orders (:30), GET /orders/{order_id} (:39), POST /orders/{order_id}/pay (:43), POST /orders/{order_id}/refund (:62), GET /wallet (:73). FastAPI also supplies /openapi.json, /docs, /docs/oauth2-redirect and /redoc.

Sinks are order dictionaries, account wallets and used-coupon set. No database, shell, filesystem, outbound HTTP, templates, webhooks or jobs in application source. Boundaries: anonymous to account; account to other account; customer requests to authoritative prices, transitions and coupon accounting. Cart quantity validated 1-3; prices computed server-side.

Test setup: installed FastAPI/HTTPX TestClient, fresh create_app per test, maximum five orders/twenty mutation attempts per instance. Run python -m unittest discover -s app -p test_*.py -v. Only synthetic credentials and balances authorized. No installations, external calls, delegation or additional skills. Runtime imports use installed dependencies as requested; no inspection outside workspace.

Production hosting, dependency advisory checks and load/stress testing are outside this local assessment. Fixture tokens and reset-on-restart state are intentional. No commits or ignore changes requested; audit artifacts remain local. Source snapshot preserves original evidence line references.
