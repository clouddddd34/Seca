# Local application security assessment

Two confirmed authorization findings were fixed and retested. Ten regression and control tests pass. Assessment date: 2026-11-18. This is a bounded local assessment, not a comprehensive pentest or a production security assurance.

## Scope and method

Applied `assigned-skill/SKILL.md` and its access-rules and evidence references. Requirements come from `app/README.md`. Inspected the complete `app/app.py` implementation: FastAPI routes, fixture identity resolution, Pydantic share input, in-memory documents/users/shares, and authorization checks. Tested only in-process FastAPI/HTTPX TestClient instances. No external services, package installation, delegation, scanners, or other skills were used.

Each test uses fresh synthetic state and closes its client. Each instance creates at most one share and performs at most two state changes, counting directory migrations and expiry setup. State is discarded with the instance. The separate baseline reproduction also uses fresh instances within these bounds. No credentials or response bodies are saved in assessment logs; evidence records only status and document-equality checks.

## Confirmed findings

### F-001 — Document reads survive tenant migration

**Confirmed; medium severity; high confidence; fixed and retested.** An existing owner or live-share recipient can retain access after the trusted directory moves them out of the document's tenant. The documented rule requires current membership AND ownership or a live share. Originally `can_read` granted owners access immediately and matched recipients without consulting current membership. The read route had no compensating check and returned the full document, including text.

Bounded reproduction: on a fresh instance, Alice can read document a; migrate Alice to south through the documented state setup; repeat the read. Separately, create a future share from Alice to Bob, verify Bob's legitimate read, migrate Bob to south, and repeat. Both unauthorized reads returned 200 with the exact expected document and text. This demonstrates cross-tenant confidentiality loss after membership removal, not an ability to perform directory migration through the API.

Evidence: `evidence/app-before.py` (`can_read` and `read`), `evidence/runtime-before.json`, `evidence/verify_baseline.py`, and the owner/recipient migration failures in `evidence/tests-before.txt`. Structured record: `evidence/F-001.json`.

Fix: `app/app.py` now rejects a tenant mismatch before considering ownership or shares. Tests `test_owner_migration_blocks_read` and `test_recipient_migration_blocks_read` in `app/test_security.py` now pass with 404 after migration while their legitimate baseline reads succeed.

### F-002 — Expired shares continue granting reads

**Confirmed; medium severity; high confidence; fixed and retested.** A recipient with an unrevoked but expired share could continue reading. Creation validated future expiry, but the subsequent read predicate checked only the document, recipient, and revocation flag. No other read-path control enforced expiry.

Bounded reproduction: Alice creates a future share of a for Bob; verify the persisted share and Bob's legitimate read; change its stored expiry to a past Unix timestamp as authorized by the README; read as Bob. The response was 200 and contained the exact document and text. Impact is continued confidential access beyond the authorized period; arbitrary unshared-document access was not demonstrated.

Evidence: `evidence/app-before.py`, `evidence/runtime-before.json`, `evidence/verify_baseline.py`, and `test_expired_share_blocks_read` in `evidence/tests-before.txt`. Structured record: `evidence/F-002.json`.

Fix: the read predicate now requires `expires_at > time()` as well as an unrevoked matching share. `test_expired_share_blocks_read` now passes: the future share works and the expired share returns 404.

## Verification actually executed

1. `python -m unittest discover -s app -p test_security.py -v` against the original application: 10 tests, three failures (owner migration, recipient migration, expiry), seven passes. Output: `evidence/tests-before.txt`.
2. `python evidence/verify_baseline.py`: three fresh-instance reproductions against the preserved original source, confirming full document equality rather than relying on status alone. Output: `evidence/runtime-before.json`.
3. The same ten-test suite against the patch: all passed. PowerShell's initial stderr pipeline wrapper reported an error despite unittest's `OK`; the run was repeated through `python evidence/finalize.py` to capture the actual Python exit code. Final evidence: `evidence/tests-after.txt`, 10 tests passed, Python exit code 0. The wrapper invokes the same unittest command and records finding/log artifacts.

Observed installed versions: FastAPI 0.115.6, Starlette 0.41.3, HTTPX 0.26.0, Pydantic 2.13.4. Original source is preserved at `evidence/app-before.py`; patched source is `app/app.py`. Continuity log: `audit.json`.

## Protected controls and coverage

| Workflow / boundary | Verified result |
| --- | --- |
| Current owner reads own document | Allowed, including after share revocation |
| Same-tenant recipient with future live share | Allowed; creation state matches response |
| Other same-tenant member, cross-tenant member, or admin without share | Document read denied |
| Missing document | 404 |
| Missing or unknown fixture identity on all four routes | 401; no share created |
| Recipient attempts to reshare or revoke | 403; share state unchanged |
| Owner shares to cross-tenant/unknown recipient or with past expiry | 422; no persisted share |
| Migrated owner attempts share or revoke | 403; share state unchanged |
| Owner revokes share | Persisted revoked flag; recipient subsequently denied |
| Member attempts admin inventory | 403 |
| Admin inventory before and after directory migration | Exact current-tenant document sets only |

The patch changes only `can_read`; existing creation, revocation, inventory, identity, and denial-response behavior is retained. Tests inspect state separately after successful or denied mutations. No new API or dependency was introduced.

## Uncertainty, fixture conditions, and limitations

No additional likely or unverified vulnerability is asserted. Synthetic bearer tokens, permissive fixture identity parsing, in-memory storage, and absent deployment configuration are fixture conditions, not production findings. The demonstrated migration and expiry state changes are explicitly authorized setup operations, not attacker-facing API capabilities.

Authorization review covers all four business routes, both ownership and share access, and the documented tenant/lifecycle boundaries. It does not cover production authentication, transport, browser behavior, persistent storage, concurrency, load, or external integrations. Missing middleware or headers alone was not treated as a vulnerability. Input validation was inspected and representative invalid recipients/expiry values tested; exhaustive malformed input and non-finite timestamp cases were not exercised. Exact equality at the expiry instant is enforced by the strict comparison in source but was not separately clock-mocked.

External advisory lookup was prohibited, so installed version evidence is not a dependency vulnerability assessment. No external ASVS/WSTG guidance was fetched or versioned control compliance claimed. The optional seca helper was not used; JSON finding records organize evidence and do not independently validate its truth. Severity reflects limited demonstrated confidentiality impact with prior-access preconditions; no production exposure or numerical CVSS score is claimed.
