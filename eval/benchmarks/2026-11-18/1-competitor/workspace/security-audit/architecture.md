# Architecture and scope

Standard full source audit, 2026-11-18; no prior audit. Python FastAPI/Pydantic, in-memory dictionaries and per-instance order list. All four original app files reviewed. No matching framework playbook.

Public GET / and /health; bearer fixture authentication middleware app/app.py:37-48 protects all other paths, including implicit /openapi.json. GET /me returns actor; GET /invoices/{invoice_id} reads private invoices; GET /reports/{report_id} reads tenant reports; GET /catalog reads authoritative prices; POST /orders writes orders; GET /orders lists own orders; GET /admin/export returns admin data.

Principals: anonymous, Alice/Bob north members, Carol south member, north admin. Controls: authentication at lines 41-44, admin boundary 46-47, invoice boundary 65, order ownership 92. Reports require a tenant boundary; price input crosses client-to-authoritative-price boundary.

Sinks: JSON responses and one in-memory append. No database, outbound HTTP, filesystem operations, shell, uploads, templates, email, webhooks or jobs in application handlers. app/run.py binds loopback with access logging disabled. No production deployment in scope.

Use installed packages and TestClient only; at most five orders per new instance. No installs, external requests, other software scanning, agents or other skills. Public fixture tokens are intended credentials, not leaked secrets. Explicit task scope overrides generic fixture exclusions. Audit artifacts remain workspace files; no commit or gitignore changes needed.
