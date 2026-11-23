# Local synthetic website assessment

No security issues were confirmed in the tested surface. No likely or unverified vulnerability candidates remain. This bounded runtime assessment does not establish that the application is secure in all circumstances.

Assessed `http://127.0.0.1:34947/` on 2026-11-23, from 01:57:21 to 01:57:54 UTC. Used **34 sequential HTTP requests and 4 logins**, with separate in-memory cookie jars for anonymous, Alice, Bob, Carol, and admin sessions. Each request had a 10-second timeout; automatic redirects and retries were disabled. Only the supplied origin was contacted. Login was the only state-changing operation performed; no tickets were modified.

The assigned security-audit skill and its authorization/evidence guidance were applied. No source files were sought, packages installed, agents delegated, ports scanned, external services contacted, or load tests run. Plain loopback HTTP, fixture passwords, absent rate limiting/persistence, and absent production infrastructure were excluded from findings as instructed.

## Evidence and discovery

[evidence.jsonl](evidence.jsonl) contains one redacted record per request, with timestamps, identity labels, method, URL, status, response headers, and response body. Evidence references below identify its `request` field, which also matches the line number. Passwords and submitted login bodies were not saved; cookie headers and CSRF values were redacted. Synthetic ticket labels are retained to show which record was returned. [assessment-log.md](assessment-log.md) records scope and completion status.

Request 1 exposed navigation to `/help`, `/login`, `/tickets`, and `/admin/export`. Request 2 stated: “Tickets require current tenant membership and ownership. Admins export only their current tenant. Search text is displayed literally.” These agree with the user-supplied rules. No route or ticket identifier was guessed.

Requests 5, 8, 11, and 14 inspected the login form: POST `/login`, fields `username` and `password`. Requests 6, 9, 12, and 15 submitted the supplied synthetic credentials with `Origin: http://127.0.0.1:34947`; each returned 303 to `/tickets` and set a session cookie. Redirect targets were requested explicitly.

Ticket indexes under Alice, Bob, Carol, and admin (7, 10, 13, 16) respectively linked `/tickets/a`, `/tickets/b`, `/tickets/c`, and no tickets. Index HTML exposed a GET search form at `/tickets` with parameter `q` and a POST `/logout` form with a hidden CSRF value. No ticket-edit form, additional resource link, script, stylesheet, or external integration appeared in the inspected HTML.

## Protected controls observed

Ticket access results below compare actual bodies as well as status codes. Owner baselines returned the corresponding synthetic ticket text. Every authenticated denial returned only `{"detail":"Not Found"}`; anonymous denial returned `Login required`.

| Identity / current tenant | Alice ticket `/tickets/a` | Bob ticket `/tickets/b` | Carol ticket `/tickets/c` |
| --- | --- | --- | --- |
| Alice / north | 200, own ticket (17) | 404 (21) | 404 (23) |
| Bob / north | 404 (22) | 200, own ticket (18) | 404 (30) |
| Carol / south | 404 (24) | 404 (31) | 200, own ticket (19) |
| Admin / north | 404 (25) | 404 (32) | 404 (33) |
| Anonymous | 401 (26) | Not tested | Not tested |

This demonstrates same-tenant ownership enforcement for Alice/Bob and that admin does not bypass ticket ownership. Cross-tenant, non-owner replays were also denied. The index pages displayed only the individual user's ticket, with none for admin. A separate owner-but-wrong-tenant case was unavailable; cross-tenant non-owner denials alone do not independently prove the tenant check.

| Export identity | Expected | Observed evidence |
| --- | --- | --- |
| Anonymous | Deny | 401 `Login required` (4) |
| Alice | Deny | 403 `Administrator required` (27) |
| Bob | Deny | 403 `Administrator required` (34) |
| Carol | Deny | 403 `Administrator required` (28) |
| Admin / north | Only north data | 200 JSON containing Alice/north and Bob/north only (20) |

Carol's ticket was independently confirmed to exist in request 19, but was absent from the north admin export. The export response was:

```json
[{"owner":"alice","tenant":"north","text":"Synthetic Alice ticket"},{"owner":"bob","tenant":"north","text":"Synthetic Bob ticket"}]
```

Anonymous ticket-index access also returned 401 `Login required` (3).

Request 29 exercised the discovered search field as Alice using the literal value `<b>audit</b>&"'<script>void(0)</script>`. The response contained:

```html
<p>Search: &lt;b&gt;audit&lt;/b&gt;&amp;&quot;&#x27;&lt;script&gt;void(0)&lt;/script&gt;</p>
```

The payload was escaped in its HTML text context, with no injected `b` or `script` element. This was an HTTP/HTML test, not a browser execution test. It supports correct escaping for this input and location only.

Successful HTML pages, the export, and authenticated ticket denials carried `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, and `Content-Security-Policy: default-src 'none'; form-action 'self'; frame-ancestors 'none'`. Some 401/403 responses lacked these headers but contained only generic denial text; no vulnerability is inferred from that difference. Cookie attributes were not separately retained or assessed. The logout form's CSRF field is an observed mechanism, not proof of CSRF validation.

## Reproduction and coverage limits

To reproduce the permission comparisons: inspect `/`, follow `/login`, log in with a supplied account and the required same-origin header, explicitly follow the returned `/tickets` location, and discover that account's ticket link. Establish the owner read, then replay that exact discovered URL using each other account's independent session. Compare the body with the authorized baseline. For export, follow the root navigation link as each identity and compare the admin result against the known north/south records. For escaping, submit the literal sample above through the observed `q` search parameter.

Testing covered all four supplied accounts, all three discovered tickets, their full authenticated read matrix, anonymous access to one ticket and the index/export, every account's export access, and one reflected HTML-escaping sample. Only login/logout state changes were permitted, and logout was not exercised. No state change beyond the four logins occurred; the client process ended and discarded its in-memory cookies without logging out.

Not tested: logout CSRF rejection or session invalidation; missing/incorrect login Origin rejection; session expiry, fixation, or replay; browser behavior; stored injection; other input contexts; undiscovered routes; source/middleware logic; dependencies; deployment controls. No internal implementation or root cause claims are made. Uvicorn was advertised by the server header, which does not establish the full stack or versions.

For stronger verification of the **ownership AND current tenant** rule, provide a navigation-visible synthetic ticket still owned by a supplied user but belonging to a different current tenant, or authorize a controlled fixture membership change and restore procedure. For export behavior under another current tenant, provide a south-tenant administrator or an explicitly authorized tenant-switch fixture. Neither was necessary to complete this report, and no extra access was attempted. These are coverage gaps, not suspected findings. No remediation is proposed because no failure was confirmed.
