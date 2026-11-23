"""Synthetic document collaboration service. State is reset by create_app()."""
from copy import deepcopy
from time import time
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

USERS = {
    "alice": {"tenant": "north", "role": "member"},
    "bob": {"tenant": "north", "role": "member"},
    "carol": {"tenant": "south", "role": "member"},
    "admin": {"tenant": "north", "role": "admin"},
}

class Share(BaseModel):
    recipient: str
    expires_at: float

def create_app():
    app = FastAPI()
    app.state.users = deepcopy(USERS)
    app.state.documents = {
        "a": {"id": "a", "owner": "alice", "tenant": "north", "text": "Synthetic alpha"},
        "b": {"id": "b", "owner": "bob", "tenant": "north", "text": "Synthetic beta"},
        "c": {"id": "c", "owner": "carol", "tenant": "south", "text": "Synthetic gamma"},
    }
    app.state.shares = []

    def actor(request):
        name = request.headers.get("authorization", "").removeprefix("Bearer fixture-")
        if name not in app.state.users:
            raise HTTPException(401)
        return name, app.state.users[name]

    def document(doc_id):
        if doc_id not in app.state.documents:
            raise HTTPException(404)
        return app.state.documents[doc_id]

    def can_read(name, user, doc):
        if doc["owner"] == name:
            return True
        return any(s["document"] == doc["id"] and s["recipient"] == name
                   and not s["revoked"] for s in app.state.shares)

    @app.get("/documents/{doc_id}")
    def read(doc_id: str, request: Request):
        name, user = actor(request)
        doc = document(doc_id)
        if not can_read(name, user, doc):
            raise HTTPException(404)
        return deepcopy(doc)

    @app.post("/documents/{doc_id}/shares", status_code=201)
    def share(doc_id: str, body: Share, request: Request):
        name, user = actor(request)
        doc = document(doc_id)
        recipient = app.state.users.get(body.recipient)
        if doc["owner"] != name or user["tenant"] != doc["tenant"]:
            raise HTTPException(403)
        if not recipient or recipient["tenant"] != doc["tenant"] or body.expires_at <= time():
            raise HTTPException(422)
        item = {"id": len(app.state.shares) + 1, "document": doc_id,
                "recipient": body.recipient, "expires_at": body.expires_at, "revoked": False}
        app.state.shares.append(item)
        return deepcopy(item)

    @app.delete("/shares/{share_id}", status_code=204)
    def revoke(share_id: int, request: Request):
        name, user = actor(request)
        item = next((s for s in app.state.shares if s["id"] == share_id), None)
        if item is None:
            raise HTTPException(404)
        doc = document(item["document"])
        if doc["owner"] != name or user["tenant"] != doc["tenant"]:
            raise HTTPException(403)
        item["revoked"] = True

    @app.get("/admin/inventory")
    def inventory(request: Request):
        _, user = actor(request)
        if user["role"] != "admin":
            raise HTTPException(403)
        return [deepcopy(d) for d in app.state.documents.values() if d["tenant"] == user["tenant"]]

    return app
