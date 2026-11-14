"""Conversation graph: one thread per client conversation. Approval gate."""
from __future__ import annotations

import uuid
from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from agent.state import GigBidState
from agent.nodes import client_liaison


def _approve_message(state: GigBidState) -> GigBidState:
    payload = {
        "client_message": state.get("client_message"),
        "intent": state.get("intent"),
        "reply_draft": state.get("reply_draft"),
    }
    state["approval_payload"] = payload
    decision = interrupt({
        "action": "approve_message",
        "payload": payload,
        "message": "Review and approve, edit, or reject this client reply.",
    })
    state["approval_status"] = decision.get("action", "rejected") if isinstance(decision, dict) else str(decision)
    return state


def build_conversation_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()
    builder = StateGraph(GigBidState)
    builder.add_node("client_liaison", client_liaison.client_liaison_node)
    builder.add_node("approve_message", _approve_message)
    builder.add_edge(START, "client_liaison")
    builder.add_edge("client_liaison", "approve_message")
    builder.add_edge("approve_message", END)
    return builder.compile(checkpointer=checkpointer)


def run_conversation(message: dict[str, Any], user_id: str = "default",
                     thread_id: str | None = None):
    graph = build_conversation_graph()
    if thread_id is None:
        thread_id = f"conv-{uuid.uuid4().hex[:8]}"
    state: GigBidState = {
        "thread_id": thread_id, "mode": "conversation", "user_id": user_id,
        "client_message": message, "step_count": 0, "token_budget": 6000,
        "errors": [], "trace_id": f"trace-{uuid.uuid4().hex[:8]}", "tool_calls": [],
    }
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(state, config=config)
