"""Bid graph: one thread per job. Parallel analysis, bounded critique, approval gate."""
from __future__ import annotations

from typing import Any
import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

try:
    from langgraph.checkpoint.postgres import PostgresSaver
    _HAS_POSTGRES = True
except ImportError:
    _HAS_POSTGRES = False

from agent.state import GigBidState
from agent.nodes import scout, analyst, risk_assessor, fit_matcher, pricing, writer, critic, compliance


def _decision_node(state: GigBidState) -> GigBidState:
    risk = state.get("risk_report", {}) or {}
    fit = state.get("fit_report", {}) or {}
    price = state.get("price_quote", {}) or {}
    decision = "skip"
    if risk.get("scam"):
        decision = "skip"
    elif price.get("worth_it"):
        decision = "bid"
    elif float(fit.get("score", 0)) >= 0.6 and not risk.get("scam"):
        decision = "watch"
    state["decision"] = decision
    return state


def _approval_gate(state: GigBidState) -> GigBidState:
    payload = {
        "job": state.get("job"),
        "decision": state.get("decision"),
        "price": state.get("price_quote"),
        "proposal": state.get("proposal_draft"),
        "risk": state.get("risk_report"),
        "fit": state.get("fit_report"),
        "verification": state.get("claim_verification"),
        "compliance": state.get("compliance_verdict"),
        "critique": state.get("critique"),
    }
    state["approval_payload"] = payload
    decision = interrupt({
        "action": "approve_proposal",
        "payload": payload,
        "message": "Review and approve, edit, or reject this proposal.",
    })
    state["approval_status"] = decision.get("action", "rejected") if isinstance(decision, dict) else str(decision)
    return state


def _get_checkpointer():
    """Get Postgres checkpointer if DATABASE_URL is set, else MemorySaver."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url and _HAS_POSTGRES:
        return PostgresSaver.from_conn_string(db_url)
    return MemorySaver()


def build_bid_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = _get_checkpointer()
    builder = StateGraph(GigBidState)
    builder.add_node("scout", scout.scout_node)
    builder.add_node("analyst", analyst.analyst_node)
    builder.add_node("risk_assessor", risk_assessor.risk_assessor_node)
    builder.add_node("fit_matcher", fit_matcher.fit_matcher_node)
    builder.add_node("decision", _decision_node)
    builder.add_node("pricing", pricing.pricing_node)
    builder.add_node("writer", writer.writer_node)
    builder.add_node("critic", critic.critic_node)
    builder.add_node("compliance", compliance.compliance_node)
    builder.add_node("approval_gate", _approval_gate)
    builder.add_edge(START, "scout")
    builder.add_edge("scout", "analyst")
    builder.add_edge("scout", "risk_assessor")
    builder.add_edge("scout", "fit_matcher")
    builder.add_edge("analyst", "decision")
    builder.add_edge("risk_assessor", "decision")
    builder.add_edge("fit_matcher", "decision")
    builder.add_edge("decision", "pricing")
    builder.add_edge("pricing", "writer")
    builder.add_edge("writer", "critic")
    builder.add_edge("critic", "compliance")
    builder.add_edge("compliance", "approval_gate")
    builder.add_edge("approval_gate", END)
    return builder.compile(checkpointer=checkpointer)


def run_bid(job: dict[str, Any], user_id: str = "default",
            saved_searches: list[str] | None = None, thread_id: str | None = None):
    import uuid
    graph = build_bid_graph()
    if thread_id is None:
        thread_id = f"bid-{uuid.uuid4().hex[:8]}"
    state: GigBidState = {
        "thread_id": thread_id, "mode": "bid", "user_id": user_id,
        "job": job, "saved_searches": saved_searches or [""],
        "step_count": 0, "token_budget": 12000, "errors": [],
        "trace_id": f"trace-{uuid.uuid4().hex[:8]}", "tool_calls": [],
    }
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(state, config=config)
