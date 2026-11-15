"""Marketplace port abstraction (R1).

All marketplace access goes through one internal interface with two adapters:
- ``gigsim`` -> ``mcp_servers.marketplace.adapters.gigsim.GigSimAdapter``
- ``upwork_live`` -> ``mcp_servers.marketplace.adapters.upwork_live.UpworkLiveAdapter``
switched by config / environment variable.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import time
from typing import Any, Optional
import httpx


@dataclass
class Job:
    job_id: str
    title: str
    description: str
    required_skills: list[str]
    budget_min: Optional[float]
    budget_max: Optional[float]
    currency: str
    duration_days: Optional[int]
    screening_questions: list[str]
    warning_signals: list[str]
    connects_cost: int
    client_id: str
    posted_at: str
    raw: dict[str, Any]


@dataclass
class ClientHistory:
    client_id: str
    completed_projects: int
    average_rating: float
    payment_verified: bool
    total_spent: Optional[float]
    notes: str
    raw: dict[str, Any]


class MarketplacePort:
    """Single internal marketplace interface."""

    def __init__(
        self,
        mode: str = "gigsim",
        base_url: str = "http://localhost:8081",
        api_token: Optional[str] = None,
        requests_per_minute: int = 20,
    ):
        self.mode = mode
        self.base_url = base_url
        self.api_token = api_token
        self._min_interval = 60.0 / max(requests_per_minute, 1)
        self._last_call = 0.0
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=httpx.Timeout(15.0))

    def _throttle(self) -> None:
        with self._lock:
            now = time.time()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(min(wait, 0.25))
            self._last_call = time.time()

    def _to_job(self, d: dict[str, Any]) -> Job:
        b = d.get("budget", {})
        return Job(
            job_id=d.get("job_id", d.get("id", "")),
            title=d.get("title", ""),
            description=d.get("description", ""),
            required_skills=list(d.get("required_skills", d.get("skills", [])) or []),
            budget_min=(b.get("min") if isinstance(b, dict) else d.get("budget_min")),
            budget_max=(b.get("max") if isinstance(b, dict) else d.get("budget_max")),
            currency=(b.get("currency") if isinstance(b, dict) else None) or d.get("currency", "USD"),
            duration_days=d.get("duration_days"),
            screening_questions=list(d.get("screening_questions", []) or []),
            warning_signals=list(d.get("warning_signals", []) or []),
            connects_cost=int(d.get("connects_cost", 6) or 6),
            client_id=d.get("client_id", ""),
            posted_at=d.get("posted_at", ""),
            raw=d,
        )

    # ---- read tools ----------------------------------------------------
    def search_jobs(self, query: str = "", limit: int = 50) -> list[Job]:
        raise NotImplementedError

    def get_job(self, job_id: str) -> Optional[Job]:
        raise NotImplementedError

    def get_client_history(self, client_id: str) -> Optional[ClientHistory]:
        raise NotImplementedError

    def get_connects_balance(self) -> int:
        raise NotImplementedError

    def list_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    # ---- write tools (idempotent) --------------------------------------
    def create_proposal_draft(
        self, job_id: str, cover_letter: str, screening_answers: list[str], idempotency_key: str
    ) -> dict[str, Any]:
        raise NotImplementedError

    def submit_proposal(self, draft_id: str, idempotency_key: str) -> dict[str, Any]:
        raise NotImplementedError

    def send_message(self, client_id: str, body: str, idempotency_key: str) -> dict[str, Any]:
        raise NotImplementedError


def build_port(mode: str | None = None, user_id: str = "default", oauth_token: str | None = None) -> MarketplacePort:
    """Factory: build a MarketplacePort from config/env (gigsim or upwork_live)."""
    mode = mode or os.environ.get("MARKETPLACE_MODE", "gigsim")
    base_url = os.environ.get("GIGSIM_BASE_URL", "http://localhost:8081")
    token = os.environ.get("GIGSIM_API_TOKEN")
    rpm = int(os.environ.get("GIGSIM_RPM", "20"))
    if mode in {"gigsim", "gigsim_http"}:
        from mcp_servers.marketplace.adapters.gigsim import GigSimAdapter

        return GigSimAdapter(mode=mode, base_url=base_url, api_token=token, requests_per_minute=rpm)
    if mode == "upwork_live":
        from mcp_servers.marketplace.adapters.upwork_live import UpworkLiveAdapter

        return UpworkLiveAdapter(user_id=user_id, oauth_token=oauth_token, requests_per_minute=min(rpm, 6))
    raise ValueError(f"Unknown marketplace mode: {mode}")
