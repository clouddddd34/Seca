# Architecture and scope

Full audit, standard profile, 2026-11-18; no prior audit. Python/FastAPI document collaboration fixture, all application source in app/app.py. No matching framework-specific playbook. Tests use installed FastAPI/HTTPX TestClient, fresh create_app instances, no sockets or external services.

Principals: anonymous callers; Alice/Bob (north), Carol (south), north admin. Trusted directory migration changes current user tenant, never document ownership/tenant. actor (app/app.py:28) maps fixture identities. document (:34) resolves objects. can_read (:39) gates document responses. share (:54) and revoke (:68) gate mutations by owner plus current tenant. inventory (:81) gates admin role and filters current tenant.

Surfaces: GET /documents/{doc_id}, POST /documents/{doc_id}/shares, DELETE /shares/{share_id}, GET /admin/inventory. Framework-generated /openapi.json, /docs, /docs/oauth2-redirect and /redoc expose schema/help only. No jobs, webhooks, uploads, SQL, shell, outbound HTTP, or user-controlled HTML rendering.

Sinks: copied document/inventory JSON, append to in-memory shares, setting revoked. Boundaries: caller to document owner, current tenant to original document tenant, live versus expired/revoked grants, member to administrator, owner to recipient.

Out of scope: deployment, external services/advisories, package installation and dependency source outside workspace. Fake bearer tokens, in-memory storage and absent deployment settings are explicitly excluded fixture conditions. Directory and expiry state edits are authorized test setup. At most ten shares and ten state changes per fresh instance. No delegation or unassigned skills. Artifacts retained locally without git operations.
