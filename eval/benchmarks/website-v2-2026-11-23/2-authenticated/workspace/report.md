# Local synthetic website assessment

Assessed on 2026-11-23 (UTC), using the assigned security-audit skill. **No confirmed vulnerabilities were found in the tested surface.** This is a bounded runtime assessment, not a claim that the application is secure.

## Scope and method

Only `http://127.0.0.1:17499/` and routes discovered in its navigation/forms were requested. Conducted **30 sequential HTTP requests, including 4 logins**, with separate in-memory cookie jars for anonymous, Alice, Bob, Carol and admin contexts. Automatic redirects and retries were disabled; requests had a 10-second timeout. No ticket modifications occurred. The only mutation attempts were four authorized logins and one rejected logout.

No application source, files outside the workspace, guessed routes, guessed credentials, packages, external services, delegated agents, port scans or load tests were used. Loopback HTTP, fixture passwords, missing rate limiting/persistence and absent production infrastructure are intentional conditions and are not findings.

Evidence is stored in [evidence](evidence/) as numbered JSON records with method, URL, actor, response status, headers and body. Credentials were not recorded; cookie headers and HTML CSRF values were redacted before saving. All response bodies fit the collection limit. Request numbers below identify the corresponding files (for example, [14](evidence/14.json)).

## Findings

Confirmed: **none**. No likely vulnerabilities were established. Internal implementation and root causes cannot be inferred from these responses.

## Protected controls observed

User-provided rules, corroborated by `/help` (request 2), require ticket ownership **and** current tenant membership; admin exports must be limited to the current tenant. All tested access decisions matched those rules.

| Check | Actual evidence | Result and limit |
| --- | --- | --- |
| Anonymous protection | 4: `/tickets`; 5: `/admin/export`; 27: `/tickets/a` | Each returned 401, `Login required`, without ticket/export content. |
| Valid authentication | 6, 8, 10, 12: POST `/login` with site Origin | Each returned 303 to `/tickets` and set a session cookie; subsequent requests established each identity's access. |
| Account-specific navigation | 7, 9, 11, 13: `/tickets` under Alice, Bob, Carol, admin | Listed `/tickets/a`, `/tickets/b`, `/tickets/c`, and no tickets, respectively. No additional resource routes were guessed. |
| Authorized ticket baselines | 14, 15, 16 | Alice/a, Bob/b and Carol/c returned 200 with their respective synthetic ticket text. |
| Same-tenant ownership boundary | 18: Alice/b; 19: Bob/a | Both returned 404 with only `{"detail":"Not Found"}`. |
| Cross-tenant, non-owner boundary | 20: Alice/c; 21: Carol/a | Both returned the same 404 denial without ticket content. These cases do not isolate membership from ownership. |
| Admin ticket access | 25: admin/a; 26: admin/c | Both returned 404; admin role did not override ownership in these samples. |
| Export role boundary | 22, 23, 24: Alice, Bob, Carol `/admin/export` | Each returned 403, `Administrator required`. |
| Export tenant scope | 17: admin `/admin/export` | Returned 200 JSON containing only Alice/north and Bob/north records. Carol's known south ticket was absent. |
| Search HTML escaping | 28: Alice `/tickets?q=...` | Input `<b data-audit="'&">probe</b>` appeared as `&lt;b data-audit=&quot;&#x27;&amp;&quot;&gt;probe&lt;/b&gt;` within a paragraph. No raw injected element appeared. |
| Rejected logout preserves session | 29: Alice POST `/logout` without Origin or CSRF; 30: Alice/a | Logout returned 403 `Forbidden`; subsequent authorized ticket read returned 200. This does not isolate whether Origin, CSRF, or both caused rejection. |

For bounded reproduction, log in with the supplied synthetic accounts using the site's Origin header and separate sessions, follow each account's ticket link for a successful baseline, then replay the exact discovered URL under the comparison identity. Export comparisons use the navigation's `/admin/export` link. The search request uses the discovered `q` field; its exact encoded URL is in evidence 28.

## HTML, forms and response observations

The home and help pages exposed Home, Help, Login, Tickets and Admin export links (1–2). The login form uses POST `/login`, with `username` and password-type `password` fields (3). Ticket pages expose a GET search form with `q` and POST `/logout` with a hidden CSRF field (7, 9, 11, 13). No scripts, stylesheets or other linked assets appeared in the inspected HTML. No ticket editing forms were encountered.

Successful HTML/JSON responses and ticket 404 responses carried `Content-Security-Policy: default-src 'none'; form-action 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, and `Cache-Control: no-store`. These are observed defense headers, not proof of comprehensive enforcement. Some 401/403 responses lacked these headers; their absence alone does not demonstrate a vulnerability. Cookie values and their complete headers were redacted, so cookie attributes are not evaluated in this report.

## Coverage limits and additional access

- **Ownership without current tenant membership remains untested.** All discovered owned tickets were in their owner's current tenant. Non-owner cross-tenant denials cannot establish the separate membership predicate. To complete this check, provide an already-prepared synthetic account and navigation-discoverable ticket it owns in a tenant it no longer belongs to, together with its current membership. No membership or ticket mutation is requested within this assessment.
- Only a north admin was supplied. The observed north export excluded the known south ticket, but south-admin behavior and post-membership-change export behavior were not tested. An existing south admin or preconfigured changed-membership admin would enable those comparisons if desired.
- Login Origin rejection, successful logout, session invalidation after logout, token mismatch handling, session expiry/rotation and cookie attribute behavior were not independently tested. The logout rejection is deliberately described narrowly above.
- HTML escaping was tested with one benign markup probe in the search text context. Browser execution, other injection contexts and stored content changes were not tested.
- No hidden routes, undiscovered resources, dependency versions, source implementation, deployment configuration or broader exploit classes were assessed. Runtime authorization was evaluated from actual response content as well as status codes.

No additional access is needed to support the observations above. The prepared fixtures described here are needed only to resolve the remaining authorization coverage gaps. No fixes were applied or remediation verification performed.
