# Local support portal assessment

## Outcome and scope

One confirmed low-severity input-handling defect was fixed at two comparison sites. No ownership, tenant, administrator, session-replay, CSRF-bypass, or HTML-injection vulnerability was demonstrated by the bounded checks. This is not a claim that all possible vulnerabilities have been excluded.

Scope and access rules came from `app/README.md`. Reviewed all of `app/app.py`. Used installed FastAPI/HTTPX TestClient in process; no external services, package installation, skills, delegation, or optional seca tools. All assessment files were written within this workspace. Each test creates a fresh application; helpers enforce at most ten login attempts and twenty mutations per instance, including directory migration. The initial probe used three login attempts and two logout attempts. Each regression suite instance stayed within the same limits.

## Confirmed finding F1: non-ASCII comparison input raises HTTP 500

Severity: low; request-level error handling/robustness. No authentication bypass, session invalidation, persistent outage, or process-wide denial of service was demonstrated.

Evidence: `app/app.py:72` (login) and `app/app.py:107` (logout); regression coverage at `app/test_app.py:45` and `app/test_app.py:82`.

Before the fix, `secrets.compare_digest` received Python strings. Its string mode accepts only ASCII. A valid URL-encoded non-ASCII value therefore raised `TypeError: comparing strings with non-ASCII characters is not supported`.

A bounded TestClient probe with `raise_server_exceptions=False` produced:

| Request | Original status |
| --- | --- |
| POST /login, same-site Origin, alice, password=wrong | 401 |
| POST /login, same-site Origin, alice, password=café | 500 |
| POST /login, same-site Origin, valid Alice credentials | 303 |
| POST /logout, authenticated, csrf=wrong | 403 |
| POST /logout, authenticated, csrf=café | 500 |

The login error is reachable without authentication for an existing fixture username. Logout requires an authenticated session. Different responses for known and unknown usernames may also distinguish account existence; this was not separately verified or treated as an independent finding.

Fix: encode both operands as UTF-8 bytes before constant-time comparison. Invalid Unicode passwords now receive 401 and invalid Unicode CSRF fields receive 403, while valid login/logout retain their behavior. No authorization predicates, cookie attributes, Origin policy, or token generation changed. Rejected logout attempts retain the active session.

## Tests actually executed

1. Original application probe described above: completed, confirmed two 500 responses.
2. `python -m unittest discover -s app -t . -p test_app.py -v`: failed before running tests because `app` is not an importable discovery start directory under this configuration. No package change was needed; direct module invocation works.
3. `python -m unittest app.test_app -v`: **7 tests passed**, 0.153 seconds reported by unittest.
4. Original-comparison regression check: read the patched source, replaced only the two changed comparisons in memory, compiled it, and ran the two regression methods against that factory. **2 tests executed, 2 expected TypeError errors, 0 assertion failures**. The fixed file was not reverted. This confirms the tests detect the original defect, not merely successful behavior after editing.

The suite is reproducible from the workspace root with `python -m unittest app.test_app -v`.

## Protected controls and coverage

| Control/workflow | Evidence and result |
| --- | --- |
| Public navigation and authentication boundary | `app/test_app.py:36`: home/help/login work; anonymous ticket/list/export/logout and unknown session denied. Middleware at `app/app.py:33`. |
| Login Origin and credentials | `app/test_app.py:45`: missing/foreign Origin denied; wrong, empty, Unicode credentials and unknown account rejected; valid login succeeds. |
| Ownership AND tenant | `app/test_app.py:54`: all four fixture accounts checked against all three tickets, listing visibility, missing ticket, and admin route. Admin has no implicit ownership override. Predicates at `app/app.py:83` and `app/app.py:94`. |
| Current directory membership | `app/test_app.py:65`: Alice's existing session loses old-tenant access after migration, cannot access Carol's ticket, regains owned ticket when moved back. Ticket records remain fixed. |
| Tenant-limited admin export | `app/test_app.py:76`: exact north rows before migration and exact south row afterward with existing admin session. Export at `app/app.py:101`. |
| Session rotation and logout | `app/test_app.py:82`: token rotation removes old token; replay denied; missing/incorrect/Unicode/stale CSRF rejected; valid CSRF invalidates session and clears cookie; logged-out token replay denied. HttpOnly and SameSite=strict preserved. |
| Literal search and response controls | `app/test_app.py:104`: script/image/quote/ampersand payload appears escaped; authenticated response retains CSP, nosniff and no-store. Ticket text also uses `html.escape` in source. |

## Fixture conditions, uncertainty and limitations

Plain loopback HTTP, fixed fake passwords, missing rate limiting/persistence/deployment infrastructure, and lack of Secure cookies are intentional fixture conditions per README, not findings.

Middleware returns authentication/role denials before adding its response headers. This is a source observation, not a demonstrated data disclosure or exploit: those early responses contain static denial messages. The header test covers a successful authenticated response, not every response path.

Tests are sequential and bounded. No browser JavaScript execution, network deployment, concurrency/race testing, load testing, exhaustive route encoding/fuzzing, malformed byte-body testing, directory account deletion, or production proxy/Host configuration testing was performed. Search escaping was checked in returned HTML; browser rendering was not exercised. Trusted directory migration was simulated exactly through app.state.users as authorized. No unsupported assumptions about production infrastructure were used to invent findings.

Changed files: `app/app.py` (two comparison fixes), `app/test_app.py` (seven local tests), and this report.
