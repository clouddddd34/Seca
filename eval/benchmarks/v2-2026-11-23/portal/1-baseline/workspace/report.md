# Local support portal assessment

## Result

No confirmed security vulnerability was found in the reviewed source and bounded checks of the documented workflows. This is a scoped result, not proof that all possible inputs and deployments are secure. No application source fixes were made. Added `app/test_assessment.py` to make the verified controls repeatable; there are no fix-specific regression tests because no fix was justified.

## Scope and method

Read `app/README.md` and all of `app/app.py`. Used the installed FastAPI/HTTPX TestClient against `create_app()` in process. All requests were synthetic and local; an untrusted Origin string was only a request header, never an external destination. No services, packages, skills, delegation, or optional seca tool were used. Work artifacts stayed in this workspace.

Each test creates a fresh application. The largest test performs four login requests and two trusted state changes: at most four logins and six mutations per instance, counting POST attempts and direct state assignments conservatively. These are below the README limits of ten logins and twenty mutations. Invalid credentials were one deliberately invalid negative test, not credential guessing. Tenant changes simulate the expressly authorized directory migration; a role change and a synthetic ticket text assignment are test fixtures, not attacker capabilities.

## Evidence and protected controls

| Control | Source evidence | Executed test evidence and result |
| --- | --- | --- |
| Public navigation and authentication boundary | `app/app.py:32-41`, `48-61` | `app/test_assessment.py:24`: public pages return 200; anonymous protected routes and unknown session return 401. |
| Login Origin and credential validation | `app/app.py:63-73` | `app/test_assessment.py:33`: absent/foreign Origin returns 403, deliberately invalid password returns 401, no session created. |
| Ticket ownership AND tenant membership | `app/app.py:82-98` | `app/test_assessment.py:43`: all four users checked against all three tickets and list links; only the owning member sees a ticket. Other and missing tickets return 404, including for admin. |
| Current directory membership in existing sessions | `app/app.py:38-39`, `86`, `96` | `app/test_assessment.py:55`: migrating Alice to south hides her north ticket without re-login and does not expose Carol's ticket; restoring north restores valid access. |
| Admin role and current-tenant export | `app/app.py:40-41`, `100-102` | `app/test_assessment.py:65`: all members denied with 403; admin exports exactly Alice/Bob in north, then exactly Carol after migration to south; role removal denies the existing session. |
| Session rotation and cookie attributes | `app/app.py:74-79` | `app/test_assessment.py:80`: login changes the token, invalidates the prior token, permits the new user's ticket, and sets HttpOnly, SameSite=Strict, Path=/. |
| Logout CSRF and invalidation | `app/app.py:87-91`, `104-112` | `app/test_assessment.py:95`: missing/wrong CSRF returns 403 while preserving the session; GET returns 405; valid logout returns 303, removes the cookie/session, and rejects replay. |
| Literal HTML rendering and response controls | `app/app.py:43-45`, `84`, `89`, `98` | `app/test_assessment.py:109`: tag, ampersand, and quote payload is escaped in search and ticket text; authenticated HTML retains CSP, nosniff, and no-store. |

All these controls and successful workflows remain unchanged.

## Tests actually executed

1. `python -m unittest app.test_assessment -v` with PowerShell stderr redirection through `Tee-Object`: eight tests passed, but PowerShell classified native stderr output as a `NativeCommandError` and the shell tool reported exit 1. This was a logging issue, not an assertion failure.
2. Repeated the same suite with the runner explicitly writing stdout, capturing clean output in `app/assessment-results.txt`:

```powershell
python -c "import sys, unittest; suite = unittest.defaultTestLoader.loadTestsFromName('app.test_assessment'); result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite); sys.exit(not result.wasSuccessful())" | Tee-Object -FilePath app/assessment-results.txt
exit $LASTEXITCODE
```

Result: **8 tests passed, process exit 0**. The second run used new application instances throughout. The saved output records this second run.

## Observations, fixture conditions, and limitations

The middleware's early 401/403 responses return before its security-header assignments (`app/app.py:35-45`). These responses contain constant denial text, and no sensitive-data disclosure or executable content was demonstrated. This is a source observation, not a confirmed exploitable vulnerability; header assertions cover authenticated HTML, not every response.

Plain HTTP, absence of Secure cookies, fixed synthetic passwords, no rate limiting, in-memory storage, and missing production deployment infrastructure are explicitly intentional fixture conditions in `app/README.md`. They are not findings. Search is verified for literal display as specified; no filtering semantics are assumed.

Coverage includes every declared endpoint and the principal positive and negative authorization paths. Tests validate response HTML and headers, not browser execution or browser enforcement of cookies/CSP. No exhaustive fuzzing, malformed encoding/non-ASCII credential testing, concurrency testing, load testing, dependency audit, proxy/host configuration review, or production deployment assessment was performed. User deletion, arbitrary ticket-key mutation, and hostile changes to trusted directory state are outside the documented migration workflow. No claims are made about those unverified cases.
