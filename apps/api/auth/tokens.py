"""User session and Fernet-encrypted OAuth token store (E4)."""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Any

from cryptography.fernet import Fernet

_OAUTH_TOKENS: dict[str, bytes] = {}
_USER_SETTINGS: dict[str, dict[str, Any]] = {}


def _fernet() -> Fernet:
    secret = os.environ.get("APP_SECRET_KEY", "dev-secret-change-me").encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def store_oauth_token(user_id: str, provider: str, token: str) -> None:
    """Encrypt and store per-user OAuth token (never logged)."""
    _OAUTH_TOKENS[f"{user_id}:{provider}"] = _fernet().encrypt(token.encode("utf-8"))


def get_oauth_token(user_id: str, provider: str) -> str | None:
    enc = _OAUTH_TOKENS.get(f"{user_id}:{provider}")
    if not enc:
        return None
    return _fernet().decrypt(enc).decode("utf-8")


def get_user_id_from_header(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return "ai_ml_engineer"
    return authorization.split(" ", 1)[1].strip() or "ai_ml_engineer"


def get_user_settings(user_id: str) -> dict[str, Any]:
    return _USER_SETTINGS.setdefault(
        user_id,
        {
            "autonomy_level": "review_all",
            "weekly_connects_budget": 80,
            "hourly_floor": 45,
            "saved_searches": ["python machine learning", "fastapi langgraph"],
            "connected_marketplace": "gigsim",
        },
    )


def update_user_settings(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    cur = get_user_settings(user_id)
    cur.update(patch)
    return cur
