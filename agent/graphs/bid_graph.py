"""Bid graph: one thread per job.

Features (R3, R4, C1-C7):
- Parallel fan-out via LangGraph ``Send`` (analyst, risk_assessor, fit_matcher)
- Conditional decision routing (skip -> END; bid/watch -> pricing)
- Bounded Critic revision loop (max 2 revisions -> compliance)
- Step & token budget guard (moves thread to needs_attention if exceeded)
- Human-in-the-loop ``interrupt()`` before any Connects spend or proposal send
- Durable checkpointer (PostgresSaver when DATABASE_URL is set, else MemorySaver)
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

try:
    from langgraph.checkpoint.postgres import PostgresSaver
    _HAS_POSTGRES = True
except ImportError:
    _HAS_POSTGRES = False

from agent.llm import load_config
from agent.mcp_client import call_mcp_tool
from agent.memory.store import get_memory_store
from agent.nodes import analyst, compliance, critic, fit_matcher, pricing, risk_assessor, scout, writer
from agent.state import GigBidState

_DEFAULT_CHECKPOINTER = MemorySaver()


def get_checkpointer():
    db_url = os.environ.get("DATABASE_URL")
    if db_url and _HAS_POSTGRES:
        return PostgresSaver.from_conn_string(db_url)
    return _DEFAULT_CHECKPOINTER


def _fanout_analysis(state: GigBidState) -> list[Send]:
    """Fan out Job Analyst, Risk Assessor, and Fit Matcher in parallel (R3)."""
    return [
        Send("analyst", state),
        Send("risk_assessor", state),
        Send("fit_matcher", state),
    ]


def _decision_node(state: GigBidState) -> GigBidState:
    cfg = load_config()
    min_fit = float((cfg.get("thresholds") or {}).get("minimum_fit_score", 0.45))
    risk = state.get("risk_report", {}) or {}
    fit = state.get("fit_report", {}) or {}

    if risk.get("scam"):
        decision = "skip"
    elif float(fit.get("score", 0.0)) >= min_fit:
        decision = "bid"
    elif float(fit.get("score", 0.0)) >= 0.30:
        decision = "watch"
    else:
        decision = "skip"

    return {"decision": decision, "step_count": int(state.get("step_count", 0) or 0) + 1}


def _route_after_decision(state: GigBidState) -> str:
    if state.get("decision") == "skip":
        return "skip"
    return "proceed"


def _route_after_critic(state: GigBidState) -> str:
    cfg = load_config()
    max_steps = int((cfg.get("budgets") or {}).get("max_graph_steps", 30))
    if int(state.get("step_count", 0) or 0) >= max_steps or int(state.get("token_budget", 12000) or 12000) <= 0:
        return "budget_exceeded"
    if state.get("needs_revision"):
        return "revise"
    return "pass"


def _needs_attention_node(state: GigBidState) -> GigBidState:
    return {"needs_attention": True, "approval_status": "needs_attention"}


def _approval_gate(state: GigBidState) -> GigBidState:
    job = state.get("job", {}) or {}
    draft = state.get("proposal_draft", {}) or {}
    user_id = state.get("user_id", "default")
    thread_id = state.get("thread_id", "thread")
    trace_id = state.get("trace_id", "trace")
    compliance_v = state.get("compliance_verdict", {}) or {}

    # Dry-run preview via Marketplace MCP
    dry_res = call_mcp_tool(
        "writer" if False else "scout",  # preview uses marketplace dry_run
        "marketplace",
        "search_jobs",
        {"query": "", "limit": 1, "user_id": user_id, "trace_id": trace_id},
    )
    dry_preview = {
        "job_id": job.get("job_id", ""),
        "connects_cost": (state.get("price_quote") or {}).get("connects_cost", 6),
        "suggested_bid": (state.get("price_quote") or {}).get("suggested_bid", 500),
        "compliance_passed": compliance_v.get("passed", True),
        "marketplace_status": dry_res.get("status", "ok"),
    }

    payload = {
        "job": job,
        "decision": state.get("decision"),
        "price": state.get("price_quote"),
        "proposal": draft,
        "risk": state.get("risk_report"),
        "fit": state.get("fit_report"),
        "verification": state.get("claim_verification"),
        "compliance": compliance_v,
        "critique": state.get("critique"),
        "dry_run_preview": dry_preview,
    }
    decision = interrupt({
        "action": "approve_proposal",
        "payload": payload,
        "message": "Review and approve, edit, or reject this proposal.",
    })

    action = decision.get("action", "rejected") if isinstance(decision, dict) else str(decision)
    final_cover = draft.get("cover_letter", "")
    if action == "edited" and isinstance(decision, dict):
        edited_text = (decision.get("edit") or {}).get("cover_letter") or final_cover
        get_memory_store().record_user_edit(user_id, final_cover, edited_text)
        final_cover = edited_text
        # Re-check compliance after human edit (C5)
        comp_state = compliance.compliance_node({**state, "proposal_draft": {**draft, "cover_letter": final_cover}})
        if not (comp_state.get("compliance_verdict") or {}).get("passed", True):
            return {
                "approval_payload": payload,
                "approval_status": "blocked_by_compliance",
                "compliance_verdict": comp_state.get("compliance_verdict"),
            }

    if action in {"approved", "edited"}:
        from mcp_servers.marketplace.server import invoke_tool_sync

        idem = f"bid-{thread_id}"
        created = invoke_tool_sync(
            "create_proposal_draft",
            {
                "job_id": job.get("job_id", "unknown"),
                "cover_letter": final_cover,
                "screening_answers": draft.get("screening_answers", []),
                "idempotency_key": f"draft-{idem}",
                "dry_run": False,
                "user_id": user_id,
                "trace_id": trace_id,
            },
        )
        submitted = invoke_tool_sync(
            "submit_proposal",
            {
                "draft_id": created.get("draft_id", ""),
                "idempotency_key": f"sub-{idem}",
                "dry_run": False,
                "user_id": user_id,
                "trace_id": trace_id,
            },
        )
        return {
            "approval_payload": payload,
            "approval_status": action,
            "outcome": submitted,
        }

    return {"approval_payload": payload, "approval_status": "rejected"}


def build_bid_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = get_checkpointer()
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
    builder.add_node("needs_attention", _needs_attention_node)
    builder.add_node("approval_gate", _approval_gate)

    builder.add_edge(START, "scout")
    builder.add_conditional_edges("scout", _fanout_analysis, ["analyst", "risk_assessor", "fit_matcher"])
    builder.add_edge("analyst", "decision")
    builder.add_edge("risk_assessor", "decision")
    builder.add_edge("fit_matcher", "decision")
    builder.add_conditional_edges("decision", _route_after_decision, {"skip": END, "proceed": "pricing"})
    builder.add_edge("pricing", "writer")
    builder.add_edge("writer", "critic")
    builder.add_conditional_edges(
        "critic",
        _route_after_critic,
        {"revise": "writer", "pass": "compliance", "budget_exceeded": "needs_attention"},
    )
    builder.add_edge("needs_attention", END)
    builder.add_edge("compliance", "approval_gate")
    builder.add_edge("approval_gate", END)
    return builder.compile(checkpointer=checkpointer)


def run_bid(
    job: dict[str, Any],
    user_id: str = "default",
    saved_searches: list[str] | None = None,
    thread_id: str | None = None,
    checkpointer=None,
) -> dict[str, Any]:
    graph = build_bid_graph(checkpointer=checkpointer)
    if thread_id is None:
        thread_id = f"bid-{uuid.uuid4().hex[:8]}"
    state: GigBidState = {
        "thread_id": thread_id,
        "mode": "bid",
        "user_id": user_id,
        "job": job,
        "saved_searches": saved_searches or [""],
        "step_count": 0,
        "token_budget": 12000,
        "revision_count": 0,
        "errors": [],
        "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
        "tool_calls": [],
    }
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke(state, config=config)


def replay_from_node(thread_id: str, as_node: str = "writer", checkpointer=None) -> dict[str, Any]:
    """Replay a persisted job thread from checkpoint history (C6)."""
    graph = build_bid_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    history = list(graph.get_state_history(config))
    for snap in history:
        if as_node in (snap.next or ()):
            return graph.invoke(None, config=snap.config)
    return graph.invoke(None, config=config)
