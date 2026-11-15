"""Integration tests for Part C: Bid Graph, Conversation Graph, interrupt/resume, budget guard, and replay."""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agent.graphs.bid_graph import build_bid_graph, replay_from_node, run_bid
from agent.graphs.conversation_graph import build_conversation_graph, run_conversation


def _sample_good_job() -> dict:
    return {
        "job_id": "int-good-001",
        "persona": "ai_ml_engineer",
        "title": "Build Multi-Agent LangGraph RAG Pipeline with FastAPI",
        "description": "Need an AI engineer with Python, LangGraph, FastAPI, ChromaDB, and pytest to build a production RAG system.",
        "required_skills": ["Python", "LangGraph", "FastAPI", "ChromaDB"],
        "budget": {"min": 800, "max": 2500, "currency": "USD"},
        "connects_cost": 6,
        "client_id": "client-001",
        "warning_signals": [],
    }


def test_scam_job_routes_to_skip_without_interrupt():
    cp = MemorySaver()
    scam_job = {
        "job_id": "int-scam-001",
        "title": "Free unpaid test project via Telegram",
        "description": "Unpaid test project first. Message me on Telegram @fake.",
        "required_skills": ["Python"],
        "budget": {"min": 0, "max": 0},
        "connects_cost": 4,
        "warning_signals": ["unpaid_work"],
    }
    res = run_bid(scam_job, user_id="u-scam", thread_id="t-scam-1", checkpointer=cp)
    assert res["decision"] == "skip"
    assert res["risk_report"]["scam"] is True
    assert "__interrupt__" not in res


def test_bid_graph_parallel_fanout_interrupt_and_resume_approve():
    cp = MemorySaver()
    tid = "t-approve-1"
    res = run_bid(_sample_good_job(), user_id="u-int", thread_id=tid, checkpointer=cp)
    assert res["decision"] in {"bid", "watch"}
    assert "job_spec" in res and "risk_report" in res and "fit_report" in res
    assert "__interrupt__" in res

    graph = build_bid_graph(checkpointer=cp)
    resumed = graph.invoke(Command(resume={"action": "approved"}), config={"configurable": {"thread_id": tid}})
    assert resumed["approval_status"] == "approved"
    assert resumed["outcome"].get("proposal_id") or resumed["outcome"].get("submitted") is True


def test_bid_graph_edit_blocked_if_human_adds_off_platform_contact():
    cp = MemorySaver()
    tid = "t-edit-block-1"
    run_bid(_sample_good_job(), user_id="u-int", thread_id=tid, checkpointer=cp)
    graph = build_bid_graph(checkpointer=cp)
    resumed = graph.invoke(
        Command(resume={"action": "edited", "edit": {"cover_letter": "Email me at hacker@evil.com or Telegram @me"}}),
        config={"configurable": {"thread_id": tid}},
    )
    assert resumed["approval_status"] == "blocked_by_compliance"
    assert resumed["compliance_verdict"]["passed"] is False


def test_budget_guard_moves_thread_to_needs_attention():
    cp = MemorySaver()
    graph = build_bid_graph(checkpointer=cp)
    tid = "t-budget-1"
    state = {
        "thread_id": tid,
        "mode": "bid",
        "user_id": "u-budget",
        "job": _sample_good_job(),
        "step_count": 99,  # exceeds max_graph_steps=30
        "token_budget": 0,
        "errors": [],
        "trace_id": "trace-budget",
        "tool_calls": [],
    }
    res = graph.invoke(state, config={"configurable": {"thread_id": tid}})
    assert res.get("needs_attention") is True
    assert res.get("approval_status") == "needs_attention"


def test_crash_resume_replay_from_writer():
    cp = MemorySaver()
    tid = "t-replay-1"
    run_bid(_sample_good_job(), user_id="u-rep", thread_id=tid, checkpointer=cp)
    replayed = replay_from_node(tid, as_node="writer", checkpointer=cp)
    assert "__interrupt__" in replayed or "proposal_draft" in replayed


def test_conversation_graph_interrupt_and_resume():
    cp = MemorySaver()
    tid = "t-conv-1"
    res = run_conversation(
        {"client_id": "client-001", "body": "Can we schedule a 20-minute call tomorrow to discuss milestones?"},
        user_id="u-conv",
        thread_id=tid,
        checkpointer=cp,
    )
    assert "__interrupt__" in res
    assert res["intent"] == "interview_request"

    graph = build_conversation_graph(checkpointer=cp)
    resumed = graph.invoke(Command(resume={"action": "approved"}), config={"configurable": {"thread_id": tid}})
    assert resumed["approval_status"] == "approved"
    assert resumed["outcome"].get("message_id") or resumed["outcome"].get("sent") is True
