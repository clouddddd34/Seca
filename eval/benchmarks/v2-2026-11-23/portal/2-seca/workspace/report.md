# Local support portal assessment

## Result

No confirmed vulnerabilities were demonstrated within the reviewed source and bounded tests. No likely findings remain supported by the evidence. This is a limited assessment, not a claim that the application is universally secure. **No application fixes were made** because the tested controls satisfy the documented requirements. Added eight reusable security control tests in [app/test_security.py](app/test_security.py); these are preservation checks, not regressions for an alleged vulnerability.

## Scope and evidence

Assessment date: 2026-11-23. Applied `assigned-skill/SKILL.md` and its access-rules/evidence references. Authorization and expected behavior come from [app/README.md](app/README.md). Reviewed all nine registered route handlers, middleware, validation, session state and HTML generation in [app/app.py](app/app.py). Runtime requests used fresh `create_app()` instances through installed FastAPI/HTTPX TestClient, with no network services. The four supplied fixture identities were used only in their documented roles.

- [Test source](app/test_security.py): reproducible assertions and synthetic inputs.
- [Executed test output](evidence/security-tests.txt): final command, exit code 0, eight passing tests.
- [Environment](evidence/environment.json): installed versions and SHA-256 hashes of application, rules and tests, identifying the assessed source.
- [Assessment log](assessment-log.md): hypotheses, disposition and limitations.

Evidence output contains no session cookies, CSRF tokens or response bodies. Fixture credentials remain confined to existing source/rules and synthetic test setup.

## Expected versus observed controls

| Boundary / expected behavior | Observed result and evidence test |
| --- | --- |
| Public navigation works; anonymous users cannot read tickets/export or logout | Public routes 200; protected requests 401; no sessions created. `test_anonymous_and_public_routes` |
| Tickets require ownership AND tenant membership | Alice, Bob and Carol each read only their own ticket; same-tenant nonowners and cross-tenant users receive 404; listing content matches ownership; missing ID 404; member exports 403. `test_ownership_and_tenant_matrix` |
| Existing sessions use current directory membership | After Alice moves north to south, her north ticket disappears from listing and detail returns 404; Carol's south ticket remains denied; restoring Alice to north restores access. `test_existing_session_tracks_tenant_migration` |
| Admin export is role restricted and limited to current tenant | North admin receives exactly north records; changing current membership to south returns exactly south records; removing admin role immediately returns 403. Admin cannot bypass ticket ownership. `test_admin_export_current_tenant_and_role` |
| Login requires exact site Origin and valid credentials | Missing/foreign/lookalike Origins return 403 and a single empty-password negative control returns 401; existing session state and access remain intact. No guessing performed. `test_login_origin_and_credentials_preserve_state` |
| Login rotates sessions | Successful second login changes session and CSRF, removes previous server session, permits new identity access and rejects old-cookie replay with 401. Cookie is HttpOnly, SameSite=strict and path `/`. `test_rotation_and_cookie_controls` |
| Logout requires session CSRF and invalidates session | Missing, invalid and previous-session CSRF each return 403 without invalidation; correct token returns 303, removes server state and cookie; subsequent access and replay return 401. `test_logout_csrf_and_invalidation` |
| Search and ticket text display literally | Synthetic script/image markup is HTML escaped in list/detail responses and search reflection; raw payload absent. Successful protected responses carry CSP, nosniff and no-store. `test_literal_search_ticket_text_and_headers` |

Source confirms the full relevant control path: middleware resolves the session name against the current user directory on every protected request and checks current admin role; list/detail independently enforce both ticket predicates; export filters current tenant. Login verifies Origin and credentials before modifying sessions; logout verifies CSRF before removal. Directory/ticket fixture changes and session transitions were inspected directly and checked through subsequent HTTP reads. No unauthorized state change or data disclosure was observed.

## Execution and changes

Executed `python -m unittest app.test_security -v` twice. Both runs reported eight tests passing. The first PowerShell stderr pipeline reported a shell error even though unittest reported OK; the second used Python subprocess capture and explicitly recorded process exit **0**. Final run: eight tests in 0.160 seconds. No additional test suite existed under `app/`.

Each test creates a fresh application. Maximum login POST attempts per instance: five (including rejected attempts). Maximum state-changing POST attempts per instance: six; at most two direct fixture changes per instance. This stays below ten logins and twenty mutations even when rejected requests and direct fixture edits are conservatively counted. Requests were sequential, redirects disabled, and all state was disposable in-memory fixture state. No raw data extraction or load tests occurred.

Only test and assessment artifacts were added; `app/app.py` remains unchanged. All protected controls listed above remain in place. No fix-specific regression was warranted.

## Fixture conditions, uncertainty and limitations

Plain HTTP, fixed fake passwords, absent rate limiting/persistent database/deployment infrastructure, and cookies without Secure are explicitly intentional fixture conditions, not findings. Early middleware denials skip the headers attached after `call_next`; their constant denial bodies showed no sensitive content, and missing headers alone were not classified as vulnerabilities.

Installed environment: Python 3.11.9, FastAPI 0.115.6, Starlette 0.41.3, HTTPX 0.26.0, AnyIO 4.13.0, Pydantic 2.13.4. External advisory lookup was prohibited; no dependency vulnerability or clean dependency claim is made. No ASVS/WSTG version-specific compliance claim is made without fetching authoritative guidance.

No real browser was used: escaping was verified at response level, not through JavaScript execution or browser cookie enforcement. Concurrency/race behavior, malformed-input fuzzing, resource exhaustion, TLS/proxy/Host configuration, production session expiry, and deployment-specific behavior were not tested. Trusted directory deletion and arbitrary attacker control of fixture storage were not assumed. No external services, packages, optional scanner, unassigned skills or subagents were used. The report covers the documented workflows and specific bounded cases, not exhaustive penetration testing.
