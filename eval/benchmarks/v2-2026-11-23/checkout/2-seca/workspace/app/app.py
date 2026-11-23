"""Synthetic checkout and returns service with independent per-instance state."""
from copy import deepcopy
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

class Cart(BaseModel):
    quantity: int = Field(ge=1, le=3)

class Payment(BaseModel):
    coupon: str = ""

def create_app():
    app = FastAPI()
    app.state.orders = {}
    app.state.wallets = {"alice": 10000, "bob": 10000}
    app.state.used_coupons = set()

    def actor(request):
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer fixture-"):
            raise HTTPException(401)
        name = authorization.removeprefix("Bearer fixture-")
        if name not in app.state.wallets:
            raise HTTPException(401)
        return name

    def owned(order_id, name):
        order = app.state.orders.get(order_id)
        if order is None or order["owner"] != name:
            raise HTTPException(404)
        return order

    @app.post("/orders", status_code=201)
    def create(body: Cart, request: Request):
        name = actor(request)
        order = {"id": len(app.state.orders) + 1, "owner": name, "quantity": body.quantity,
                 "total": body.quantity * 1000, "state": "draft", "paid": 0}
        app.state.orders[order["id"]] = order
        return deepcopy(order)

    @app.get("/orders/{order_id}")
    def read(order_id: int, request: Request):
        return deepcopy(owned(order_id, actor(request)))

    @app.post("/orders/{order_id}/pay")
    def pay(order_id: int, body: Payment, request: Request):
        name = actor(request)
        order = owned(order_id, name)
        if order["state"] != "draft":
            raise HTTPException(409)
        if body.coupon not in ("", "WELCOME"):
            raise HTTPException(422)
        if body.coupon and (name, body.coupon) in app.state.used_coupons:
            raise HTTPException(409)
        discount = 500 if body.coupon == "WELCOME" else 0
        charge = order["total"] - discount
        if app.state.wallets[name] < charge:
            raise HTTPException(409)
        app.state.wallets[name] -= charge
        if body.coupon:
            app.state.used_coupons.add((name, body.coupon))
        order.update(state="paid", paid=charge)
        return deepcopy(order)

    @app.post("/orders/{order_id}/refund")
    def refund(order_id: int, request: Request):
        name = actor(request)
        order = owned(order_id, name)
        if order["state"] != "paid":
            raise HTTPException(409)
        app.state.wallets[name] += order["paid"]
        order["state"] = "refunded"
        return deepcopy(order)

    @app.get("/wallet")
    def wallet(request: Request):
        name = actor(request)
        return {"balance": app.state.wallets[name],
                "used_coupons": sorted(c for owner, c in app.state.used_coupons if owner == name)}

    return app
