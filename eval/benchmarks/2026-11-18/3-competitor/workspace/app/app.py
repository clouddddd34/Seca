"""Deliberately vulnerable, fake-data-only local assessment fixture."""
from copy import deepcopy

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


USERS = {
    "fixture-alice": {"id": "alice", "tenant": "north", "role": "member"},
    "fixture-bob": {"id": "bob", "tenant": "north", "role": "member"},
    "fixture-carol": {"id": "carol", "tenant": "south", "role": "member"},
    "fixture-admin": {"id": "admin", "tenant": "north", "role": "admin"},
}
INVOICES = {
    "inv-a": {"id": "inv-a", "owner": "alice", "tenant": "north", "amount": 100},
    "inv-b": {"id": "inv-b", "owner": "bob", "tenant": "north", "amount": 200},
    "inv-c": {"id": "inv-c", "owner": "carol", "tenant": "south", "amount": 300},
}
REPORTS = {
    "report-n": {"id": "report-n", "tenant": "north", "summary": "Synthetic north report"},
    "report-s": {"id": "report-s", "tenant": "south", "summary": "Synthetic south report"},
}
CATALOG = {"book": 1000}


class Purchase(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=5)
    unit_price_cents: int = Field(ge=1, le=100000)


def create_app():
    app = FastAPI(title="Seca local fixture", docs_url=None, redoc_url=None)
    app.state.orders = []

    @app.middleware("http")
    async def identity_and_admin_boundary(request: Request, call_next):
        if request.url.path in ("/", "/health"):
            return await call_next(request)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        actor = USERS.get(token)
        if actor is None:
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        request.state.actor = actor
        if (request.url.path == "/admin" or request.url.path.startswith("/admin/")) and actor["role"] != "admin":
            return JSONResponse({"detail": "Administrator required"}, status_code=403)
        return await call_next(request)

    @app.get("/")
    def index():
        return {"application": "Seca fake-data fixture", "environment": "local evaluation"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/me")
    def me(request: Request):
        return request.state.actor

    @app.get("/invoices/{invoice_id}")
    def invoice(invoice_id: str, request: Request):
        item = INVOICES.get(invoice_id)
        if item is None or item["owner"] != request.state.actor["id"]:
            raise HTTPException(404, "Not found")
        return deepcopy(item)

    @app.get("/reports/{report_id}")
    def report(report_id: str, request: Request):
        item = REPORTS.get(report_id)
        if item is None or item["tenant"] != request.state.actor["tenant"]:
            raise HTTPException(404, "Not found")
        return deepcopy(item)

    @app.get("/catalog")
    def catalog():
        return CATALOG

    @app.post("/orders", status_code=201)
    def purchase(body: Purchase, request: Request):
        if body.sku not in CATALOG:
            raise HTTPException(404, "Unknown product")
        order = {"id": len(app.state.orders) + 1, "owner": request.state.actor["id"],
                 "sku": body.sku, "quantity": body.quantity,
                 "total_cents": body.quantity * CATALOG[body.sku]}
        app.state.orders.append(order)
        return order

    @app.get("/orders")
    def orders(request: Request):
        return [o for o in app.state.orders if o["owner"] == request.state.actor["id"]]

    @app.get("/admin/export")
    def export():
        return {"export": "Synthetic administrative data"}

    return app


app = create_app()
