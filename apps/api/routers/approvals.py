"""Human-in-the-loop approval resume router (R4 / C5)."""
from __future__ import annotations

from fastapi import APIRouter, Header
from langgraph.types import Command

from agent.graphs.bid_graph import build_bid_graph
from apps.api.auth.tokens import get_user_id_from_header
from apps.api.routers.jobs import PIPELINE_CARDS, RUN_RECORDS
from apps.api.schemas.api import ApproveRequest

router = APIRouter(prefix="/api", tags=["approvals"])


@router.post("/approvals/respond")
async def approvals_respond(req: ApproveRequest, authorization: str | None = Header(None)):
    _ = get_user_id_from_header(authorization)
    graph = build_bid_graph()
    resume_data: dict = {"action": req.action}
    if req.edit:
        resume_data["edit"] = req.edit
    if req.reason:
        resume_data["reason"] = req.reason

    res = graph.invoke(
        Command(resume=resume_data),
        config={"configurable": {"thread_id": req.thread_id}},
    )
    clean = {k: v for k, v in res.items() if k != "__interrupt__"}
    if req.thread_id in RUN_RECORDS:
        RUN_RECORDS[req.thread_id]["status"] = f"resolved ({req.action})"
        RUN_RECORDS[req.thread_id]["result"] = clean
    for card in PIPELINE_CARDS.values():
        if card.get("thread_id") == req.thread_id:
            card["status"] = "submitted" if req.action in {"approved", "edited"} else "lost"
    return {"status": "ok", "thread_id": req.thread_id, "approval_status": res.get("approval_status"), "result": clean}
