"""Jobs, analysis, and pipeline state router."""
from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Header, HTTPException

from agent.graphs.bid_graph import run_bid
from agent.marketplace_port import build_port
from agent.mcp_client import is_marketplace_degraded, set_marketplace_degraded
from apps.api.auth.tokens import get_user_id_from_header
from apps.api.schemas.api import AnalyzeJobRequest

router = APIRouter(prefix="/api", tags=["jobs"])

RUN_RECORDS: dict[str, dict[str, Any]] = {}
PIPELINE_CARDS: dict[str, dict[str, Any]] = {}


def _serialize_result(res: dict[str, Any], thread_id: str) -> dict[str, Any]:
    interrupted = bool(res.get("__interrupt__"))
    clean = {k: v for k, v in res.items() if k != "__interrupt__"}
    return {
        "status": "interrupted" if interrupted else "ok",
        "needs_approval": interrupted,
        "thread_id": thread_id,
        "result": clean,
    }


@router.get("/jobs/search")
async def search_jobs(q: str = "", limit: int = 20, authorization: str | None = Header(None)):
    if is_marketplace_degraded():
        return {"jobs": [], "degraded": True, "error": "Marketplace unavailable — queued for retry."}
    uid = get_user_id_from_header(authorization)
    port = build_port(user_id=uid)
    jobs = port.search_jobs(query=q, limit=limit)
    return {"jobs": [j.__dict__ for j in jobs], "degraded": False}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, authorization: str | None = Header(None)):
    if is_marketplace_degraded():
        raise HTTPException(status_code=503, detail="Marketplace unavailable")
    port = build_port()
    job = port.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.__dict__


@router.post("/jobs/analyze")
async def analyze_job(req: AnalyzeJobRequest, authorization: str | None = Header(None)):
    uid = req.user_id or get_user_id_from_header(authorization)
    thread_id = f"thread-{uuid.uuid4().hex[:8]}"
    res = run_bid(job=req.job, user_id=uid, saved_searches=req.saved_searches, thread_id=thread_id)
    payload = _serialize_result(res, thread_id)
    RUN_RECORDS[thread_id] = {
        "thread_id": thread_id,
        "job_id": req.job.get("job_id", ""),
        "title": req.job.get("title", ""),
        "status": "awaiting_approval" if payload["needs_approval"] else f"completed ({res.get('decision', 'skip')})",
        "trace_id": res.get("trace_id"),
        "result": payload["result"],
    }
    jid = req.job.get("job_id") or thread_id
    PIPELINE_CARDS[jid] = {
        "id": jid,
        "thread_id": thread_id,
        "title": req.job.get("title", "Untitled Job"),
        "status": "drafted" if payload["needs_approval"] else ("lost" if res.get("decision") == "skip" else "drafted"),
        "decision": res.get("decision"),
        "fit_score": (res.get("fit_report") or {}).get("score", 0.0),
    }
    return payload


@router.get("/pipeline")
async def get_pipeline():
    return {"cards": list(PIPELINE_CARDS.values())}


@router.post("/marketplace/degraded")
async def toggle_degraded(flag: bool = True):
    set_marketplace_degraded(flag)
    return {"degraded": is_marketplace_degraded()}
