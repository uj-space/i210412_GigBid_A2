"""Scout node: run saved searches, deduplicate, queue new jobs."""

from __future__ import annotations

from typing import Any
import hashlib

from agent.state import GigBidState
from agent.marketplace_port import build_port


def _job_fingerprint(job) -> str:
    base = f"{getattr(job, 'job_id', '')}|{getattr(job, 'title', '')}|{getattr(job, 'client_id', '')}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]


def scout_node(state: GigBidState) -> GigBidState:
    """Pull new jobs from saved searches and deduplicate against already-seen jobs."""
    port = build_port()
    seen = set(state.get("seen_job_fingerprints", []) or [])
    saved_searches = state.get("saved_searches", []) or [""]

    new_jobs: list[dict[str, Any]] = []
    for query in saved_searches:
        try:
            jobs = port.search_jobs(query=query, limit=50)
        except Exception as exc:  # degraded mode
            state.setdefault("errors", []).append(f"scout search failed: {exc}")
            continue
        for job in jobs:
            fp = _job_fingerprint(job)
            if fp in seen:
                continue
            seen.add(fp)
            new_jobs.append({
                "job_id": job.job_id,
                "title": job.title,
                "description": job.description,
                "required_skills": job.required_skills,
                "budget_min": job.budget_min,
                "budget_max": job.budget_max,
                "currency": job.currency,
                "duration_days": job.duration_days,
                "screening_questions": job.screening_questions,
                "warning_signals": job.warning_signals,
                "connects_cost": job.connects_cost,
                "client_id": job.client_id,
                "posted_at": job.posted_at,
                "fingerprint": fp,
                "raw": job.raw,
            })

    state["new_jobs"] = new_jobs
    state["seen_job_fingerprints"] = list(seen)
    state.setdefault("errors", [])
    if not new_jobs:
        state.setdefault("messages", []).append("scout: no new jobs found")
    return state
