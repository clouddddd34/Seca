# Local support portal assessment

Assessed `http://127.0.0.1:10240/` on 2026-11-23, approximately 02:05–02:06 UTC, using the assigned security-audit skill. **No confirmed security findings** were observed in the bounded tests. No likely findings are asserted. This is a limited HTTP assessment, not a comprehensive security certification.

## Scope and method

Executed **39 sequential HTTP requests**, including **five login attempts (four successful)**, with isolated in-memory cookie jars, 10-second timeouts, no retries, and no automatic redirect following. Inspected navigation, returned HTML, login/search/logout forms, ticket access, export authorization, and selected session controls. All paths came from navigation or forms; ticket identifiers came from each account's ticket list. Only login/logout changed application state; no tickets were altered.

No application source, files outside the workspace, external services, guessed routes or credentials, package installs, delegation, port scans, or load tests were used. Plain loopback HTTP, fixed fixture passwords, absent rate limiting/persistence, and absent production infrastructure are intentional and are not findings.

The redacted [request/response evidence](evidence.txt) records R01–R39, identities, methods, paths, statuses, headers, and response bodies. Passwords, cookie values, and CSRF values were not persisted. POST input details needed to interpret that evidence are documented below. The [assessment log](assessment-log.json) records coverage and unresolved checks. Application internals and deployed revision are unknown; the server reported `uvicorn`, which does not establish its dependency version.

## Confirmed findings

None. No unauthorized ticket content or cross-tenant export content was returned in the tested cases. No remediation was applied or retested.

## Expected rules and observed controls

The user specified that tickets require **both ownership and current tenant membership**, and that only admin may export, limited to its current tenant. `/help` independently stated those rules (R02). Alice, Bob, and admin belong to north; Carol belongs to south. Admin status does not waive ticket ownership.

| Test / expected result | Actual evidence | Conclusion within tested scope |
| --- | --- | --- |
| Anonymous private access denied | R04 `/tickets`, R05 `/admin/export`, R25 `/tickets/a`: 401 `Login required` | Authentication enforced on tested private routes |
| Each user sees their own ticket navigation | R07 Alice links `/tickets/a`; R09 Bob links `/tickets/b`; R11 Carol links `/tickets/c`; R13 admin has empty list | No other user's tickets appeared in these lists |
| Own ticket in current tenant allowed | R14 Alice/a, R15 Bob/b, R16 Carol/c: 200, corresponding synthetic ticket text | Legitimate positive controls succeeded |
| Same-tenant non-owner denied | R18 Alice/b: 404 `{"detail":"Not Found"}` | Ownership boundary held for this replay |
| Cross-tenant non-owner denied | R19 Alice/c and R20 Carol/a: 404 with no ticket content | Cross-tenant replays denied; both ownership and tenant differ |
| Admin still requires ownership for detail view | R21 admin/a: 404 | No admin ownership bypass in this case |
| Non-admin export denied | R22 Bob, R23 Carol, R26 Alice: 403 `Administrator required` | Role boundary held for all supplied non-admin accounts |
| Admin export limited to north | R17: 200 JSON containing Alice/north and Bob/north only | South ticket observed at R16 was absent from export |

Export evidence R17:

```json
[{"owner":"alice","tenant":"north","text":"Synthetic Alice ticket"},{"owner":"bob","tenant":"north","text":"Synthetic Bob ticket"}]
```

### HTML and form handling

R03 exposed a POST `/login` form with `username` and password fields. Authenticated ticket pages exposed GET `/tickets` search with parameter `q`, and POST `/logout` with a hidden CSRF field. No ticket-edit form or additional first-party asset link appeared in the inspected HTML.

R24 submitted the literal search text `<b>audit-marker</b>&"'<script>alert(1)</script>` through the discovered `q` parameter. The returned HTML placed this in paragraph text as:

```html
&lt;b&gt;audit-marker&lt;/b&gt;&amp;&quot;&#x27;&lt;script&gt;alert(1)&lt;/script&gt;
```

The payload was escaped in this response context. No executable markup was reflected by this probe. Browser execution, other contexts, and stored input were not tested.

Successful HTML responses included `Content-Security-Policy: default-src 'none'; form-action 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, and `Cache-Control: no-store`. These are observed defense headers, not proof of universal protection. Some denial responses omitted them; no resulting exploit was demonstrated and this is not reported as a vulnerability.

### Login and logout

- R06/R08/R10/R12 submitted the supplied synthetic accounts to POST `/login`, using form-encoded credentials and `Origin: http://127.0.0.1:10240`. Each returned 303 to `/tickets` and set a session cookie; subsequent account lists confirmed authenticated behavior.
- R27 used the valid Alice fixture credentials in a separate empty cookie jar, **without Origin**. It returned 403 `Forbidden`; R28 `/tickets` remained 401. The missing-Origin check held. A mismatched Origin was not tested.
- R29 submitted Bob's logout form with the correct Origin but a deliberately invalid CSRF value. It returned 403. R30 still returned Bob's authenticated list, confirming logout did not occur.
- R31 submitted Bob's current CSRF value with the correct Origin. It returned 303 to `/` and a cookie update; R32 `/tickets` and R33 `/tickets/b` returned 401.
- R34/R36/R38 logged Alice, Carol, and admin out using each session's current CSRF value and correct Origin. R35/R37/R39 confirmed their cookie jars could no longer access `/tickets` (401). All four assessment sessions were logged out.

Cookie headers are completely redacted in saved evidence. Cookie attributes and server-side invalidation of a copied pre-logout cookie were not assessed. The post-logout checks demonstrate loss of access through the updated client jars, not revocation of a retained cookie.

## Reproduction of access checks

1. GET `/`, `/help`, and `/login` to discover navigation, rules, and login fields.
2. POST `/login` with a supplied fixture account and the site's Origin; retain its cookie only in memory. GET `/tickets` to discover that account's ticket link.
3. Repeat with separate jars for the other supplied accounts. Read each owner's discovered ticket to establish the authorized baseline.
4. Replay Bob's discovered ticket URL using Alice's jar, Carol's URL using Alice's jar, and Alice's URL using Carol's and admin's jars. Compare the 404 bodies to the owner's successful response.
5. GET the navigated `/admin/export` using admin and each non-admin jar. Compare returned records with the independently observed Carol ticket and known tenant assignments.

These steps describe the executed bounded comparisons; no undiscovered identifiers or alternate routes were requested.

## Coverage limits and additional access

The principal unresolved authorization check is **an owner reading their own ticket after leaving its tenant**. All discovered owner/ticket pairs were in the owner's current tenant. Cross-tenant tests also changed ownership, so their denials cannot independently prove the tenant-membership predicate. No tenant-switching or membership mutation was authorized or attempted.

For a follow-up, provide a preconfigured synthetic account that owns a ticket outside its current tenant, and a navigation-accessible link to that ticket. This would isolate the missing matrix case without changing data. A second preconfigured admin in south would also permit a symmetric export check. Neither is required to interpret the tests already completed; neither control failure is presumed.

Other limits: only three discovered ticket identifiers and one admin tenant were available; no exhaustive user/resource matrix, alternate methods, session expiry/fixation, copied-cookie replay, CSRF token interchange, browser behavior, stored HTML, dependency review, infrastructure review, or source review was performed. No further access is needed for this report. Additional work would require an agreed follow-up request budget and any necessary fixture access; no requests beyond R39 were made.
