"""Conversation graph: one thread per client conversation with interrupt() approval gate."""
from __future__ import annotations

import os
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

try:
    from langgraph.checkpoint.postgres import PostgresSaver
    _HAS_POSTGRES = True
except ImportError:
    _HAS_POSTGRES = False

from agent.nodes import client_liaison
from agent.state import GigBidState

_DEFAULT_CHECKPOINTER = MemorySaver()


def get_checkpointer():
    db_url = os.environ.get("DATABASE_URL")
    if db_url and _HAS_POSTGRES:
        return PostgresSaver.from_conn_string(db_url)
    return _DEFAULT_CHECKPOINTER


def _approve_message(state: GigBidState) -> GigBidState:
    msg = state.get("client_message", {}) or {}
    draft = state.get("reply_draft", {}) or {}
    user_id = state.get("user_id", "default")
    thread_id = state.get("thread_id", "conv")
    trace_id = state.get("trace_id", "trace")

    payload = {
        "client_message": msg,
        "intent": state.get("intent"),
        "reply_draft": draft,
    }
    decision = interrupt({
        "action": "approve_message",
        "payload": payload,
        "message": "Review and approve, edit, or reject this client reply.",
    })
    action = decision.get("action", "rejected") if isinstance(decision, dict) else str(decision)
    body = draft.get("body", "")
    if action == "edited" and isinstance(decision, dict):
        body = (decision.get("edit") or {}).get("body") or body

    if action in {"approved", "edited"}:
        from mcp_servers.marketplace.server import invoke_tool_sync

        res = invoke_tool_sync(
            "send_message",
            {
                "client_id": msg.get("client_id", "unknown"),
                "body": body,
                "idempotency_key": f"msg-{thread_id}",
                "dry_run": False,
                "user_id": user_id,
                "trace_id": trace_id,
            },
        )
        return {"approval_payload": payload, "approval_status": action, "outcome": res}

    return {"approval_payload": payload, "approval_status": "rejected"}


def build_conversation_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = get_checkpointer()
    builder = StateGraph(GigBidState)
    builder.add_node("client_liaison", client_liaison.client_liaison_node)
    builder.add_node("approve_message", _approve_message)
    builder.add_edge(START, "client_liaison")
    builder.add_edge("client_liaison", "approve_message")
    builder.add_edge("approve_message", END)
    return builder.compile(checkpointer=checkpointer)


def run_conversation(
    message: dict[str, Any],
    user_id: str = "default",
    thread_id: str | None = None,
    checkpointer=None,
) -> dict[str, Any]:
    graph = build_conversation_graph(checkpointer=checkpointer)
    if thread_id is None:
        thread_id = f"conv-{uuid.uuid4().hex[:8]}"
    state: GigBidState = {
        "thread_id": thread_id,
        "mode": "conversation",
        "user_id": user_id,
        "client_message": message,
        "step_count": 0,
        "token_budget": 6000,
        "errors": [],
        "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
        "tool_calls": [],
    }
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(state, config=config)
