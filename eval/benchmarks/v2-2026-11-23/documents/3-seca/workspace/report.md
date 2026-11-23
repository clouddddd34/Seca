# Local application security assessment

Two confirmed authorization findings were fixed and retested. Before remediation, 3 of 12 regression/control tests failed; after remediation, all 12 passed. Bounded probes separately confirmed actual document disclosure before the fix and denial afterward.

## Scope and evidence

Assessment date: 2026-11-23. Applied `assigned-skill/SKILL.md` and its access-rules/evidence references. Requirements came from `app/README.md`. Reviewed the entire `app/app.py`: FastAPI routes, Pydantic share input, fixture identity resolution, document lookup, read authorization, share creation, revocation, inventory filtering, and state initialization. No external services, package installation, delegation, or other skills were used.

Original source is preserved at [evidence/app-before.py](evidence/app-before.py); fixes are in [app/app.py](app/app.py), function `can_read`. Tests are in [app/test_security.py](app/test_security.py). Each test/probe uses a fresh instance with at most one share and three state changes, including authorized setup changes. No raw credentials or document response bodies are recorded in test/probe output; source fixtures and test code contain the supplied synthetic authentication values.

Installed versions observed: FastAPI 0.115.6, HTTPX 0.26.0, Starlette 0.41.3, Pydantic 2.13.4. No current advisory lookup was performed because external access was excluded; these versions alone are not vulnerability findings.

## Confirmed findings

### F-001 — Document reads ignore current tenant membership

**Confirmed; high severity; high confidence.** Requires an authenticated previous owner or live-share recipient whose directory membership moves away from the document tenant. The trusted migration operation itself is authorized setup, not an attacker capability.

Expected: current membership in the document tenant AND ownership or a live share. Observed: both migrated owners and migrated recipients received HTTP 200 with the complete synthetic document. The path is `read -> actor -> document -> can_read`; `actor` retrieves current user state, but the original `can_read` ignored it. Ownership returned immediately and share matching lacked a tenant gate. No middleware or upstream check supplied that gate.

Reproduction: on a fresh instance, read Alice's document as Alice; change Alice's current tenant to south; read again. Independently, create a future Alice-to-Bob share, verify Bob can read, migrate Bob to south, and repeat the read. [evidence/probe-before.txt](evidence/probe-before.txt) records 200 and document-body equality for both cases. [evidence/tests-before.txt](evidence/tests-before.txt) records failures in `test_migrated_owner_denied` and `test_migrated_recipient_denied`.

Impact: confidentiality breach across the current tenant boundary for documents previously owned or shared. Arbitrary document enumeration, writes, and privilege elevation were not demonstrated.

Fix applied: reject mismatched current tenant before evaluating ownership or shares. Both probes now return 404 without the document, and both regression tests pass. Existing same-tenant owner and recipient reads remain allowed.

### F-002 — Expired shares continue authorizing reads

**Confirmed; medium severity; high confidence.** Requires an authenticated same-tenant recipient of a previously valid, unrevoked share that has expired.

Expected: a share authorizes reads only strictly before `expires_at`. Observed: after moving the stored share expiry into the past, Bob still received HTTP 200 with Alice's document. Creation validates a future expiry, but the original read predicate only checked document, recipient, and revocation; it never reevaluated expiry.

Reproduction: create a future Alice-to-Bob share, inspect the persisted share, verify Bob's successful read, set that share's expiry to a past Unix timestamp as authorized by the README, then repeat the read. [evidence/probe-before.txt](evidence/probe-before.txt) records document-body equality after expiry; `test_expired_share_denied` fails in [evidence/tests-before.txt](evidence/tests-before.txt).

Impact: loss of time-limited document confidentiality for existing recipients. No ability to create an unauthorized share was demonstrated.

Fix applied: require `expires_at > time()` alongside the existing non-revoked check. The expiry probe now returns 404 and its regression test passes. Future shares still authorize reads; owners remain independent of share expiry.

## Verification actually executed

Commands executed from the workspace root, once before and once after the patch:

```text
python -m unittest discover -s app -p test_security.py -v
python evidence/probe.py
```

Output was captured with PowerShell `Tee-Object`. Before: 12 tests, 3 failures (exit 1). After: 12 tests, all passed; probe execution succeeded. PowerShell annotates unittest's stderr as `NativeCommandError` in captured text even for successful runs; the unittest summary is `OK` after the fix. Evidence: [tests-before](evidence/tests-before.txt), [tests-after](evidence/tests-after.txt), [probe-before](evidence/probe-before.txt), [probe-after](evidence/probe-after.txt). Probe implementation: [evidence/probe.py](evidence/probe.py).

State-changing tests inspect `app.state.shares` separately from creation/deletion responses: valid shares persist, revocation marks the stored record, and denied changes leave share count/revocation unchanged. Positive reads compare the returned object with the synthetic stored document. The probes compare bodies without printing them.

## Protected controls and coverage

All rules below are documented in `app/README.md`; identity rejection is additionally derived from source. These are local observed controls, not assurances about a deployment.

| Actor/relationship | Action | Expected and retested result |
| --- | --- | --- |
| Current-tenant owner (Alice or Carol) | Read own document | Allow |
| Same-tenant user without share; other-tenant user; admin without ownership/share | Read Alice's document | Deny |
| Current-tenant live recipient | Read | Allow |
| Migrated owner or recipient | Read old tenant's document | Deny after fix |
| Expired or revoked recipient | Read | Deny; expiry fixed, revocation preserved |
| Current owner | Create valid same-tenant share; revoke | Allow; persisted state checked |
| Recipient | Reshare or revoke | Deny; state unchanged |
| Owner targeting unknown/other-tenant user or past expiry | Create share | Deny; no persisted share |
| Migrated owner | Create share or revoke | Deny; state unchanged |
| Member | List inventory | Deny |
| Admin, before and after trusted migration | List inventory | Only current tenant's documents |
| Missing or unknown identity | All four endpoints | Deny |

Only `can_read` production behavior changed. Owner-only share/revoke checks, recipient tenant validation, creation expiry validation, revocation enforcement, administrator role checks, inventory tenant filtering, and denied-read 404 semantics were preserved.

## Uncertainty and limitations

No unresolved likely or unverified vulnerability candidates remain from these checks. This is a bounded source and local runtime assessment, not a comprehensive pentest or a declaration that the application is secure. Exact equality at expiry follows the strict comparison in source; runtime tests used a clearly past timestamp. Concurrent state changes, broad malformed-input fuzzing, load, multiple-share combinations, and deployed infrastructure were not tested. No advisory scanner or optional seca helper was run, and no versioned ASVS/WSTG control IDs are claimed because external guidance was not fetched.

Fixture bearer identities (including the intentionally simple parser), in-memory state, and absent deployment configuration are fixture conditions, not reported production vulnerabilities. Trusted directory migration and direct expiry manipulation were only authorized setup operations. There is no evidence here of an attacker being able to perform them through this API. See [audit.json](audit.json) for the completed assessment log.
