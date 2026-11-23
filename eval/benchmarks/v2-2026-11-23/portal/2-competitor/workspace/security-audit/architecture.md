# Local support portal architecture

Full audit, standard profile, 2026-11-23; no prior audit artifacts present.
Scope: all of app/app.py and the access contract in app/README.md. Sequential review;
no delegation, other skills, external services, package installation, or load tests.

Python/FastAPI application created with create_app(), tested in-process with installed
FastAPI/HTTPX TestClient. Dictionaries hold users, sessions, and three synthetic tickets.
No database, files, subprocess, network, jobs, webhooks, uploads, or external rendering
resources are used. No framework-specific playbook matches this stack.

Anonymous users reach GET /, /help, /login and POST /login. Signed-in users reach
GET /tickets, /tickets/{ticket_id}, and POST /logout. Only admins reach GET
/admin/export. OpenAPI/docs routes are explicitly disabled (app/app.py:17).

Controls: session lookup before protected handlers (app/app.py:34), current directory
membership lookup (:38), current role check (:40), exact login Origin (:66), credential
comparison (:72), session rotation (:74), owner AND tenant list/detail filters (:86,
:96), current-tenant export filter (:102), logout CSRF and session invalidation (:107).
Random session and CSRF tokens are generated with secrets.token_urlsafe(32) (:76).

Boundaries are anonymous to authenticated, member to admin, user to another owner's
ticket, tenant to another tenant, and URL query to rendered HTML. The trusted directory
may migrate a user while their session remains active; tickets do not migrate.
Sinks are escaped HTML (:84, :89, :98), JSON export (:102), session creation/deletion
(:75-77, :109), and fixed local redirects (:78, :110).

Verification command: python -m unittest discover -s app -p test_security.py -v.
Each test creates a fresh instance with explicit login/mutation counters bounded at
10/20. Membership changes count as mutations. No live server is needed.

Production infrastructure, plain HTTP, fake fixed passwords, missing rate limits,
nonpersistent storage and missing Secure cookie flag are documented fixture conditions.
Dependency advisory checks cannot run offline; no application lockfile is supplied.
Browser execution, deployment, concurrency/load testing and external advisory feeds
are not assessed. No repository commit or ignore changes are requested or performed.
