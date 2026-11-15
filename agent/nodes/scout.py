"""Scout node: deduplicate jobs and fetch via Marketplace MCP allowlist."""
from __future__ import annotations

import hashlib
from agent.llm import load_prompt
from agent.mcp_client import call_mcp_tool
from agent.safety import mask_pii
from agent.state import GigBidState


def scout_node(state: GigBidState) -> GigBidState:
    _ = load_prompt("scout")
    job = state.get("job") or {}
    seen = set(state.get("seen_job_fingerprints", []) or [])
    trace_id = state.get("trace_id", "trace-local")
    user_id = state.get("user_id", "default")

    if not job:
        searches = state.get("saved_searches") or [""]
        res = call_mcp_tool(
            "scout",
            "marketplace",
            "search_jobs",
            {"query": searches[0], "limit": 5, "user_id": user_id, "trace_id": trace_id},
        )
        state.setdefault("tool_calls", []).append({
            "node": "scout", "tool": "search_jobs", "status": res.get("status"), "trace_id": trace_id
        })
        items = res.get("data") or []
        if items:
            job = items[0]
            state["job"] = job

    fp = hashlib.sha256(f"{job.get('title','')}|{job.get('description','')[:120]}".encode()).hexdigest()[:12]
    if fp not in seen:
        state["seen_job_fingerprints"] = [fp]

    state["step_count"] = int(state.get("step_count", 0) or 0) + 1
    _ = mask_pii(job.get("description", ""))
    return state
