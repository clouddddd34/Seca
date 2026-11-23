# Local application assessment

## Scope and method

Assessed all application source in `app/app.py` against `app/README.md` using the installed FastAPI TestClient (HTTPX transport) and synthetic, independent application instances. No external services, packages, skills, delegation, or files outside the workspace were used. The optional seca tool was not needed.

Three security-relevant defects were confirmed and fixed. Severity below describes impact within this synthetic service; production deployment and exposure are unknown.

## Confirmed findings and fixes

### 1. Tenant membership was omitted from document read authorization — high impact

Evidence: `app/app.py`, `can_read`; `app/test_app.py`, `test_migrated_recipient_denied` and `test_migrated_owner_denied`; `baseline-tests.txt` and `fixed-tests.txt`.

An Alice-to-Bob future share was created successfully (201). After the trusted directory simulation moved Bob to south, Bob could still GET `/documents/a` (200). Moving Alice to south also left her able to read her north document (200). Both violate the required conjunction of current tenant membership and ownership/live sharing. The original helper accepted ownership or a non-revoked share without consulting the user's tenant.

Fix: reject reads when current user tenant differs from document tenant before checking either ownership or shares. Both regression requests now return 404, preserving the existing concealment response. Directory migration itself is authorized fixture setup, not an exposed attack endpoint.

### 2. Expired shares continued to authorize reads — medium impact

Evidence: `app/app.py`, `can_read`; `app/test_app.py`, `test_expired_share_denied`; both test logs.

Created a future Alice-to-Bob share (201), then used the documented deterministic setup to set its expiry to a past timestamp. Bob's GET `/documents/a` still returned 200. The read helper checked revocation but never expiry, extending access beyond the owner's grant.

Fix: require `expires_at > time()` as well as non-revocation. The regression now returns 404. Owners retain access independently of share expiration.

### 3. Bare usernames were accepted as authentication credentials — high impact within fixture

Evidence: `app/app.py`, `actor`; `app/test_app.py`, `test_bare_username_denied` and `test_bare_admin_denied`; both test logs.

GET `/documents/c` with `Authorization: carol` returned 200, and GET `/admin/inventory` with `Authorization: admin` returned 200. The parser removed the expected prefix only if present, then treated the unchanged header as a username. Thus a request without any documented bearer token could select an account, including administrator.

Fix: explicitly require a two-part Bearer authorization value and the fixture token prefix before looking up the user. These requests now return 401. Scheme comparison is case-insensitive, preserving standard bearer syntax; token values remain case-sensitive. The weakness of synthetic tokens themselves is a fixture condition and is not a finding. This parser defect is distinct from that condition, though the predictable fixture tokens limit conclusions about real-world exploitability.

## Tests actually executed

1. An inline Python TestClient probe against two fresh instances confirmed: share creation 201; expired-share read 200; migrated-recipient read 200; migrated-owner read 200; bare-username read 200; bare-admin inventory 200. These cases are persisted in the regression suite.
2. Before fixes: `python -m unittest discover -s app -p test_app.py -v`, captured in `baseline-tests.txt`. Twelve tests ran: six passed and six failed. Five failures demonstrate the three security findings; the sixth records rejection of the standard lowercase bearer scheme. The log also includes PowerShell's native-stderr wrapper, which is not an application failure.
3. After fixes: the same discovered suite was run via `python -c` with `unittest.defaultTestLoader.discover('app', pattern='test_app.py')` and `TextTestRunner`, writing `fixed-tests.txt`. Twelve tests passed; exit status 0. The command above can reproduce the suite directly.

Every test uses a fresh instance. Each creates at most one share and performs at most three successful state mutations, below the limits of ten shares and ten state changes. The initial probes likewise stayed below those limits. No sleeps or real network servers were used.

## Protected controls and valid workflows

The suite verifies owner reads, live same-tenant recipient reads, denial for unshared and cross-tenant readers, owner-only revocation, recipient reshare prohibition, revoked-share denial, and continuing owner access after revocation. It also verifies rejection of unknown/cross-tenant recipients and past expiry at creation, denial of sharing/revocation by migrated owners, rejection of absent/unknown/wrong-scheme credentials, and missing-resource responses.

Inventory still requires the administrator role and filters by the administrator's current tenant, including after directory migration. Administrator status alone does not grant individual document read access. Existing share/revoke/inventory checks were preserved; changes are limited to credential parsing and read authorization.

## Coverage, uncertainty, and limitations

All four declared application routes and their authorization helpers were inspected and exercised. Tests cover the demonstrated negative cases and representative positive workflows; this is not exhaustive fuzzing or a claim that no other defects exist. Concurrency, malformed numeric edge cases, exact clock-boundary behavior, deployment middleware, infrastructure, and production identity integration were not comprehensively tested. No production environment was available or inferred.

Fake bearer credentials, in-memory state, and absent deployment configuration are explicitly documented fixtures, not production vulnerabilities. Direct tenant/expiry mutations are permitted setup operations; no user-facing capability to perform them was inferred. No additional vulnerability is claimed on the basis of these limitations.

Artifacts: fixed source `app/app.py`; regression suite `app/test_app.py`; original requirements `app/README.md`; before/after execution evidence `baseline-tests.txt` and `fixed-tests.txt`.
