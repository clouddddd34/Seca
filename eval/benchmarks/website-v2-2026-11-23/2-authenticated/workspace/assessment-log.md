# Assessment log

Scope: http://127.0.0.1:17499/ and linked first-party resources only. Runtime HTTP review; no source inspection. Maximum 40 sequential requests and 10 logins. Only login/logout mutations authorized. Credentials, cookies and CSRF values redacted from saved evidence.

User-confirmed rules: ticket reads require both ownership and current tenant membership; exports require admin role and current tenant scope. Alice, Bob, admin: north; Carol: south.

Completed: 30 sequential requests, 4 logins. Evidence: evidence/01.json through evidence/30.json. Report: report.md. No confirmed or likely findings. Checked navigation, forms, anonymous gates, all supplied account listings, authorized ticket baselines, same-tenant and cross-tenant replays, admin ticket ownership boundary, export role/tenant scope, search escaping and rejected logout session continuity.

Outstanding coverage: owner outside current tenant cannot be isolated with discovered fixtures; south admin unavailable. Successful logout/session invalidation and independent Origin/CSRF enforcement untested. Requested additional prepared fixtures are documented in report.md; no further runtime requests planned. Cookies remained in process memory only; client process stopped after assessment.
