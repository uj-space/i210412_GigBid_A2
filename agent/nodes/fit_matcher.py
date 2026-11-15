"""Fit Matcher node: map requirements to verified portfolio evidence via Portfolio MCP."""
from __future__ import annotations

from agent.handoffs import FitReport
from agent.llm import load_config, load_prompt
from agent.mcp_client import call_mcp_tool
from agent.state import GigBidState


def fit_matcher_node(state: GigBidState) -> GigBidState:
    _ = load_prompt("fit_matcher")
    cfg = load_config()
    top_k = int((cfg.get("rag") or {}).get("top_k", 6))

    job = state.get("job", {}) or {}
    skills = list(job.get("required_skills", []) or [])
    persona = state.get("user_id", "default")
    if persona not in {"ai_ml_engineer", "fullstack_web_dev", "data_analyst"}:
        persona = "default"

    query = " ".join(skills + [job.get("title", ""), job.get("description", "")[:200]]).strip()
    res = call_mcp_tool(
        "fit_matcher",
        "portfolio",
        "search_evidence",
        {"requirement": query or "software engineering", "k": top_k, "filters": {"persona": persona}},
    )
    evidence = res.get("data") or []

    matched: list[str] = []
    missing: list[str] = []
    for s in skills:
        sl = s.lower()
        if any(
            sl in [sk.lower() for sk in (e.get("skills") or [])] or sl in (e.get("text", "").lower())
            for e in evidence
        ):
            matched.append(s)
        else:
            missing.append(s)

    score = len(matched) / max(len(skills), 1) if skills else (0.6 if evidence else 0.3)
    matrix = []
    for req in skills[:6]:
        rl = req.lower()
        supporting = [
            e.get("evidence_id") or e.get("id")
            for e in evidence
            if rl in [sk.lower() for sk in (e.get("skills") or [])] or rl in (e.get("text", "").lower())
        ]
        matrix.append({"requirement": req, "evidence_ids": supporting[:3]})

    report = FitReport(
        score=round(score, 3),
        matched_skills=matched,
        missing_skills=missing,
        evidence_ids=[e.get("evidence_id") or e.get("id") for e in evidence],
        requirement_matrix=matrix,
        reasons=f"Matched {len(matched)} of {max(len(skills), 1)} required skills across {len(evidence)} portfolio items.",
    )
    return {
        "fit_report": report.model_dump(),
        "evidence": evidence,
        "tool_calls": [{"node": "fit_matcher", "tool": "search_evidence", "status": res.get("status")}],
    }
