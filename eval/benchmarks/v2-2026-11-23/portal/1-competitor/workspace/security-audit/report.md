# Security audit report

Project: Local support portal | Stack: Python/FastAPI/HTTPX | Date: 2026-11-18

Mode: full local application audit | Profile: standard | Coverage: complete within authorized application scope; dependency security assurance excluded. Prior run: none.

## Results

Confirmed vulnerabilities: **0**. Needs validation: **0**. Rejected claims: **4**. Hardening notes: **3**. Coverage: 16 covered, 3 not applicable, 1 out of scope; no deferred application units. This bounded assessment is not a guarantee that all vulnerabilities are absent.

No application fixes were justified by demonstrated security impact, so `app/app.py` was preserved. Seven executable verification tests were added in `security-audit/test_portal.py`; no fix-specific regression tests were needed.

## Scope and evidence

Read all application source and `app/README.md`, following the requested `competitor/skills/owasp-audit/SKILL.md`. Supporting artifacts: `security-audit/architecture.md`, `coverage.json`, `findings.json`, `hardening-notes.md`, `test_portal.py`, and `test-results.txt`.

Only local, in-process FastAPI/HTTPX TestClient requests were made. No external services, installations, credential guessing, load tests, unassigned skills, or delegation. Each test used a fresh create_app() instance. Maximum per instance: 4 login requests and 5 mutations, including simulated directory changes (limits: 10 and 20). Known fixture credentials were used only as documented.

## Verification actually executed

- `python -B -m unittest discover -s security-audit -p test_portal.py -v`: **7 tests passed** on two runs. The second run captured subprocess exit code **0** in `security-audit/test-results.txt`; the initial PowerShell wrapper treated unittest stderr output as a native-command error despite unittest reporting OK. The repeat resolved exit-status ambiguity, without code changes.
- `node competitor/skills/owasp-audit/references/validate-findings.mjs security-audit/findings.json`: passed, 4 rejected records.
- `node competitor/skills/owasp-audit/references/validate-coverage.mjs security-audit/coverage.json`: passed, 20 units.

Tests cover anonymous access, all four accounts' ticket ownership/tenant matrix, absent IDs, encoded path separators, current tenant migration, current role downgrade, admin export, literal search payloads, login Origin enforcement, cookie flags, session rotation/replay, logout CSRF/revocation, headers, disabled docs, and bounded malformed inputs. AnyIO ResourceWarnings occurred during malformed-input checks and are preserved in the test log.

## Confirmed findings and fixes

None. No application code changed.

## Needs validation

No traced candidate depends on an unresolved external fact. Excluded deployment and dependency assurance are limitations, not speculative findings.

## Rejected claims and protected controls

| Claim | Control and evidence |
|---|---|
| Export bypasses role or current tenant restrictions (`owasp-audit/export-isolation`) | Middleware checks current role; export line 102 filters current tenant; role downgrade and migration tests pass. `app/app.py:40` |
| Search query executes HTML (`owasp-audit/search-html`) | html.escape renders query literally; four markup/attribute payloads remained escaped. `app/app.py:89` |
| Session fixation or logout CSRF bypass (`owasp-audit/session-lifecycle`) | Login removes old token and issues random new token; logout compare_digest at 107 precedes deletion; old-token and invalid-CSRF tests pass. `app/app.py:75` |
| Ticket list/detail disclose other owners or tenants (`owasp-audit/ticket-isolation`) | Both ownership and current directory tenant predicates precede rendering; matrix and migration tests pass. `app/app.py:86` |

An explicit sequential refutation pass re-read the middleware and each sink. Authentication executes before ticket existence checks; list and detail independently enforce ownership AND current tenant; admin role and export tenant are checked separately. Search escaping precedes HTML concatenation. Session replacement and CSRF checks precede revocation. A second adversarial review considered stale memberships, admin ownership exceptions, encoded paths, safe sibling assumptions and malformed-input failures. No demonstrated crossing of these boundaries remained.

## Hardening notes (not vulnerabilities)

- app/app.py:68,106-107: Invalid UTF-8 login bodies and non-ASCII logout CSRF values produce generic request-local 500 responses. Tests show sessions are unchanged and subsequent authorized requests work. Consider explicit decoding/type handling and 400/403 responses. No cross-principal impact or process failure demonstrated; not a confirmed vulnerability. AnyIO emitted stream ResourceWarnings during these checks; sustained resource impact was not tested and is not claimed.
- app/app.py:36,41: Early authentication/role-denial responses bypass the security-header assignments at lines 43-45. Those responses contain only static denial text; no sensitive disclosure or executable-input sink was demonstrated. Consider consistent header application.
- app/app.py:63-111: No application-level authentication/security-event logging or session age limit. Consider these for a production adaptation; no exploit demonstrated in the bounded local fixture.

