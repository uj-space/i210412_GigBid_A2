"""GigSim adapter implementing the single MarketplacePort interface."""
from __future__ import annotations

from typing import Any, Optional
import httpx

from agent.marketplace_port import ClientHistory, Job, MarketplacePort
from gigsim.simulator import get_simulator


class GigSimAdapter(MarketplacePort):
    """Adapter over GigSim (HTTP service if GIGSIM_BASE_URL is live, else local GigSimSimulator)."""

    def _use_http(self) -> bool:
        return bool(self.base_url and self.base_url.startswith("http") and self.mode == "gigsim_http")

    def search_jobs(self, query: str = "", limit: int = 50) -> list[Job]:
        self._throttle()
        if self._use_http():
            try:
                resp = self._client.get(
                    f"{self.base_url}/jobs",
                    params={"q": query, "limit": limit},
                    headers={"Authorization": f"Bearer {self.api_token}"} if self.api_token else None,
                )
                resp.raise_for_status()
                data = resp.json()
                raw_jobs = data.get("jobs", data if isinstance(data, list) else [])
                return [self._to_job(j) for j in raw_jobs[:limit]]
            except Exception as exc:
                raise ConnectionError(f"Marketplace unavailable: {exc}") from exc
        sim = get_simulator()
        return [self._to_job(j) for j in sim.search_jobs(query=query, limit=limit)]

    def get_job(self, job_id: str) -> Optional[Job]:
        self._throttle()
        if self._use_http():
            resp = self._client.get(f"{self.base_url}/jobs/{job_id}")
            if resp.status_code != 200:
                return None
            return self._to_job(resp.json())
        j = get_simulator().get_job(job_id)
        return self._to_job(j) if j else None

    def get_client_history(self, client_id: str) -> Optional[ClientHistory]:
        self._throttle()
        d = get_simulator().get_client_history(client_id)
        if not d:
            return None
        return ClientHistory(
            client_id=d.get("client_id", client_id),
            completed_projects=int(d.get("completed_projects", 0)),
            average_rating=float(d.get("average_rating", 0.0)),
            payment_verified=bool(d.get("payment_verified", False)),
            total_spent=d.get("total_spent"),
            notes=d.get("notes", ""),
            raw=d,
        )

    def get_connects_balance(self) -> int:
        self._throttle()
        return get_simulator().get_connects_balance()

    def list_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        self._throttle()
        return get_simulator().list_messages(limit=limit)

    def create_proposal_draft(
        self, job_id: str, cover_letter: str, screening_answers: list[str], idempotency_key: str
    ) -> dict[str, Any]:
        self._throttle()
        return get_simulator().create_proposal_draft(job_id, cover_letter, screening_answers, idempotency_key)

    def submit_proposal(self, draft_id: str, idempotency_key: str) -> dict[str, Any]:
        self._throttle()
        return get_simulator().submit_proposal(draft_id, idempotency_key)

    def send_message(self, client_id: str, body: str, idempotency_key: str) -> dict[str, Any]:
        self._throttle()
        return get_simulator().send_message(client_id, body, idempotency_key)
