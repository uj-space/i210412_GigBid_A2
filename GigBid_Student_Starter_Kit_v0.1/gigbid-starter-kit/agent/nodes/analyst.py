"""Job Analyst node: extract a structured JobSpec from a job post."""
from __future__ import annotations

from typing import Any
from agent.state import GigBidState
from agent.handoffs import JobSpec


def analyst_node(state: GigBidState) -> GigBidState:
    job = state.get("job", {}) or {}
    spec = JobSpec(
        job_id=job.get("job_id", ""),
        title=job.get("title", ""),
        deliverables=_extract_deliverables(job.get("description", "")),
        required_skills=list(job.get("required_skills", []) or []),
        budget_min=job.get("budget_min"),
        budget_max=job.get("budget_max"),
        currency=job.get("currency", "USD"),
        duration_days=job.get("duration_days"),
        screening_questions=list(job.get("screening_questions", []) or []),
        hidden_needs=_infer_hidden_needs(job.get("description", "")),
        raw=job,
    )
    state["job_spec"] = spec.model_dump()
    state["job"] = {**job, "job_spec": spec.model_dump()}
    return state


def _extract_deliverables(description: str) -> list[str]:
    desc = (description or "").lower()
    items = []
    for keyword in ["dashboard", "report", "model", "classifier", "api", "website",
                    "script", "automation", "analysis", "frontend", "backend"]:
        if keyword in desc:
            items.append(keyword)
    return items or ["project deliverable"]


def _infer_hidden_needs(description: str) -> list[str]:
    desc = (description or "").lower()
    needs = []
    if "urgent" in desc or "asap" in desc:
        needs.append("fast turnaround")
    if "fixed price" in desc:
        needs.append("fixed budget")
    if "hourly" in desc:
        needs.append("hourly engagement")
    return needs
