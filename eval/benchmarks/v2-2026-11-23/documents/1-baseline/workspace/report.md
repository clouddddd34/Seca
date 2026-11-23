# Local application assessment

Three bugs were confirmed and fixed in `app/app.py`. The regression suite now passes all 11 tests. Assessment used only workspace source and in-process FastAPI/HTTPX TestClient requests with installed packages. No skills, delegates, external services, package installation, or optional seca tooling were used.

## Scope and evidence

- Access contract and authorized fixture setup: `app/README.md`.
- Reviewed implementation: all of `app/app.py`, including authentication and all four application endpoints.
- Reproductions and regression tests: `app/test_app.py`.
- Before-fix execution: `baseline-tests.txt` (11 tests, five failed assertions across four test methods, corresponding to the three findings below).
- After-fix execution: `fixed-tests.txt` (11 tests, all pass; Python exit code 0).

Line references below refer to the fixed source. Each test creates a fresh independent instance. No instance creates more than one share or performs more than two state changes, counting successful share creation, revocation, and direct fixture mutations. All requests remain in process.

## Confirmed findings and fixes

### 1. Document reads omit current tenant membership

**Evidence:** `app/app.py:42`, tests `test_migrated_owner_denied` and `test_migrated_recipient_denied` in `app/test_app.py`, failures in `baseline-tests.txt`.

The original `can_read` accepted ownership immediately and accepted an unrevoked share without comparing the actor's current tenant to the document's tenant. On separate instances, moving Alice to south and reading her north document a returned 200; creating an Alice-to-Bob share, then moving Bob to south and reading a also returned 200. Both should return 404 under the documented conjunctive access rule. Previously authorized users could retain document contents after leaving the tenant.

**Fix:** Require current tenant equality before checking either ownership or shares. Both reproductions now return 404. Directory migration is an authorized test precondition, not an exposed API or a separate vulnerability.

### 2. Expired shares continue granting access

**Evidence:** `app/app.py:47`, `test_expired_share_denied`, `baseline-tests.txt`.

Alice creates a future share for Bob (201); Bob initially reads a (200). Setting that share's expiry to a past Unix timestamp, as authorized by the README, still allowed Bob to read a (200). The read predicate checked revocation but omitted expiration, extending disclosure beyond the owner's chosen deadline.

**Fix:** A share must satisfy `time() < expires_at` as well as the existing document, recipient, and revocation checks. The expired read now returns 404; valid future shares still return 200. Direct expiry mutation is deterministic fixture setup, not a user-facing attack capability.

### 3. Bare usernames accepted as authentication

**Evidence:** `app/app.py:28`, `test_bare_identity_is_not_bearer_token`, two subtest failures in `baseline-tests.txt`.

The original parser used `removeprefix` without requiring the prefix to exist. Consequently `Authorization: alice` fetched document a (200), and `Authorization: admin` fetched north inventory (200), without supplying a documented bearer token. This is a confirmed parsing defect relative to the fixture's authentication contract. Its production exploitability cannot be inferred from this synthetic authentication system.

**Fix:** Require the existing `Bearer fixture-` prefix before extracting and validating the identity. Both bare-identity requests now return 401. Documented fixture tokens remain valid. This finding concerns accepting an unintended credential form, not the intentional availability or simplicity of fixture tokens.

## Tests executed and preserved controls

Executed `python -m unittest discover -s app -p test_app.py -v` before and after fixes. The first post-fix run reported all tests passing, but PowerShell's stderr redirection surfaced unittest output as a NativeCommandError and the shell reported exit 1. A final run used Python `subprocess.run` to combine stdout/stderr, write `fixed-tests.txt`, and propagate the actual Python return code: 0. The baseline log retains PowerShell's wrapper diagnostics and the underlying assertion failures.

The 11 test methods cover:

- Expired-share rejection and valid-share reads.
- Migrated owner and recipient read rejection.
- Bare-identity authentication rejection for member and admin.
- Owner reads, same-tenant share creation, recipient reads, owner revocation, and revoked-share rejection.
- Unshared reads and cross-tenant reads denied; admin role alone does not grant document reads.
- Unknown recipients, cross-tenant recipients, and past-expiry shares rejected without creating shares.
- Recipients cannot reshare or revoke, and failed revocation leaves their valid read intact.
- Migrated owners cannot create or revoke shares.
- Inventory requires admin role and follows the admin's current tenant, including after migration.
- Missing, unknown, and incorrect-scheme credentials rejected; missing documents and shares return 404.

Existing share creation and revocation ownership/tenant controls, recipient validation, inventory tenant filtering, and read-denial status codes were preserved. Changes are limited to the demonstrated authentication and read-authorization defects, with tests added separately.

## Coverage and limitations

This is a bounded source review and functional authorization assessment of the supplied local service, not proof that no other bugs exist. Tests exercise all four application endpoint types. They do not exhaust arbitrary malformed bodies, non-finite numeric values, concurrent requests, exact wall-clock expiry boundaries, every credential variation, or every combination of multiple shares. No load testing, deployment review, network testing, or dependency audit was performed.

Fake tokens, in-memory state, and absent deployment configuration are explicitly fixture conditions and are not reported as production vulnerabilities. No real directory, persistent datastore, or production authentication provider was available or evaluated. The README's `from app import create_app` works with `app/` on the Python import path; the test file sets that workspace-local path explicitly because the supplied directory contains `app.py` without a package initializer. This packaging detail was not treated as a security finding.
