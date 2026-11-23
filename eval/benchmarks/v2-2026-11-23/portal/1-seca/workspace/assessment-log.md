# Local assessment log

Scope: app/app.py and app/README.md; assigned security-audit skill; in-process FastAPI/HTTPX TestClient only. No external services, package installation, delegation, or out-of-workspace reads. Documentation defines the expected access rules. Synthetic state changes are authorized, with at most ten login attempts and twenty mutations per fresh instance.

Initial source review: one FastAPI factory, in-memory users/sessions/tickets, authentication and role middleware, login Origin check, live directory membership lookup, ownership AND tenant ticket predicates, tenant-filtered admin export, HTML escaping, session rotation, CSRF-protected logout. No database, file input, outbound integration, or dependency manifest supplied.

Hypotheses awaiting bounded verification: unauthorized ticket reads; stale tenant/role access; cross-tenant export; session reuse after rotation/logout; missing logout CSRF enforcement; reflected HTML interpretation. No confirmed finding at initial review. Evidence record template copied to evidence/candidate-template.json; it is not a finding.

Next: run local control tests, record outcomes and limitations, fix only demonstrated bugs.

Completed: all seven tests in app/test_security.py passed on two runs, using fresh instances per test. First PowerShell stderr pipeline reported a shell error despite unittest reporting OK; reran with an explicit Python runner and UTF-8 artifact output, obtaining exit code 0. Final output: evidence/test-results.txt. No confirmed or likely findings; initial control-failure hypotheses were not reproduced. No application fixes justified. Coverage, rule matrix, environment fingerprint, fixture exclusions, and untested areas are recorded in report.md. No outstanding local remediation. Dependency advisory lookup and production/browser/concurrency testing remain outside this assessment.
