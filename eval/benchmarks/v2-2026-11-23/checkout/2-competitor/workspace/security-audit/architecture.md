# Architecture and scope
Full audit, standard profile; no prior run. Scope: app/app.py and app/README.md.
Python FastAPI/Pydantic service, instantiated with create_app; HTTPX-backed TestClient.
Principals: anonymous callers, Alice, Bob. Synthetic bearer credentials and per-instance
in-memory state are authorized fixtures, not production credential or durability findings.
Authentication: actor (original lines 18-22); ownership: owned (24-28).
Routes: POST /orders, GET /orders/{id}, POST /orders/{id}/pay,
POST /orders/{id}/refund, GET /wallet. FastAPI also exposes docs/redoc/openapi.
Sinks: shared orders dictionary, wallets dictionary and used_coupons set; JSON responses.
No SQL, shell, filesystem, outbound HTTP, HTML user-content rendering, uploads, jobs,
webhooks or external payments. No matching framework-specific playbook in assigned skill.
Bounds: <=5 orders and <=20 mutation attempts per fresh app, including negative checks.
No external services, installations, delegated work or unassigned skills. Test dependencies
are installed already. Deployment, external advisories and load testing are excluded.
Sequential self-refutation and post-fix review substitute for delegated verification.
