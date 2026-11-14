"""Marketplace port abstraction.

R1: One marketplace port. All marketplace access goes through this internal
interface with two adapters (GigSim and live Upwork), switched by config.
Agents never call GigSim/Upwork directly; they go through the port.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import httpx
import os
import threading
import time


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
    """Single internal marketplace interface. Backed by GigSim (dev/grading) or
    the official Upwork MCP server (live mode), switched by config."""

    def __init__(self, mode: str = "gigsim", base_url: str = "http://localhost:8081",
                 api_token: Optional[str] = None, requests_per_minute: int = 20):
        self.mode = mode
        self.base_url = base_url
        self.api_token = api_token
        self._min_interval = 60.0 / max(requests_per_minute, 1)
        self._last_call = 0.0
        self._lock = threading.Lock()
        self._client = httpx.Client(timeout=httpx.Timeout(15.0))

    # ---- rate limiting -------------------------------------------------
    def _throttle(self) -> None:
        with self._lock:
            now = time.time()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()
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
    def create_proposal_draft(self, job_id: str, cover_letter: str,
                              screening_answers: list[str], idempotency_key: str) -> dict[str, Any]:
        raise NotImplementedError

    def submit_proposal(self, draft_id: str, idempotency_key: str) -> dict[str, Any]:
        raise NotImplementedError

    def send_message(self, client_id: str, body: str, idempotency_key: str) -> dict[str, Any]:
        raise NotImplementedError



class GigSimAdapter(MarketplacePort):
    """Adapter over the GigSim marketplace simulator REST API."""

    def search_jobs(self, query: str = "", limit: int = 50) -> list[Job]:
        self._throttle()
        try:
            resp = self._client.get(f"{self.base_url}/jobs",
                                    params={"q": query, "limit": limit},
                                    headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            if resp.status_code >= 500:
                return self._fallback_jobs()
            data = resp.json()
        except Exception:
            return self._fallback_jobs()
        return [self._to_job(j) for j in data.get("jobs", data if isinstance(data, list) else [])][:limit]

    def get_job(self, job_id: str) -> Optional[Job]:
        self._throttle()
        try:
            resp = self._client.get(f"{self.base_url}/jobs/{job_id}",
                                    headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            if resp.status_code != 200:
                return None
            return self._to_job(resp.json())
        except Exception:
            return None

    def get_client_history(self, client_id: str) -> Optional[ClientHistory]:
        self._throttle()
        try:
            resp = self._client.get(f"{self.base_url}/clients/{client_id}",
                                    headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            if resp.status_code != 200:
                return None
            d = resp.json()
            return ClientHistory(
                client_id=d.get("client_id", client_id),
                completed_projects=d.get("completed_projects", 0),
                average_rating=d.get("average_rating", 0.0),
                payment_verified=d.get("payment_verified", False),
                total_spent=d.get("total_spent"),
                notes=d.get("notes", ""),
                raw=d,
            )
        except Exception:
            return None

    def get_connects_balance(self) -> int:
        self._throttle()
        try:
            resp = self._client.get(f"{self.base_url}/connects",
                                    headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            return int(resp.json().get("balance", 0))
        except Exception:
            return 0

    def list_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        self._throttle()
        try:
            resp = self._client.get(f"{self.base_url}/messages",
                                    params={"limit": limit},
                                    headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            return resp.json().get("messages", [])
        except Exception:
            return []

    def create_proposal_draft(self, job_id: str, cover_letter: str,
                              screening_answers: list[str], idempotency_key: str) -> dict[str, Any]:
        self._throttle()
        try:
            resp = self._client.post(f"{self.base_url}/proposals/draft",
                                     json={"job_id": job_id, "cover_letter": cover_letter,
                                           "screening_answers": screening_answers,
                                           "idempotency_key": idempotency_key},
                                     headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e), "draft_id": None}

    def submit_proposal(self, draft_id: str, idempotency_key: str) -> dict[str, Any]:
        self._throttle()
        try:
            resp = self._client.post(f"{self.base_url}/proposals/{draft_id}/submit",
                                     json={"idempotency_key": idempotency_key},
                                     headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e), "submitted": False}

    def send_message(self, client_id: str, body: str, idempotency_key: str) -> dict[str, Any]:
        self._throttle()
        try:
            resp = self._client.post(f"{self.base_url}/messages",
                                     json={"client_id": client_id, "body": body,
                                           "idempotency_key": idempotency_key},
                                     headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None)
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e), "sent": False}
    # ---- internal helpers ---------------------------------------------
    def _to_job(self, d: dict[str, Any]) -> Job:
        b = d.get("budget", {})
        return Job(
            job_id=d.get("job_id", d.get("id", "")),
            title=d.get("title", ""),
            description=d.get("description", ""),
            required_skills=d.get("required_skills", d.get("skills", [])),
            budget_min=b.get("min") if isinstance(b, dict) else None,
            budget_max=b.get("max") if isinstance(b, dict) else None,
            currency=(b.get("currency") if isinstance(b, dict) else None) or d.get("currency", "USD"),
            duration_days=d.get("duration_days"),
            screening_questions=d.get("screening_questions", []),
            warning_signals=d.get("warning_signals", []),
            connects_cost=d.get("connects_cost", 0),
            client_id=d.get("client_id", ""),
            posted_at=d.get("posted_at", ""),
            raw=d,
        )

    def _fallback_jobs(self) -> list[Job]:
        return []


def build_port(mode: str | None = None) -> MarketplacePort:
    """Factory: build a MarketplacePort from env/config."""
    mode = mode or os.environ.get("MARKETPLACE_MODE", "gigsim")
    base_url = os.environ.get("GIGSIM_BASE_URL", "http://localhost:8081")
    token = os.environ.get("GIGSIM_API_TOKEN")
    rpm = int(os.environ.get("GIGSIM_RPM", "20"))
    if mode == "gigsim":
        return GigSimAdapter(mode=mode, base_url=base_url, api_token=token, requests_per_minute=rpm)
    raise ValueError(f"Unknown marketplace mode: {mode}")