"""Job Analyst node: extract structured JobSpec from untrusted job post."""
from __future__ import annotations

from agent.handoffs import JobSpec
from agent.llm import get_node_llm, load_prompt
from agent.safety import delimit_untrusted
from agent.state import GigBidState


def analyst_node(state: GigBidState) -> GigBidState:
    prompt = load_prompt("analyst")
    job = state.get("job", {}) or {}
    delimited = delimit_untrusted(f"Title: {job.get('title', '')}\n{job.get('description', '')}", "untrusted_job_post")

    llm = get_node_llm("analyst")
    spec: JobSpec | None = None
    if llm is not None:
        try:
            structured = llm.with_structured_output(JobSpec)
            spec = structured.invoke(f"{prompt}\n\n{delimited}")
        except Exception:
            spec = None

    if spec is None:
        b = job.get("budget") if isinstance(job.get("budget"), dict) else {}
        spec = JobSpec(
            job_id=job.get("job_id", ""),
            title=job.get("title", ""),
            deliverables=_extract_deliverables(job.get("description", "")),
            required_skills=list(job.get("required_skills", []) or []),
            budget_min=job.get("budget_min") if job.get("budget_min") is not None else b.get("min"),
            budget_max=job.get("budget_max") if job.get("budget_max") is not None else b.get("max"),
            currency=job.get("currency", b.get("currency", "USD") if b else "USD"),
            duration_days=job.get("duration_days"),
            screening_questions=list(job.get("screening_questions", []) or []),
            hidden_needs=_infer_hidden_needs(job.get("description", "")),
            raw={},
        )

    return {"job_spec": spec.model_dump(), "step_count": int(state.get("step_count", 0) or 0) + 1}


def _extract_deliverables(description: str) -> list[str]:
    desc = (description or "").lower()
    items = [
        kw for kw in ["dashboard", "report", "model", "classifier", "api", "website", "script", "automation", "pipeline", "rag"]
        if kw in desc
    ]
    return items or ["project deliverable"]


def _infer_hidden_needs(description: str) -> list[str]:
    desc = (description or "").lower()
    needs = []
    if "urgent" in desc or "asap" in desc:
        needs.append("fast turnaround")
    if "fixed" in desc:
        needs.append("fixed-price milestone clarity")
    if "production" in desc or "test" in desc:
        needs.append("production-grade tests and docs")
    return needs
