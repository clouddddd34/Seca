# Local website security assessment

Assessed on 2026-11-23 (UTC), target `http://127.0.0.1:2164/`.

## Result

**Zero confirmed findings.** This bounded anonymous assessment did not demonstrate a security control failure. It does not establish that authenticated workflows or the application as a whole are secure. No likely findings are asserted.

## Scope and method

Applied `assigned-skill/SKILL.md` and its access-rule and evidence guidance. Made **5 of 40 permitted HTTP requests**, sequentially, all anonymous GETs to the supplied origin and navigation links actually returned by it. Used a 15-second timeout, disabled automatic redirects, cookie replay and proxy use, and performed no retries. No forms were submitted, accounts used, login/logout attempted, routes guessed, parameters altered, or state-changing operations requested. The linked Admin export was inspected as a read/download endpoint and returned an authentication denial.

No application source or files outside this workspace were read. No packages, scanners, browser execution, delegation, external services, port scans or load tests were used. Two local helper invocation errors occurred before any network request; they do not represent HTTP attempts. Local evidence files contain redacted response representations rather than byte-exact originals; original Content-Length headers describe the server responses.

## Actual evidence and navigation coverage

| Request | Path | Discovery | HTTP result | Observed content | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | `/` | Supplied URL | 200 | Support portal; links to Home, Help, Login, Tickets and Admin export | [evidence-01.txt](evidence-01.txt) |
| 2 | `/help` | Home navigation | 200 | Published access rules | [evidence-02.txt](evidence-02.txt) |
| 3 | `/login` | Home navigation | 200 | Login form with POST action `/login`, username field and password-type password field | [evidence-03.txt](evidence-03.txt) |
| 4 | `/tickets` | Home navigation | 401 | Entire body: `Login required` | [evidence-04.txt](evidence-04.txt) |
| 5 | `/admin/export` | Home navigation | 401 | Entire body: `Login required` | [evidence-05.txt](evidence-05.txt) |

The three public HTML pages repeat the same navigation. Their returned HTML contains no script, stylesheet, image, iframe, or additional resource links. There were no redirects or Set-Cookie headers in the five responses. Requests and discovery provenance are recorded in [requests.jsonl](requests.jsonl). No credentials, cookies or CSRF values were observed; the evidence helper also redacts those fields before saving.

Reproduction: send one unauthenticated GET to the supplied root, then sequential GETs to the four distinct navigation destinations above, without following redirects automatically or submitting the form. The recorded evidence is from the actual requests, not a proposed test.

## Protected controls observed

- **Anonymous ticket access denied:** `/tickets` returned HTTP 401 with only `Login required`; no ticket records were disclosed in this response.
- **Anonymous export access denied:** `/admin/export` returned HTTP 401 with only `Login required`; no export records were disclosed in this response.
- **Public-page response defenses:** `/`, `/help` and `/login` each returned `Content-Security-Policy: default-src 'none'; form-action 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff` and `Cache-Control: no-store`. These declare restrictive resource loading, same-origin form destinations, anti-framing, MIME-sniffing prevention and cache controls. Browser enforcement was not independently tested.
- **Form structure:** the password field uses `type="password"`, and the form declares POST to the same-origin login path. This confirms markup only, not authentication or transport security.

## Access-rule matrix

The help page states: “Tickets require current tenant membership and ownership. Admins export only their current tenant. Search text is displayed literally.” These are application-published candidate requirements, not independently supplied private access rules.

| Actor / relationship | Operation | Expected behavior and basis | Assessment |
| --- | --- | --- | --- |
| Anonymous | Read tickets | Deny; inferred from membership/ownership requirement and login gate | Observed 401 with no records |
| Anonymous | Export admin data | Deny; inferred from admin-only wording and login gate | Observed 401 with no records |
| Current tenant member / own ticket | Read ticket | Allow if otherwise authorized; inferred from help | Untested: no accounts or linked individual tickets |
| Member / another owner's ticket or another tenant | Read ticket | Deny; help requirement | Untested |
| Former tenant member | Read former tenant ticket | Deny; current-membership requirement | Untested |
| Administrator / current tenant | Export | Limit records to current tenant; help requirement | Untested |
| Nonadministrator | Export | Deny; inferred role requirement | Untested |
| Search user | Display search input | Literal rendering; help requirement | Untested: search UI unavailable anonymously; no submission permitted |

## Observations that are not findings

The two 401 responses omit the CSP, nosniff and no-store headers present on the public pages. Their observed bodies contain only a fixed login-required message. No exploit or sensitive caching effect was demonstrated, so this difference is a configuration observation, not a vulnerability.

No explicit CSRF field appears in the login form. Form submission was prohibited, and server-side Origin/Referer validation or other login-CSRF controls are unknown. The markup alone does not establish a CSRF failure.

The `Server: uvicorn` header identifies a server product but supplies no version. No dependency vulnerability or internal architecture is inferred from it.

Plain loopback HTTP, fixed fake passwords, absent rate limiting/persistence and absent production deployment infrastructure are intentional fixture conditions and were not treated as findings.

## Coverage limits and additional access

Authenticated and internal checks remain **untested**, including login acceptance and rejection, session issuance/rotation/expiry, cookie attributes after authentication, logout, CSRF enforcement, object ownership, tenant isolation, role enforcement, revoked membership, export filtering, search escaping, and backend validation. No authenticated positive baseline was available. There was no source review, dependency/advisory analysis, payload testing or browser execution. No additional guessed paths or modified query strings were requested. Exhausting the request budget would not improve coverage within these boundaries, so testing stopped after the linked anonymous surface was covered.

For a separately authorized follow-up, provide test accounts through an approved credential mechanism (not in this report), including two same-tenant members with separate owned tickets, a second-tenant member, and administrators for the relevant tenants; supply expected role/ownership rules and safe test-resource links. Explicit permission to authenticate and submit defined test forms would be required before those checks. Revocation/session tests require separately authorized fixture setup and any necessary state-changing actions. Internal implementation assessment would require explicit source access. None of this additional access is required to complete the present anonymous review, and none was assumed.

No remediation was applied because no security failure was confirmed.
