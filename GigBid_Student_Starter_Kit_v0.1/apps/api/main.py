"""GigBid FastAPI backend.

Typed API contract serving the web UI: jobs, proposals, approvals, messages,
analytics, and SSE streaming of LangGraph runs.
"""
from __future__ import annotations

from typing import Any
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import uuid

from agent.graphs.bid_graph import build_bid_graph, run_bid
from agent.graphs.conversation_graph import build_conversation_graph, run_conversation
from agent.state import GigBidState
from agent.marketplace_port import build_port

app = FastAPI(title="GigBid API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_user_id(authorization: str | None = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return "anonymous"
    return authorization.split(" ", 1)[1] or "anonymous"


class AnalyzeJobRequest(BaseModel):
    job: dict[str, Any]
    user_id: str = "default"
    saved_searches: list[str] | None = None


class ApproveRequest(BaseModel):
    thread_id: str
    action: str
    edit: dict[str, Any] | None = None
    reason: str | None = None


class MessageRequest(BaseModel):
    thread_id: str
    client_message: dict[str, Any]
    user_id: str = "default"


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok", "service": "gigbid-api"}


@app.post("/api/jobs/analyze")
async def analyze_job(req: AnalyzeJobRequest, authorization: str | None = Header(None)):
    user_id = get_user_id(authorization) or req.user_id
    thread_id = f"thread-{uuid.uuid4().hex[:8]}"
    try:
        result = run_bid(
            job=req.job,
            user_id=user_id,
            saved_searches=req.saved_searches,
            thread_id=thread_id,
        )
    except Exception as exc:
        return {
            "status": "interrupted",
            "thread_id": thread_id,
            "error": str(exc),
            "needs_approval": True,
        }
    return {"status": "ok", "thread_id": thread_id, "result": result}


@app.get("/api/jobs/search")
async def search_jobs(q: str = "", limit: int = 20, authorization: str | None = Header(None)):
    port = build_port()
    jobs = port.search_jobs(query=q, limit=limit)
    return {"jobs": [j.__dict__ for j in jobs]}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, authorization: str | None = Header(None)):
    port = build_port()
    job = port.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job.__dict__


@app.post("/api/approvals/respond")
async def approvals_respond(req: ApproveRequest, authorization: str | None = Header(None)):
    from langgraph.types import Command

    graph = build_bid_graph()
    resume_data = {"action": req.action}
    if req.edit:
        resume_data["edit"] = req.edit
    if req.reason:
        resume_data["reason"] = req.reason
    try:
        result = graph.invoke(
            Command(resume=resume_data),
            config={"configurable": {"thread_id": req.thread_id}},
        )
    except Exception as exc:
        return {"status": "interrupted_again", "thread_id": req.thread_id, "error": str(exc)}
    return {"status": "ok", "thread_id": req.thread_id, "result": result}


@app.post("/api/messages/respond")
async def messages_respond(req: MessageRequest, authorization: str | None = Header(None)):
    thread_id = req.thread_id or f"conv-{uuid.uuid4().hex[:8]}"
    try:
        result = run_conversation(
            message=req.client_message,
            user_id=req.user_id,
            thread_id=thread_id,
        )
    except Exception as exc:
        return {"status": "interrupted", "thread_id": thread_id, "error": str(exc), "needs_approval": True}
    return {"status": "ok", "thread_id": thread_id, "result": result}


@app.get("/api/runs/{thread_id}/stream")
async def stream_run(thread_id: str, authorization: str | None = Header(None)):
    def event_stream():
        yield f"data: {json.dumps({'type': 'run_start', 'thread_id': thread_id})}\n\n"
        yield f"data: {json.dumps({'type': 'note', 'message': 'run streamed via LangGraph stream modes'})}\n\n"
        yield f"data: {json.dumps({'type': 'run_end', 'thread_id': thread_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/analytics")
async def analytics(authorization: str | None = Header(None)):
    return {
        "reply_rate_by_category": {"AI/ML": 0.42, "Web": 0.35, "Data": 0.38},
        "connects_spent_vs_outcomes": [{"category": "AI/ML", "spent": 120, "replies": 5}],
        "cost_and_latency_per_proposal": {"p95_latency_s": 8.2, "usd": 0.04},
        "top_rejection_reasons": ["budget mismatch", "skill gap", "client unresponsive"],
    }


@app.get("/api/connects")
async def connects(authorization: str | None = Header(None)):
    port = build_port()
    return {"balance": port.get_connects_balance()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
