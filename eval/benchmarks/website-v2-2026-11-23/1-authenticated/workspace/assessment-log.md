Scope: http://127.0.0.1:34947 and discovered first-party resources only. Runtime-only inspection; no source access, external services, route guessing, installs, delegation, or ticket mutations. Limit 40 sequential requests and 10 logins. Only login/logout state changes authorized.

Rules supplied by user: ticket reads require ownership AND current tenant membership. Admin exports must contain only current tenant. Alice/Bob/admin north; Carol south; only admin is administrator.

Completed: 34 sequential requests, 4 logins, no retries or automatic redirects. Navigation and forms inspected; all four accounts' indexes inspected; three discovered tickets tested against all four authenticated accounts. Anonymous index/export/one-ticket access denied. All non-admin exports denied; north admin export contained only north records. Search HTML-escaping sample was encoded correctly. No confirmed, likely, or unverified vulnerability candidates. See report.md and evidence.jsonl.

Limits: no owner/wrong-current-tenant fixture or south administrator; logout/session invalidation and negative Origin/CSRF tests not performed. Proposed additional fixture access is documented in report.md. No further runtime work pending. No ticket changes; client process ended with session cookies discarded from memory. Credentials/cookies/CSRF redacted in saved evidence.
