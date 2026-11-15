"""Pydantic request and response schemas for the GigBid FastAPI backend."""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    name: str = Field(min_length=1)
    persona: str = "ai_ml_engineer"


class AnalyzeJobRequest(BaseModel):
    job: dict[str, Any]
    user_id: str = "ai_ml_engineer"
    saved_searches: Optional[list[str]] = None


class ApproveRequest(BaseModel):
    thread_id: str
    action: str  # approved | edited | rejected
    edit: Optional[dict[str, Any]] = None
    reason: Optional[str] = None
    user_id: str = "ai_ml_engineer"


class MessageRequest(BaseModel):
    thread_id: Optional[str] = None
    client_message: dict[str, Any]
    user_id: str = "ai_ml_engineer"


class HealthResponse(BaseModel):
    status: str
    service: str
    marketplace_degraded: bool = False
