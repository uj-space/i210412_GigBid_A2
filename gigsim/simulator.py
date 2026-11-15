"""GigSim marketplace simulator service & in-memory client.

Provides a repeatable stand-in for Upwork during development and evaluation:
- Jobs loaded from processed Kaggle + synthetic dev jobs
- Client histories with hidden preferences (budget ceiling, dislike of generic openings)
- Connects balance, proposal drafts, idempotent submissions, and messaging
- Simulated client reply / interview / hire outcomes for end-to-end evals
- Configurable fault injection (5xx / unavailable) for degraded-mode testing
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class GigSimState:
    connects_balance: int = 80
    unavailable: bool = False
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    clients: dict[str, dict[str, Any]] = field(default_factory=dict)
    drafts: dict[str, dict[str, Any]] = field(default_factory=dict)
    submissions: dict[str, dict[str, Any]] = field(default_factory=dict)
    idempotency_cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)


class GigSimSimulator:
    """In-memory GigSim simulator with FastAPI router factory."""

    def __init__(self) -> None:
        self.state = GigSimState()
        self._seed()

    def _seed(self) -> None:
        sample_jobs = ROOT / "data" / "sample" / "jobs.json"
        processed_jobs = ROOT / "data" / "processed" / "all_jobs.json"
        dev_jobs = ROOT / "evals" / "datasets" / "dev_set.json"
        client_hist = ROOT / "data" / "sample" / "client_history.json"

        loaded: list[dict[str, Any]] = []
        if sample_jobs.exists():
            loaded.extend(json.loads(sample_jobs.read_text(encoding="utf-8")))
        if dev_jobs.exists():
            loaded.extend(json.loads(dev_jobs.read_text(encoding="utf-8"))[:60])
        if processed_jobs.exists():
            loaded.extend(json.loads(processed_jobs.read_text(encoding="utf-8"))[:100])

        for j in loaded:
            jid = j.get("job_id") or j.get("id")
            if jid:
                self.state.jobs[jid] = j

        if client_hist.exists():
            for c in json.loads(client_hist.read_text(encoding="utf-8")):
                cid = c.get("client_id")
                if cid:
                    self.state.clients[cid] = c

        # Seed default client histories for dev clients
        for i in range(1, 45):
            cid = f"dev-client-{i:03d}"
            if cid not in self.state.clients:
                self.state.clients[cid] = {
                    "client_id": cid,
                    "completed_projects": 4 + (i % 12),
                    "average_rating": round(4.3 + (i % 7) * 0.1, 2),
                    "payment_verified": i % 6 != 0,
                    "total_spent": 2500.0 + (i * 450.0),
                    "notes": "Verified repeat client" if i % 6 != 0 else "New unverified client",
                    "dislikes_generic": True,
                }

        self.state.messages = [
            {
                "message_id": "msg-001",
                "client_id": "dev-client-001",
                "job_id": "dev-ai_ml_engineer-001",
                "sender": "client",
                "body": "Thanks for applying! Can you share how you handled data leakage in your churn model and your availability for a quick call this week?",
                "timestamp": "2026-11-10T10:15:00Z",
            },
            {
                "message_id": "msg-002",
                "client_id": "dev-client-003",
                "job_id": "dev-fullstack_web_dev-002",
                "sender": "client",
                "body": "We like your React dashboard examples. Could you do a quick call tomorrow or discuss a 15% discount on the $1800 budget?",
                "timestamp": "2026-11-11T14:30:00Z",
            },
        ]

    def set_unavailable(self, flag: bool) -> None:
        self.state.unavailable = flag

    def search_jobs(self, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        if self.state.unavailable:
            raise RuntimeError("GigSim marketplace unavailable (503)")
        q = (query or "").lower().strip()
        items = list(self.state.jobs.values())
        if q:
            items = [
                j for j in items
                if q in (j.get("title", "") + " " + j.get("description", "") + " " + " ".join(j.get("required_skills", []))).lower()
            ]
        return items[:limit]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        if self.state.unavailable:
            raise RuntimeError("GigSim marketplace unavailable (503)")
        return self.state.jobs.get(job_id)

    def get_client_history(self, client_id: str) -> dict[str, Any] | None:
        if self.state.unavailable:
            raise RuntimeError("GigSim marketplace unavailable (503)")
        return self.state.clients.get(client_id)

    def get_connects_balance(self) -> int:
        return self.state.connects_balance

    def list_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        if self.state.unavailable:
            raise RuntimeError("GigSim marketplace unavailable (503)")
        return self.state.messages[-limit:]

    def create_proposal_draft(self, job_id: str, cover_letter: str, screening_answers: list[str], idempotency_key: str) -> dict[str, Any]:
        if idempotency_key in self.state.idempotency_cache:
            return self.state.idempotency_cache[idempotency_key]
        draft_id = f"draft-{uuid.uuid4().hex[:8]}"
        job = self.state.jobs.get(job_id, {})
        res = {
            "draft_id": draft_id,
            "job_id": job_id,
            "cover_letter": cover_letter,
            "screening_answers": screening_answers,
            "connects_cost": int(job.get("connects_cost", 6)),
            "status": "draft",
        }
        self.state.drafts[draft_id] = res
        self.state.idempotency_cache[idempotency_key] = res
        return res

    def submit_proposal(self, draft_id: str, idempotency_key: str) -> dict[str, Any]:
        if idempotency_key in self.state.idempotency_cache:
            return self.state.idempotency_cache[idempotency_key]
        draft = self.state.drafts.get(draft_id)
        cost = int((draft or {}).get("connects_cost", 6))
        if self.state.connects_balance < cost:
            return {"status": "error", "error": "Insufficient Connects", "submitted": False}
        self.state.connects_balance -= cost
        outcome = self.simulate_client_outcome(
            (draft or {}).get("job_id", ""),
            (draft or {}).get("cover_letter", ""),
        )
        res = {
            "submission_id": f"sub-{uuid.uuid4().hex[:8]}",
            "draft_id": draft_id,
            "submitted": True,
            "connects_spent": cost,
            "remaining_connects": self.state.connects_balance,
            "simulated_outcome": outcome,
        }
        self.state.submissions[draft_id] = res
        self.state.idempotency_cache[idempotency_key] = res
        return res

    def send_message(self, client_id: str, body: str, idempotency_key: str) -> dict[str, Any]:
        if idempotency_key in self.state.idempotency_cache:
            return self.state.idempotency_cache[idempotency_key]
        msg = {
            "message_id": f"msg-{uuid.uuid4().hex[:8]}",
            "client_id": client_id,
            "sender": "freelancer",
            "body": body,
            "sent": True,
        }
        self.state.messages.append(msg)
        self.state.idempotency_cache[idempotency_key] = msg
        return msg

    def simulate_client_outcome(self, job_id: str, cover_letter: str, has_citations: bool = True) -> dict[str, Any]:
        """Deterministic client simulator: evaluates personalisation, evidence citations, and generic openers."""
        job = self.state.jobs.get(job_id, {})
        text = (cover_letter or "").lower()
        generic_openers = ["i am writing to apply", "hardworking developer", "dear sir/madam"]
        is_generic = any(g in text for g in generic_openers) and "[" not in text
        skills = [s.lower() for s in (job.get("required_skills") or [])]
        skill_hits = sum(1 for s in skills if s in text)
        has_evidence_ref = "[" in text or "case study" in text or "delivered" in text or has_citations
        replied = (not is_generic) and (skill_hits >= 1) and has_evidence_ref and len(text) >= 100
        hired = replied and skill_hits >= 2 and len(text) >= 160
        return {"replied": replied, "hired": hired, "skill_hits": skill_hits, "generic_penalty": is_generic}


_GLOBAL_SIM = GigSimSimulator()


def get_simulator() -> GigSimSimulator:
    return _GLOBAL_SIM
