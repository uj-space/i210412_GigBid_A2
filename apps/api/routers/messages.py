"""Client messages & ConversationGraph router."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Header
from langgraph.types import Command

from agent.graphs.conversation_graph import build_conversation_graph, run_conversation
from agent.marketplace_port import build_port
from apps.api.auth.tokens import get_user_id_from_header
from apps.api.schemas.api import ApproveRequest, MessageRequest

router = APIRouter(prefix="/api", tags=["messages"])


@router.get("/messages")
async def list_messages(limit: int = 50):
    port = build_port()
    return {"messages": port.list_messages(limit=limit)}


@router.post("/messages/respond")
async def messages_respond(req: MessageRequest, authorization: str | None = Header(None)):
    uid = req.user_id or get_user_id_from_header(authorization)
    tid = req.thread_id or f"conv-{uuid.uuid4().hex[:8]}"
    res = run_conversation(message=req.client_message, user_id=uid, thread_id=tid)
    interrupted = bool(res.get("__interrupt__"))
    clean = {k: v for k, v in res.items() if k != "__interrupt__"}
    return {"status": "interrupted" if interrupted else "ok", "needs_approval": interrupted, "thread_id": tid, "result": clean}


@router.post("/messages/approve")
async def approve_message(req: ApproveRequest):
    graph = build_conversation_graph()
    resume_data = {"action": req.action}
    if req.edit:
        resume_data["edit"] = req.edit
    res = graph.invoke(Command(resume=resume_data), config={"configurable": {"thread_id": req.thread_id}})
    clean = {k: v for k, v in res.items() if k != "__interrupt__"}
    return {"status": "ok", "thread_id": req.thread_id, "result": clean}
