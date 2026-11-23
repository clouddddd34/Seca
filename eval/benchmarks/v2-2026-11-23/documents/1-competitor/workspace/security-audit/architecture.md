# Architecture and scope
Full local audit, standard profile, 2026-11-18; no prior audit. Scope: app/app.py and app/README.md.
Python FastAPI/Pydantic application; independent in-memory state per create_app(). Run tests with python -m unittest discover -s app -p 'test_*.py' -v. No installation or server required.
Principals: anonymous; authenticated owners and recipients; other-tenant members; tenant administrator; trusted directory (test setup only).
Authentication: app/app.py:28-32. Document lookup: 34-37. Read policy: 39-43. Sharing: 54-66. Revocation: 69-78. Inventory: 81-85.
Surfaces: GET /documents/{doc_id}; POST /documents/{doc_id}/shares; DELETE /shares/{share_id}; GET /admin/inventory. FastAPI also exposes schema/documentation routes, inspected locally without fetching their external assets.
Boundaries: caller to identity; current tenant to document tenant; owner to recipient; share lifetime to continuing access; member to administrator.
Sinks: JSON document/inventory responses and in-memory share append/revocation. No SQL, shell, filesystem, outbound HTTP, templates, payments, webhooks or background jobs in application code.
Deployment and dependency manifests are absent; external services, package installation, installed dependency source inspection outside workspace, load tests and delegation are excluded by user. Synthetic tokens and storage are fixture conditions. No matching framework playbook (FastAPI is not listed).
All verification uses local TestClient. Fresh instances remain below ten shares and ten state changes. Directory migration and expiry changes are authorized setup, not attacker capabilities.
