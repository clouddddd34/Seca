# Local application security assessment

Assessed 2026-11-18 using the assigned security-audit skill. Two vulnerabilities were confirmed and fixed in `app/app.py`; all eight regression/control tests pass. This is a bounded local assessment, not a comprehensive pentest or a statement that the application is secure.

## Scope and evidence

Authority and expected behavior: `app/README.md`. Reviewed the complete `app/app.py`, including identity resolution, document lookup, read authorization, share creation/revocation and administrator inventory. Runtime verification used installed FastAPI/HTTPX TestClient with fresh synthetic instances. No external services, installs, other skills, delegation or scanner runs were used. Optional seca was not needed.

The exact pre-fix application is preserved in `evidence/app.before.py`. Reproducible probes are in `evidence/reproduce.py`; tests are in `tests/test_access.py`. Before/after observations are in `evidence/reproduction-before.json` and `evidence/reproduction-after.json`. These record status and equality with the expected synthetic document without saving credentials or response bodies. Structured findings are `evidence/F-001.json`, `evidence/F-002.json` and `audit.json`; continuity notes are in `assessment-log.md`.

Installed versions observed: FastAPI 0.115.6, Starlette 0.41.3, HTTPX 0.26.0, Pydantic 2.13.4. No advisory lookup was performed because external access was excluded; no dependency vulnerability claim is made.

## Confirmed findings

### F-001: Reads ignore current tenant membership — high severity

Confidence: confirmed by local runtime reproduction and complete source trace. Preconditions: an authenticated owner or live-share recipient is migrated by the trusted directory away from the document tenant. This migration is authorized fixture setup, not an exposed API vulnerability.

Expected: membership in the document's current tenant AND ownership or a live share. Observed: both migrated owners and recipients continued to receive HTTP 200 with the full document. `actor` resolves current user state, but original `can_read` (`evidence/app.before.py:40-45`) ignores the supplied user and permits ownership or an unrevoked share. The read endpoint returns the document after that predicate; no intervening tenant check exists.

Bounded reproduction: for the owner, read a as Alice, change Alice's tenant to south, then read a again. For the recipient, Alice creates one future share of a to Bob; verify it exists in state and Bob can read; change Bob's tenant to south and repeat. Both before-fix probes returned the complete north document after migration. See the owner_migration and recipient_migration records in `evidence/reproduction-before.json` and the corresponding failing tests in `evidence/tests-before.txt`.

Impact: cross-tenant disclosure of documents previously owned or shared. High severity reflects failure of the tenant boundary, conditional on migration and a prior relationship; arbitrary unrelated document access or new write rights were not demonstrated.

Fix applied: reject tenant mismatch before ownership/share evaluation in `app/app.py`'s `can_read`. Retested: both migrated identities receive 404 and no document, while legitimate baselines remain 200 (`evidence/reproduction-after.json`). Regression tests: `test_owner_migration_removes_read_access` and `test_recipient_migration_removes_read_access`.

### F-002: Expired shares still authorize reads — medium severity

Confidence: confirmed by local runtime reproduction and source trace. Preconditions: a same-tenant recipient has an expired, unrevoked share that was originally valid.

Expected: share access ends at expires_at. Observed: original `can_read` checks recipient/document/revocation but omits expiry. Creation rejects past expiry, but this cannot protect reads after a valid share expires.

Bounded reproduction: Alice creates one future share of a to Bob; inspect persisted state and verify Bob's read; set that share's expiry to a past Unix timestamp as authorized by the README; read again. HTTP 200 still included the complete document. See expiry in `evidence/reproduction-before.json` and `test_expired_share_removes_read_access` in `evidence/tests-before.txt`.

Impact: confidentiality exposure beyond the owner-selected sharing window. This requires a prior valid share; it does not establish access to arbitrary documents.

Fix applied: require `time() < expires_at` in the share read predicate alongside the existing revocation check. Retested expired access returns 404 and no document; valid owner/live-share reads pass. Evidence: `evidence/reproduction-after.json`, `evidence/tests-after.txt`.

## Tests actually executed

From workspace root, before and after the patch:

- `python -m unittest discover -s tests -v`: before, eight tests ran with three expected authorization failures (owner migration, recipient migration, expiry); five controls passed. After, all eight passed. Captured output: `evidence/tests-before.txt`, `evidence/tests-after.txt`.
- `python evidence/reproduce.py`: three fresh instances per run; all legitimate baseline reads returned 200. Before patch, all three unauthorized follow-up reads returned 200 with document equality true. After patch, all returned 404 with document equality false.

PowerShell decorates unittest stderr as NativeCommandError in captured logs; unittest's actual summaries are FAILED (failures=3) before and OK after, not an interpreter failure.

Every instance used at most one share and three state changes (including direct fixture changes); denied mutations were checked against persisted state. No instance approached the ten-share/ten-change limit. State was discarded with each instance.

## Protected controls and coverage

| Workflow / identity | Expected and verified |
| --- | --- |
| Current owner | Reads own document, including after a share expires or is revoked |
| Same-tenant recipient with live share | Reads shared document |
| Unshared same-tenant member, other tenant, admin without ownership/share | Document read denied |
| Migrated owner / recipient | Read denied after fix |
| Expired or revoked share | Read denied; expiry fixed, revocation retained |
| Owner sharing to current same-tenant member | Creation succeeds and persisted share is inspected |
| Cross-tenant / unknown recipient or past expiry | Creation denied without persisted shares |
| Recipient attempting reshare or revoke | Denied; share count and revoked state unchanged |
| Migrated owner attempting share/revoke | Denied; persisted state unchanged |
| Current owner revoking share | Succeeds, state becomes revoked, recipient read denied |
| Missing/unknown fixture identity | All four endpoints deny requests |
| Members requesting inventory | Denied |
| Administrator inventory | North documents only; after trusted migration, south documents only |
| Unknown document | 404 |

Only the shared read predicate changed; sharing, ownership, revocation and inventory checks remain intact. No authorization rules were loosened.

## Uncertainty, fixture conditions and limitations

No unresolved likely/unverified finding is asserted from this review. Fake bearer credentials, permissive fixture identity parsing, in-memory storage, direct trusted-directory/expiry mutation and missing deployment configuration are treated as fixture conditions, not production findings. Tests exercise the documented bearer flow; they do not validate production authentication.

Coverage does not include deployed transport, browser security/CSRF, real identity infrastructure, dependency advisory matching, concurrency, load, exhaustive malformed/non-finite input validation, or an exact clock-boundary runtime test. The strict before-expiry comparison is source-verified. No external OWASP materials were fetched and no versioned ASVS/WSTG control identifiers are claimed. These limits constrain conclusions; passing local tests is not evidence of comprehensive security.