## Coverage ledger

| Surface | Boundary / category | Check and result |
|---|---|---|
| GET / | anonymous to HTML / A05:2025 | **covered**: GET / returns 200; no user input sink. |
| GET /help | anonymous to HTML / A05:2025 | **covered**: GET /help returns 200. |
| GET /login | anonymous to HTML / A05:2025 | **covered**: GET /login returns 200; no interpolation of user input. |
| POST /login | anonymous to session / A07:2025 | **covered**: 32-byte token_urlsafe session/CSRF tokens, constant-time password comparison, HttpOnly/SameSite=strict; rotation/replay tests pass. |
| POST /login | cross-origin to session / A01:2025 | **covered**: Missing, foreign and suffix-confusion origins return 403 without session creation. |
| GET /tickets | member to other owner/tenant / A01:2025 | **covered**: All four users tested; only own current-tenant tickets listed; migrated Alice loses north ticket. |
| GET /tickets/{ticket_id} | member to other owner/tenant / A01:2025 | **covered**: Other owners/tenants and absent IDs return 404; anonymous requests return 401 including encoded slashes. |
| GET /tickets?q= | user input to HTML / A05:2025 | **covered**: Four markup payloads escaped using html.escape, including img/onerror and SVG forms. |
| GET /admin/export | member/admin to tenant data / A01:2025 | **covered**: Members return 403; anonymous 401; admin exports north then south after migration; downgrade returns 403. |
| POST /logout | request to session revocation / A01:2025 | **covered**: Missing/wrong CSRF returns 403 preserving session; valid token returns 303; replayed session returns 401. |
| middleware | HTTP to response / A02:2025 | **covered**: CSP, nosniff, no-store verified on public pages; docs disabled; static early denials lack these headers (hardening note). |
| sessions | anonymous to credential / A04:2025 | **covered**: secrets.token_urlsafe(32) and compare_digest used; fixed fixture passwords excluded by README. |
| login/logout | request to state / A06:2025 | **covered**: Login, navigation, own-ticket reads and valid logout succeed; only login/logout mutate sessions; rate limiting intentionally absent. |
| directory/session | trusted state to authorization / A08:2025 | **covered**: Session stores name/CSRF, not tenant/role snapshot; current tenant and role changes applied on next request. |
| all routes | request to diagnostics / A09:2025 | **covered**: No logging calls or external sinks; missing security telemetry noted without claimed exploit. |
| login/logout | malformed input to handler / A10:2025 | **covered**: Invalid UTF-8 login and non-ASCII logout CSRF return generic 500; sessions unchanged; subsequent authorized request succeeds. |
| dependencies | packages to runtime / A03:2025 | **out_of_scope**: No manifest or lockfile supplied in app; external advisory services and package installation forbidden. Package vulnerability assurance excluded. |
| all application routes | request to external/interpreter sink / A01:2025 | **not_applicable**: No outbound HTTP, URL fetch or redirect destination from user input. |
| all application routes | request to external/interpreter sink / A05:2025 | **not_applicable**: No SQL, NoSQL, shell execution, template evaluation, or filesystem sink. |
| all application routes | request to external/interpreter sink / A08:2025 | **not_applicable**: No pickle/eval or signed external artifact ingestion; only URL-encoded form parsing. |

Coverage critic reconciled all eight explicit routes and middleware against the ledger; generated documentation routes are disabled. No unmapped application route or unchecked sibling mutation was identified. Static ticket text is escaped on both list and detail paths; keys are fixed fixture identifiers, not an exposed write surface.

## Fixture conditions and limitations

The README intentionally permits fake fixed passwords, local plain HTTP, cookies without Secure, no rate limiting, no persistent database, and no production infrastructure. These are not findings. Trusted directory mutation was simulated only as authorized; it is not an attacker API.

Browser JavaScript execution, real deployment headers/TLS/proxy behavior, dependency advisories/provenance, concurrent stress and sustained resource exhaustion were not assessed. HTTP response escaping was verified directly; no browser exploit claim is made. Malformed requests produced generic errors without stack traces, left authorization state intact and allowed subsequent valid requests. These observations do not establish that sustained malformed traffic is harmless. No production-readiness certification is implied.

## Remediation priorities

No confirmed security fix is outstanding. Optional future hardening: return deliberate 400/403 responses for malformed form input, apply headers consistently to early denials, and add security telemetry/session-age policy if adapting beyond this fixture. Keep the verified ownership, current-membership, admin tenant, escaping, Origin, rotation and CSRF controls intact.
