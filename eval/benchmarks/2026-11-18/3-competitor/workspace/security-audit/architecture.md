# Architecture and scope

Standard full source assessment of app/; local Python/FastAPI with Pydantic validation, in-memory dictionaries and an order list. No database, outbound HTTP, shell, filesystem, email, or payment sink. run.py binds loopback only. No matching framework playbook. No prior audit artifacts found.



Principals: anonymous, Alice and Bob (north members), Carol (south member), north admin. Authentication and admin prefix guard: app/app.py:38-48. Invoice policy: private owner including against admin; reports: same tenant; export: admin only; prices: catalog authoritative. Public fixture tokens are explicitly not secrets.



Surfaces: GET /, /health, /me, /invoices/{invoice_id}, /reports/{report_id}, /catalog, /orders, /admin/export; POST /orders; implicit authenticated /openapi.json and router slash redirects. docs and redoc are disabled. Object dictionary reads and order append are the sensitive sinks. JSON responses only.



Run with installed packages using FastAPI TestClient; no listener, installations, external requests, or agents. At most five successful fake orders per fresh create_app instance. All application source and README are in scope despite the skill's generic fixture exclusion, because the user explicitly assigns this training application. Audit artifacts stay in the workspace, without commit/gitignore changes. No other skills used.



Deployment/proxy/TLS and external advisory lookups excluded by authorization. Dependency advisory coverage deferred. Single-context sequential refutation and post-fix critic substitute for independent agents, limiting independence.
