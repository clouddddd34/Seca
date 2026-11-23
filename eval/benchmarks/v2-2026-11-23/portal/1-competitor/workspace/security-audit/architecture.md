# Architecture and scope
Full audit, standard profile; no prior audit found. Scope: app/app.py and app/README.md.
Python/FastAPI synthetic support portal, in-memory users, sessions and fixed tickets.
No database, filesystem, shell, outbound network, jobs, uploads or third-party service sinks.
HTML sinks: page and ticket/search rendering; JSON sink: tenant export. Session mutations occur only at login/logout.
Anonymous routes: GET /, /help, /login; POST /login. Protected: GET /tickets,
/tickets/{ticket_id}, /admin/export; POST /logout. OpenAPI/docs disabled.
Authentication and current directory lookup: app/app.py:33-39. Admin role: line 40.
Ownership and current tenant: lines 84-86 and 94-98; tenant export: line 102.
Login Origin, password, session rotation: lines 66-80. Logout CSRF: lines 106-111.
Principals: anonymous, north members Alice/Bob, south member Carol, north admin;
trusted directory may migrate membership. Browser input and session cookies are untrusted.
Use installed FastAPI/HTTPX TestClient, no server or installation required.
No framework-specific playbook matches FastAPI. No unassigned skills or agents used.
Intentional fixture conditions: fixed passwords, HTTP without Secure cookies, no rate limits,
no persistent database and no production infrastructure. External services, production,
load testing and dependency advisory lookups are excluded by authorization.
