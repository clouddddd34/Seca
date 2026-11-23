# Local support portal security assessment

Assessment date: 2026-11-18. **No security vulnerability was confirmed in the reviewed source and bounded tests.** All seven tests passed. This is a limited assessment, not a comprehensive penetration test or a claim that the application is secure.

## Scope and evidence

Applied [assigned-skill/SKILL.md](assigned-skill/SKILL.md), including its authorization and evidence references. Reviewed the complete [application](app/app.py) and [access rules](app/README.md). Runtime checks used installed FastAPI/HTTPX TestClient against fresh `create_app()` instances, without a network server. No external services, packages, unassigned skills, or delegation were used.

- [Control tests](app/test_security.py): reproducible assertions, synthetic inputs, and direct session/ticket state observations.
- [Executed test output](evidence/test-results.txt): seven passing tests, final runner exit code 0.
- [Assessment log](assessment-log.md): hypotheses, progress, outcomes, and limitations.
- [Copied candidate template](evidence/candidate-template.json): unused skill template, **not a finding**.

Assessed `app/app.py` SHA-256: `E6B0DBACD14EC56805FAF9E0E5A67342A1F0B53FE0AC10EB4847D98DF34D2259`. Application source was not modified. Environment: Python 3.11.9; FastAPI 0.115.6; Starlette 0.41.3; HTTPX 0.26.0; AnyIO 4.13.0.

## Findings and fixes

Confirmed findings: none. Likely findings: none. The tested authorization, session, CSRF, and escaping failure hypotheses were not reproduced. No application fix was justified; the added tests preserve the observed controls and provide regression coverage for future changes.

The middleware returns early for unauthenticated and non-admin denials, before adding its response security headers. This is a source-level configuration observation, not a demonstrated vulnerability: the responses contain static denial messages. No change was made solely for missing headers.

## Access rules and protected controls

Expected results below come from `app/README.md` and are corroborated by source. These are documented task requirements, not assumptions about an external deployment.

| Actor / relationship | Action | Expected and observed result | Test evidence |
| --- | --- | --- | --- |
| Anonymous | Public navigation; protected reads/logout | Public pages 200; protected operations 401 | `test_anonymous_and_public_routes` |
| Alice, Bob, Carol / own ticket in current tenant | List and read | Own text visible; detail 200 | `test_ticket_ownership_and_tenant_matrix` |
| Member / another owner's ticket, same or different tenant | Read/list | Detail 404; foreign text absent from list and denial | `test_ticket_ownership_and_tenant_matrix` |
| Alice migrated north to south / existing session | Read original ticket or Carol's ticket | Both 404; original text absent from list; fixed ticket state unchanged; return to north restores own access | `test_current_membership_after_migration` |
| Member | Admin export | 403 | `test_ticket_ownership_and_tenant_matrix` |
| Admin / current tenant | Export | Exact north ticket set; after migration exact south ticket set | `test_admin_export_current_tenant_and_role` |
| Admin / another owner's ticket | Detail read | 404; no admin ownership bypass | `test_admin_export_current_tenant_and_role` |
| Admin demoted in directory / existing session | Export | 403 | `test_admin_export_current_tenant_and_role` |

Source trace: `boundary` authenticates cookies using the server session map and reads the current directory user for each request. It checks the current admin role before export. Both `tickets` and `ticket` require ownership AND current tenant membership. `export` filters by current tenant. The tests compare actual ticket contents and export objects, not only status codes.

Other protected controls verified:

- Login rejects missing or foreign Origin without creating a session. Successful login rotates the token, removes the old session, and permits the new session; replay of the old cookie fails.
- Logout rejects missing/wrong CSRF while preserving the session and valid ticket access. GET does not log out. Valid CSRF removes server state and the client cookie; replay then fails.
- Search and ticket text encode a synthetic script-shaped string literally in HTML. Successful ticket pages retain CSP, `nosniff`, and `no-store`. Login cookies retain HttpOnly and SameSite=Strict.

## Tests actually executed

1. `python -m unittest app.test_security -v` through a PowerShell `2>&1 | Tee-Object` pipeline: seven tests reported OK. PowerShell wrapped unittest's stderr as a native-command error and the tool reported shell exit 1; this was not treated as a clean process result.
2. Reran the same suite with `unittest.defaultTestLoader.loadTestsFromName('app.test_security')` and `TextTestRunner`, capturing output in memory and writing UTF-8 to `evidence/test-results.txt`. Python explicitly exited according to `result.wasSuccessful()`: seven tests passed, exit 0. No application changes occurred between runs.

To reproduce independently from workspace root: `python -m unittest app.test_security -v`.

Every test creates a fresh app and disables redirect following. Each instance uses at most four login attempts and fewer than twenty mutations, even counting denied POSTs, directory changes, and synthetic ticket text changes. Each rerun creates fresh instances. No credentials, cookies, or CSRF values were saved in test output. State-changing checks inspect server state and subsequent reads; state disappears with each test instance.

## Coverage and limitations

Covered all declared application routes through source review and representative runtime requests; anonymous, all three member identities, admin, current membership changes, role revocation, ownership/tenant combinations, session rotation, logout CSRF, and HTML encoding. No scanner was run; optional seca was unnecessary. No external ASVS/WSTG guidance was fetched or control-version conformance claimed.

Unverified areas include concurrent requests/races, malformed-input robustness, exhaustive URL normalization and method permutations, browser execution, production proxy/Host trust, TLS, deployment configuration, session expiration policy, and dependency advisories. Installed versions were recorded, but current advisory lookup was prohibited by the no-external-services scope; no dependency safety or vulnerability conclusion is made. Tests do not establish behavior of a deployed service.

Plain HTTP, fixture passwords, absent rate limiting and persistent storage, missing production infrastructure, and the lack of Secure cookies are explicitly intentional fixture conditions in the README, not findings. No account-removal or session-expiration requirement is specified. Additional deployment requirements would require separate assessment.
