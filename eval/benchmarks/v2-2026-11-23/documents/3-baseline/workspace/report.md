# Local application assessment

## Scope and result

Assessed `app/app.py` against `app/README.md` using source inspection and installed FastAPI TestClient (HTTPX transport), entirely in process with synthetic state. Three distinct bugs were confirmed and fixed. No skills, delegation, external services, package installation, or optional seca execution were used. All assessment artifacts are in this workspace.

Each test creates an independent application. Each instance creates at most one share and has at most two persistent state changes, counting share creation, revocation, and authorized fixture edits. This is below both README limits of ten. Expiry is exercised by setting a newly created share's timestamp into the past, and migration by editing the current user's tenant as authorized. An additional expiry-boundary test patches the application clock without sleeping.

## Confirmed findings

### 1. Current tenant membership missing from document reads

**Impact:** A user moved out of north can still retrieve north document content, whether that user owns the document or has a live share. This violates the requirement that current membership and ownership/live sharing must both hold.

**Evidence:** In the original `can_read`, ownership immediately returned true, and the share branch never inspected the user's tenant. `test_migrated_owner_denied` changes Alice's tenant to south and requests `GET /documents/a` with Alice's bearer token. `test_migrated_recipient_denied` first creates Alice's share to Bob, moves Bob to south, and requests the same document with Bob's token. Both returned 200 before the fix instead of 404. See `evidence/app-before.py`, `evidence/before-tests.txt`, and `app/test_app.py`.

**Fix:** `app/app.py:can_read` now denies mismatched current/document tenants before checking either ownership or shares. Both reproductions now return 404. Document ownership and tenant remain unchanged. Migration is trusted test setup, not an exposed attack capability; the confirmed issue is continued access after that change.

### 2. Share expiration not enforced when reading

**Impact:** A recipient can continue reading a shared document after the grant expires, until revocation or another independent restriction applies.

**Evidence:** The original read predicate checked revocation but ignored `expires_at`. `test_expired_share_denied` creates a future share to Bob, sets its expiry into the past, and reads as Bob. `test_expiry_boundary_denied` tests the exact expiry instant. Both returned 200 before the fix instead of 404. See `evidence/before-tests.txt` and the named tests in `app/test_app.py`.

**Fix:** The share predicate now requires `time() < expires_at` as well as matching document/recipient and non-revocation. Both tests now return 404. Future shares and owner access remain valid.

### 3. Bare usernames accepted as authentication

**Impact within this fixture:** A request can impersonate a known user without submitting the documented bearer token, including accessing the administrator's inventory.

**Evidence:** The original `actor` used `removeprefix` without requiring the prefix; a bare username survived unchanged and matched the users map. `test_bare_identity_is_not_bearer_authentication` verifies `Authorization: alice` on `GET /documents/a` and `Authorization: admin` on `GET /admin/inventory`. Both returned 200 before the fix instead of 401. See `evidence/before-tests.txt` and `evidence/app-before.py`.

**Fix:** `actor` now requires a Bearer scheme and fixture-token prefix before looking up the identity. The scheme comparison is case insensitive. Bare identities now return 401; documented fixture bearer tokens still work.

**Fixture distinction:** The predictability of fake tokens is explicitly out of scope and is not a finding. This finding concerns acceptance of an undocumented credential form. Production exploitability or severity cannot be inferred from the fixture's deliberately public credentials.

## Fix and evidence paths

- `app/app.py`: focused authentication and document-read fixes; sharing, revocation, and inventory handlers otherwise unchanged.
- `app/test_app.py`: 15 regression and control tests, with additional parameterized subtests.
- `evidence/app-before.py`: exact source snapshot taken before fixes.
- `evidence/fix.diff`: unified source diff against that snapshot.
- `evidence/before-tests.txt`: final pre-fix run showing six failed assertions across five tests, including both bare-identity endpoints.
- `evidence/after-tests.txt`: final post-fix run, all 15 tests passing and Python exit status 0.
- `evidence/run_tests.py`: repeatable runner that captures unittest output directly, avoiding PowerShell's stderr presentation behavior.

## Tests actually executed

1. `python -m unittest discover -s app -p test_app.py -v` on original source: 15 tests; five failures. The initial authentication test stopped at its first assertion.
2. The same command on original source after making both authentication checks subtests: 15 tests; six failed assertions across five tests. This is the retained pre-fix log.
3. The same command after fixes: 15 tests; all passed. PowerShell rendered unittest stderr as a native-command error and the shell wrapper reported status 1 even though unittest printed OK.
4. `python evidence/run_tests.py`: the same 15 tests passed, with output written directly to `evidence/after-tests.txt`; process exit status 0 confirmed.

## Protected controls and workflows

Tests verify successful owner reads and live same-tenant shared reads; denial of unshared reads by members, cross-tenant users, and administrators; recipient inability to reshare or revoke; owner revocation ending recipient access while preserving owner access; and rejection of cross-tenant/unknown recipients and past expiries without creating shares.

They also verify that migrated owners cannot create or revoke shares, members cannot list administrator inventory, administrator inventory follows the administrator's current tenant (north a/b, then south c), unknown/missing credentials are rejected, and missing documents/share IDs retain 404 responses. Existing read denials retain 404 rather than revealing authorization details through a new response code.

## Coverage, uncertainty, and limitations

All four explicit application routes and the authentication, document lookup, and read authorization helpers were inspected. Bounded tests cover the documented access-rule branches, positive workflows, migration, expiry, revocation, and inventory isolation. No claim of exhaustive security coverage or measured line coverage is made.

This was an in-process assessment, without a deployed server, proxy, browser, concurrency/load testing, extensive malformed-input fuzzing, or production directory integration. HTTP header parsing beyond the exercised forms, non-finite numeric inputs, race conditions, operational configuration, and deployment behavior remain unverified. These limitations are not confirmed findings.

Fake bearer tokens, in-memory state, absent deployment configuration, and direct state edits authorized by the README are fixture conditions, not reported vulnerabilities. No external access or ability for an ordinary API caller to perform identity migration was demonstrated or assumed.
