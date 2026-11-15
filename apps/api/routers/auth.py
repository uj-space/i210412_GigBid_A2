"""Auth, onboarding, OAuth token storage, settings, and memory management router."""
from __future__ import annotations

from fastapi import APIRouter, Header

from agent.memory.store import get_memory_store
from apps.api.auth.tokens import get_user_id_from_header, get_user_settings, store_oauth_token, update_user_settings
from apps.api.schemas.api import LoginRequest

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/login")
async def login(req: LoginRequest):
    return {"user_id": req.persona, "name": req.name, "persona": req.persona, "token": req.persona}


@router.get("/settings")
async def read_settings(authorization: str | None = Header(None)):
    uid = get_user_id_from_header(authorization)
    store = get_memory_store()
    return {
        "settings": get_user_settings(uid),
        "style_memory": store.get_style_memory(uid),
        "outcome_memory": store.get_outcome_memory(uid),
    }


@router.put("/settings")
async def save_settings(payload: dict, authorization: str | None = Header(None)):
    uid = get_user_id_from_header(authorization)
    if isinstance(payload.get("rag_variant"), str):
        try:
            from rag.retriever import set_variant

            set_variant(payload["rag_variant"])
        except ValueError:
            pass
    return {"settings": update_user_settings(uid, payload)}


@router.post("/settings/oauth")
async def save_oauth(payload: dict, authorization: str | None = Header(None)):
    uid = get_user_id_from_header(authorization)
    provider = payload.get("provider", "upwork")
    token = payload.get("token", "")
    if token:
        store_oauth_token(uid, provider, token)
    return {"status": "stored_encrypted", "provider": provider}


@router.get("/memory")
async def get_memory(user_id: str | None = None, authorization: str | None = Header(None)):
    uid = user_id or get_user_id_from_header(authorization)
    store = get_memory_store()
    return {
        "user_id": uid,
        "style": store.get_style_memory(uid),
        "outcome": store.get_outcome_memory(uid),
    }


@router.delete("/memory")
async def clear_memory(kind: str | None = None, user_id: str | None = None, authorization: str | None = Header(None)):
    uid = user_id or get_user_id_from_header(authorization)
    get_memory_store().delete_memory(uid, kind=kind)
    return {"status": "deleted", "kind": kind or "all"}
