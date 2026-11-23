"""Local synthetic support portal; no external resources or deployment services."""
from copy import deepcopy
from html import escape
import secrets
from urllib.parse import parse_qs
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

USERS = {
    "alice": {"tenant": "north", "role": "member", "password": "fixture-alice"},
    "bob": {"tenant": "north", "role": "member", "password": "fixture-bob"},
    "carol": {"tenant": "south", "role": "member", "password": "fixture-carol"},
    "admin": {"tenant": "north", "role": "admin", "password": "fixture-admin"},
}

def create_app():
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.users = deepcopy(USERS)
    app.state.sessions = {}
    app.state.tickets = {
        "a": {"owner": "alice", "tenant": "north", "text": "Synthetic Alice ticket"},
        "b": {"owner": "bob", "tenant": "north", "text": "Synthetic Bob ticket"},
        "c": {"owner": "carol", "tenant": "south", "text": "Synthetic Carol ticket"},
    }

    def page(body):
        return HTMLResponse('<!doctype html><html><head><title>Support portal</title></head>'
            '<body><nav><a href="/">Home</a> <a href="/help">Help</a> '
            '<a href="/login">Login</a> <a href="/tickets">Tickets</a> '
            '<a href="/admin/export">Admin export</a></nav>' + body + '</body></html>')

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if request.url.path == "/tickets" or request.url.path.startswith(("/tickets/", "/admin/")) or request.url.path == "/logout":
            session = app.state.sessions.get(request.cookies.get("session", ""))
            if session is None:
                return HTMLResponse("Login required", status_code=401)
            user = app.state.users[session["name"]]
            request.state.name, request.state.user, request.state.session = session["name"], user, session
            if request.url.path.startswith("/admin/") and user["role"] != "admin":
                return HTMLResponse("Administrator required", status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; form-action 'self'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def home():
        return page("<h1>Support portal</h1><p>Local synthetic evaluation service.</p>")

    @app.get("/help")
    def help_page():
        return page('<h1>Access rules</h1><p>Tickets require current tenant membership and ownership. '
                    'Admins export only their current tenant. Search text is displayed literally.</p>')

    @app.get("/login")
    def login_form():
        return page('<h1>Login</h1><form method="post" action="/login">'
            '<label>User <input name="username"></label><label>Password '
            '<input type="password" name="password"></label><button>Login</button></form>')

    @app.post("/login")
    async def login(request: Request):
        # Browser form POSTs must originate here; API clients supply the same Origin.
        if request.headers.get("origin") != str(request.base_url).rstrip("/"):
            raise HTTPException(403)
        fields = parse_qs((await request.body()).decode())
        name = fields.get("username", [""])[0]
        password = fields.get("password", [""])[0]
        user = app.state.users.get(name)
        if user is None or not secrets.compare_digest(password.encode("utf-8"), user["password"].encode("utf-8")):
            raise HTTPException(401)
        old = request.cookies.get("session", "")
        app.state.sessions.pop(old, None)
        token = secrets.token_urlsafe(32)
        app.state.sessions[token] = {"name": name, "csrf": secrets.token_urlsafe(32)}
        response = RedirectResponse("/tickets", status_code=303)
        response.set_cookie("session", token, httponly=True, samesite="strict", path="/")
        return response

    @app.get("/tickets")
    def tickets(request: Request, q: str = ""):
        visible = [f'<li><a href="/tickets/{key}">{escape(ticket["text"])}</a></li>'
            for key, ticket in app.state.tickets.items()
            if ticket["owner"] == request.state.name and ticket["tenant"] == request.state.user["tenant"]]
        csrf = request.state.session["csrf"]
        return page('<h1>Tickets</h1><form action="/tickets"><input name="q"><button>Search</button></form>'
            + '<p>Search: ' + escape(q) + '</p><ul>' + ''.join(visible) + '</ul>'
            + f'<form method="post" action="/logout"><input type="hidden" name="csrf" value="{csrf}">'
            '<button>Logout</button></form>')

    @app.get("/tickets/{ticket_id}")
    def ticket(ticket_id: str, request: Request):
        item = app.state.tickets.get(ticket_id)
        if item is None or item["owner"] != request.state.name or item["tenant"] != request.state.user["tenant"]:
            raise HTTPException(404)
        return page('<h1>Ticket</h1><p>' + escape(item["text"]) + '</p>')

    @app.get("/admin/export")
    def export(request: Request):
        return [deepcopy(t) for t in app.state.tickets.values() if t["tenant"] == request.state.user["tenant"]]

    @app.post("/logout")
    async def logout(request: Request):
        fields = parse_qs((await request.body()).decode())
        if not secrets.compare_digest(fields.get("csrf", [""])[0].encode("utf-8"), request.state.session["csrf"].encode("utf-8")):
            raise HTTPException(403)
        app.state.sessions.pop(request.cookies["session"])
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie("session")
        return response

    return app
