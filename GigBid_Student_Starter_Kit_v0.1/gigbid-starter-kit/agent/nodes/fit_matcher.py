"""Fit Matcher node: map job requirements to verified portfolio evidence."""
from __future__ import annotations

from typing import Any
from agent.state import GigBidState
from agent.handoffs import FitReport
from rag.retriever import retrieve_evidence


def fit_matcher_node(state: GigBidState) -> GigBidState:
    job_spec = state.get("job_spec", {}) or {}
    skills = list(job_spec.get("required_skills", []) or [])
    deliverables = list(job_spec.get("deliverables", []) or [])
    query = " ".join(skills + deliverables + [job_spec.get("title", "")])

    evidence = retrieve_evidence(query, k=8, persona=state.get("user_id", "default"))
    matched = []
    missing = []
    for s in skills:
        if any(s.lower() in (e.get("skills", []) or []) or s.lower() in (e.get("text", "").lower())
               for e in evidence):
            matched.append(s)
        else:
            missing.append(s)

    score = len(matched) / max(len(skills), 1) if skills else 0.5
    matrix = []
    for req in skills + deliverables:
        supporting = [e.get("evidence_id") or e.get("id") for e in evidence
                      if req.lower() in (e.get("text", "").lower()
                                         or " ".join(e.get("skills", [])).lower())]
        matrix.append({"requirement": req, "evidence_ids": supporting[:3]})

    report = FitReport(
        score=round(score, 3),
        matched_skills=matched,
        missing_skills=missing,
        evidence_ids=[e.get("evidence_id") or e.get("id") for e in evidence],
        requirement_matrix=matrix,
        reasons=f"Matched {len(matched)} of {max(len(skills),1)} required skills.",
    )
    state["fit_report"] = report.model_dump()
    state["evidence"] = evidence
    return state
