# Local application architecture

Full audit, standard profile, 2026-11-18; no previous audit or Git repository.
Scope: all four original files in app/. Python FastAPI/Pydantic API with
in-memory fixture identities, invoices, reports, catalog and per-instance orders.
No matching framework-specific playbook. Only the assigned owasp-audit skill is used.

Run: installed Python packages and FastAPI TestClient, without a network listener.
app/run.py binds to loopback when used, but is not run for this assessment.

Principals: anonymous callers, Alice and Bob (north members), Carol (south
member), and north admin. app/app.py:37-48 authenticates every path except
/ and /health, attaches the server-side identity, and gates /admin paths.
Invoice authorization is at :63-68; report lookup at :70-74; order ownership
at :85 and :92-94. Public fixture credentials are intentional, not leaked secrets.

Entry surfaces: GET /, /health, /me, /invoices/{invoice_id},
/reports/{report_id}, /catalog, /orders, /admin/export; POST /orders.
FastAPI also registers authenticated GET /openapi.json; docs and redoc are disabled.
No jobs, webhooks, uploads, frontend templates, databases or alternate source files.

Boundaries: anonymous to authenticated API; member to admin; user to another
invoice owner; tenant to another tenant's reports; client price to authoritative
catalog; current user to stored order owner. Sinks: JSON responses and append to
the local order list. No shell, filesystem, outbound HTTP, email or payment sinks.

All runtime checks stay in-process with fake data and at most five orders per
fresh create_app() instance. External services, other software, package installs,
agent delegation and deployment probing are excluded by user instruction.
Dependency manifests may be read; external advisory freshness is not assessed.
No commit or ignore changes are requested or made; artifacts stay in this workspace.
