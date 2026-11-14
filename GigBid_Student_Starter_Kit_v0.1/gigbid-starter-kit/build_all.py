#!/usr/bin/env python3
"""Build script: generates the complete GigBid source tree from embedded strings.

Run: python build_all.py   (from gigbid-starter-kit/)
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FILES: dict[str, str] = {}

def w(rel: str, content: str) -> None:
    FILES[rel] = content

# =====================================================================
# 1. AGENT PACKAGE
# =====================================================================
w("agent/__init__.py", '''"""GigBid agent package: LangGraph multi-agent orchestrator for freelance job bidding."""\n''')

# ---- agent/state.py ---------------------------------------------------
w("agent/state.py", '''"""Typed LangGraph state for the GigBid bid and conversation graphs."""
from __future__ import annotations

from typing import Any, TypedDict, List


class GigBidState(TypedDict, total=False):
    # identity / routing
    thread_id: str
    mode: str  # "bid" | "conversation"
    user_id: str

    # job inputs
    saved_searches: List[str]
    new_jobs: List[dict]
    job: dict[str, Any]
    seen_job_fingerprints: List[str]

    # analysis outputs
    job_spec: dict[str, Any]
    risk_report: dict[str, Any]
    fit_report: dict[str, Any]
    evidence: List[dict[str, Any]]

    # decision / pricing
    decision: str  # skip | watch | bid
    price_quote: dict[str, Any]

    # proposal flow
    proposal_draft: dict[str, Any]
    claim_verification: List[dict[str, Any]]
    critique: dict[str, Any]
    compliance_verdict: dict[str, Any]
    revision_count: int
    approval_status: str  # pending | approved | edited | rejected
    approval_payload: dict[str, Any]

    # conversation flow
    messages: List[dict[str, Any]]
    client_message: dict[str, Any]
    intent: str
    reply_draft: dict[str, Any]

    # outcomes / memory
    outcome: dict[str, Any]
    style_memory: List[dict[str, Any]]
    outcome_memory: List[dict[str, Any]]

    # control
    errors: List[str]
    step_count: int
    token_budget: int
    needs_attention: bool

    # traces / audit
    trace_id: str
    tool_calls: List[dict[str, Any]]
''')

# ---- agent/handoffs.py ------------------------------------------------
w("agent/handoffs.py", '''"""Typed Pydantic hand-off objects exchanged between agents (C3)."""
from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_id: str
    title: str
    deliverables: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: str = "USD"
    duration_days: Optional[int] = None
    screening_questions: List[str] = Field(default_factory=list)
    hidden_needs: List[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class RiskReport(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    flags: List[str] = Field(default_factory=list)
    explanation: str
    scam: bool = False
    unpaid_work: bool = False
    off_platform: bool = False
    injection: bool = False


class FitReport(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    requirement_matrix: List[dict[str, Any]] = Field(default_factory=list)
    reasons: str = ""


class BidDecision(BaseModel):
    decision: str  # skip | watch | bid
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    autonomy_override: bool = False


class PriceQuote(BaseModel):
    job_id: str
    suggested_bid: float
    currency: str = "USD"
    connects_cost: int
    worth_it: bool
    floor: Optional[float] = None
    rationale: str = ""


class ProposalDraft(BaseModel):
    job_id: str
    cover_letter: str
    screening_answers: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    status: str = "pending_review"
    claim_citations: List[dict[str, Any]] = Field(default_factory=list)


class Critique(BaseModel):
    grounded: bool
    unsupported_claims: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    length_ok: bool
    personalised: bool
    revision_count: int = 0


class ComplianceVerdict(BaseModel):
    passed: bool
    violations: List[str] = Field(default_factory=list)
    reason: str = ""
    redacted: bool = False
''')

# ---- agent/nodes/analyst.py -------------------------------------------
w("agent/nodes/analyst.py", '''"""Job Analyst node: extract a structured JobSpec from a job post."""
from __future__ import annotations

from typing import Any
from agent.state import GigBidState
from agent.handoffs import JobSpec


def analyst_node(state: GigBidState) -> GigBidState:
    job = state.get("job", {}) or {}
    spec = JobSpec(
        job_id=job.get("job_id", ""),
        title=job.get("title", ""),
        deliverables=_extract_deliverables(job.get("description", "")),
        required_skills=list(job.get("required_skills", []) or []),
        budget_min=job.get("budget_min"),
        budget_max=job.get("budget_max"),
        currency=job.get("currency", "USD"),
        duration_days=job.get("duration_days"),
        screening_questions=list(job.get("screening_questions", []) or []),
        hidden_needs=_infer_hidden_needs(job.get("description", "")),
        raw=job,
    )
    state["job_spec"] = spec.model_dump()
    state["job"] = {**job, "job_spec": spec.model_dump()}
    return state


def _extract_deliverables(description: str) -> list[str]:
    desc = (description or "").lower()
    items = []
    for keyword in ["dashboard", "report", "model", "classifier", "api", "website",
                    "script", "automation", "analysis", "frontend", "backend"]:
        if keyword in desc:
            items.append(keyword)
    return items or ["project deliverable"]


def _infer_hidden_needs(description: str) -> list[str]:
    desc = (description or "").lower()
    needs = []
    if "urgent" in desc or "asap" in desc:
        needs.append("fast turnaround")
    if "fixed price" in desc:
        needs.append("fixed budget")
    if "hourly" in desc:
        needs.append("hourly engagement")
    return needs
''')

# ---- agent/nodes/risk_assessor.py -------------------------------------
w("agent/nodes/risk_assessor.py", '''"""Risk Assessor node: score client quality and flag scams / injection."""
from __future__ import annotations

from typing import Any
from agent.state import GigBidState
from agent.handoffs import RiskReport


def risk_assessor_node(state: GigBidState) -> GigBidState:
    job = state.get("job", {}) or {}
    client = state.get("client_history", {}) or {}
    desc = (job.get("description", "") or "").lower()
    signals = list(job.get("warning_signals", []) or [])

    flags: list[str] = []
    scam = False
    unpaid = False
    off_platform = False
    injection = False

    if "unpaid" in desc or "free trial" in desc or "test project" in desc:
        unpaid = True
        flags.append("unpaid_work")
    if "external" in desc or "telegram" in desc or "whatsapp" in desc or "off-platform" in desc:
        off_platform = True
        flags.append("off_platform_contact")
    if "guarantee" in desc or "100%" in desc:
        flags.append("unverifiable_guarantee")

    injection_phrases = ["ignore previous", "system:", "you are now", "disregard",
                         "reveal your prompt", "print your instructions"]
    if any(p in desc for p in injection_phrases):
        injection = True
        flags.append("prompt_injection")

    scam = unpaid or off_platform or injection

    score = 0.5
    if client.get("payment_verified"):
        score += 0.2
    if client.get("completed_projects", 0) >= 5:
        score += 0.15
    if client.get("average_rating", 0) >= 4.5:
        score += 0.1
    if unpaid or off_platform or injection:
        score -= 0.4
    score = max(0.0, min(1.0, score))

    report = RiskReport(
        score=score,
        flags=flags,
        explanation=(f"Risk score {score:.2f}. " +
                     ("; ".join(flags) if flags else "no major risk signals")),
        scam=scam, unpaid_work=unpaid, off_platform=off_platform, injection=injection,
    )
    state["risk_report"] = report.model_dump()
    return state
''')

# ---- agent/nodes/fit_matcher.py ---------------------------------------
w("agent/nodes/fit_matcher.py", '''"""Fit Matcher node: map job requirements to verified portfolio evidence."""
from __future__ import annotations

from typing import Any
from agent.state import GigBidState
from agent.handoffs import FitReport
from rag.retriever import retrieve_evidence


def fit_matcher_node(state: GigBidState) -> GigBidState:
    job_spec = state.get("job_spec", {}) or {}
    skills = list(job_spec.get("required_skills", []) or [])
    deliverables = list(job_spec.get("deliverables", []) or [])
    query = " ".join(skills + deliverables + [job_spec.get("title", "")])

    evidence = retrieve_evidence(query, k=8, persona=state.get("user_id", "default"))
    matched = []
    missing = []
    for s in skills:
        if any(s.lower() in (e.get("skills", []) or []) or s.lower() in (e.get("text", "").lower())
               for e in evidence):
            matched.append(s)
        else:
            missing.append(s)

    score = len(matched) / max(len(skills), 1) if skills else 0.5
    matrix = []
    for req in skills + deliverables:
        supporting = [e.get("evidence_id") or e.get("id") for e in evidence
                      if req.lower() in (e.get("text", "").lower()
                                         or " ".join(e.get("skills", [])).lower())]
        matrix.append({"requirement": req, "evidence_ids": supporting[:3]})

    report = FitReport(
        score=round(score, 3),
        matched_skills=matched,
        missing_skills=missing,
        evidence_ids=[e.get("evidence_id") or e.get("id") for e in evidence],
        requirement_matrix=matrix,
        reasons=f"Matched {len(matched)} of {max(len(skills),1)} required skills.",
    )
    state["fit_report"] = report.model_dump()
    state["evidence"] = evidence
    return state
''')

# ---- agent/nodes/pricing.py -------------------------------------------
w("agent/nodes/pricing.py", '''"""Pricing Strategist node: propose a bid and assess Connects value."""
from __future__ import annotations

from agent.state import GigBidState
from agent.handoffs import PriceQuote


def pricing_node(state: GigBidState) -> GigBidState:
    job = state.get("job", {}) or {}
    fit = state.get("fit_report", {}) or {}
    risk = state.get("risk_report", {}) or {}

    budget_min = job.get("budget_min") or 0
    budget_max = job.get("budget_max") or 0
    connects = int(job.get("connects_cost", 0))
    floor = float(state.get("floor_rate", 25.0))

    suggested = None
    worth_it = False
    rationale = ""

    if budget_max and budget_max >= floor:
        fit_score = float(fit.get("score", 0.5))
        risk_score = float(risk.get("score", 0.5))
        suggested = round(budget_max * (0.85 + 0.15 * fit_score) * (0.9 + 0.1 * risk_score), 2)
        suggested = max(suggested, floor)
        worth_it = (suggested >= floor) and (fit_score >= 0.5) and (risk_score >= 0.4)
        rationale = (f"Suggested {suggested} within budget {budget_min}-{budget_max}; "
                     f"fit {fit_score:.2f}, risk {risk_score:.2f}, connects {connects}.")
    else:
        suggested = floor
        worth_it = False
        rationale = "Budget below floor or missing; not worth bidding."

    state["price_quote"] = PriceQuote(
        job_id=job.get("job_id", ""),
        suggested_bid=suggested,
        currency=job.get("currency", "USD"),
        connects_cost=connects,
        worth_it=worth_it,
        floor=floor,
        rationale=rationale,
    ).model_dump()
    return state
''')

# ---- agent/nodes/writer.py --------------------------------------------
w("agent/nodes/writer.py", '''"""Proposal Writer node: draft a personalised proposal citing evidence only."""
from __future__ import annotations

from agent.state import GigBidState
from agent.handoffs import ProposalDraft
from rag.verify import verify_claims


def writer_node(state: GigBidState) -> GigBidState:
    job = state.get("job", {}) or {}
    job_spec = state.get("job_spec", {}) or {}
    fit = state.get("fit_report", {}) or {}
    price = state.get("price_quote", {}) or {}
    evidence = state.get("evidence", []) or []
    style_memory = state.get("style_memory", []) or []

    cover = _draft_cover_letter(job, job_spec, fit, price, evidence, style_memory)
    answers = _draft_screening_answers(job, evidence)

    draft = ProposalDraft(
        job_id=job.get("job_id", ""),
        cover_letter=cover,
        screening_answers=answers,
        evidence_ids=[e.get("evidence_id") or e.get("id") for e in evidence],
        status="pending_review",
        claim_citations=[{"claim": c, "evidence_id": e.get("evidence_id") or e.get("id")}
                         for c, e in zip(_split_claims(cover), evidence)],
    )
    state["proposal_draft"] = draft.model_dump()

    verification = verify_claims(cover, evidence)
    state["claim_verification"] = verification
    state["unsupported_claims"] = [v for v in verification if v.get("verdict") == "unsupported"]
    return state


def _draft_cover_letter(job, job_spec, fit, price, evidence, style_memory) -> str:
    title = job.get("title", "this project")
    skills = ", ".join(job_spec.get("required_skills", []) or [])
    matched = ", ".join(fit.get("matched_skills", []) or [])
    bids = price.get("suggested_bid", "N/A")
    cites = "; ".join(f"[{e.get('evidence_id') or e.get('id')}]" for e in evidence[:3]) or "[portfolio]"
    style = ""
    if style_memory:
        style = " " + " ".join(s.get("text", "") for s in style_memory[:3])
    return (
        f"Dear Client,\n\nI am writing to apply for \"{title}\". "
        f"My background in {skills} aligns with your requirements, and I have "
        f"demonstrated relevant work in {matched} {cites}. "
        f"I propose to deliver this project for {bids} and can start immediately. "
        f"I have successfully completed similar engagements and would welcome "
        f"the chance to discuss your goals in detail.{style}\n\nThank you."
    )


def _draft_screening_answers(job, evidence) -> list[str]:
    qs = list(job.get("screening_questions", []) or [])
    answers = []
    for q in qs:
        answers.append(
            f"I would approach this by clarifying your success criteria, then "
            f"delivering incremental work you can review at each stage."
        )
    return answers or ["I am available to discuss your project requirements."]


def _split_claims(text: str) -> list[str]:
    return [s.strip() for s in text.split(".") if s.strip()][:5]
''')

# ---- agent/nodes/critic.py --------------------------------------------
w("agent/nodes/critic.py", '''"""Critic node: review grounding/specificity/length; max two revisions (C4)."""
from __future__ import annotations

from agent.state import GigBidState
from agent.handoffs import Critique


def critic_node(state: GigBidState) -> GigBidState:
    draft = state.get("proposal_draft", {}) or {}
    verification = state.get("claim_verification", []) or []
    revision_count = int(state.get("revision_count", 0) or 0)

    unsupported = [v for v in verification if v.get("verdict") == "unsupported"]
    partly = [v for v in verification if v.get("verdict") == "partly_supported"]
    cover = draft.get("cover_letter", "")

    grounded = len(unsupported) == 0
    length_ok = 80 <= len(cover) <= 1200
    personalised = any(k in cover.lower() for k in ["dear client", "project", "deliver"])

    critique = Critique(
        grounded=grounded,
        unsupported_claims=[u.get("claim", "") for u in unsupported],
        suggestions=[],
        length_ok=length_ok,
        personalised=personalised,
        revision_count=revision_count,
    )
    if not length_ok:
        critique.suggestions.append("Adjust proposal length to 80-1200 characters.")
    if not personalised:
        critique.suggestions.append("Open with a client-specific reference.")
    if partly:
        critique.suggestions.append("Strengthen claims with more specific evidence.")

    state["critique"] = critique.model_dump()
    # bounded loop: send back at most twice
    if revision_count < 2 and (not grounded or not length_ok or not personalised):
        state["needs_revision"] = True
        state["revision_count"] = revision_count + 1
    else:
        state["needs_revision"] = False
        state["critique_complete"] = True
    return state
''')

# ---- agent/nodes/compliance.py ----------------------------------------
w("agent/nodes/compliance.py", '''"""Compliance Guard: enforce policy pack; block with reason shown in UI."""
from __future__ import annotations

from agent.state import GigBidState
from agent.handoffs import ComplianceVerdict


def compliance_node(state: GigBidState) -> GigBidState:
    draft = state.get("proposal_draft", {}) or {}
    cover = draft.get("cover_letter", "")
    answers = draft.get("screening_answers", []) or []
    text = cover + " " + " ".join(answers)

    violations: list[str] = []
    redacted = False
    lowered = text.lower()

    banned_phrases = ["guarantee", "100% refund", "pay me outside", "telegram",
                      "whatsapp", "contact me directly", "off-platform"]
    for phrase in banned_phrases:
        if phrase in lowered:
            violations.append(f"banned phrase: {phrase}")
            redacted = True

    # no fabricated experience: handled upstream by claim verification; here we
    # just enforce the hard policy rules.
    passed = len(violations) == 0

    state["compliance_verdict"] = ComplianceVerdict(
        passed=passed,
        violations=violations,
        reason=("; ".join(violations) if violations else "policy OK"),
        redacted=redacted,
    ).model_dump()
    return state
''')

# ---- agent/nodes/client_liaison.py ------------------------------------
w("agent/nodes/client_liaison.py", '''"""Client Liaison node: classify client intent and draft replies/slots."""
from __future__ import annotations

from agent.state import GigBidState
from agent.handoffs import ComplianceVerdict  # reuse verdict shape for replies


def client_liaison_node(state: GigBidState) -> GigBidState:
    message = state.get("client_message", {}) or {}
    body = message.get("body", "").lower()
    intent = _classify(body)

    draft = {"body": "", "intent": intent, "interview_slots": [], "needs_approval": True}
    if intent == "interview_request":
        draft["body"] = ("Thank you for your interest. I am available for an interview. "
                         "Here are some tentative slots I can hold for you.")
        draft["interview_slots"] = _tentative_slots()
    elif intent == "question":
        draft["body"] = ("Thank you for your question. I would be happy to clarify "
                         "once I have reviewed your project details.")
    elif intent == "negotiation":
        draft["body"] = ("Thank you for your message. I am open to discussing the "
                         "budget and scope to find a workable arrangement.")
    else:  # scam_signal / other
        draft["body"] = ("Thank you for reaching out. I will review your message and "
                         "get back to you shortly.")
        draft["needs_approval"] = True

    state["intent"] = intent
    state["reply_draft"] = draft
    state.setdefault("messages", []).append({"role": "assistant", "body": draft["body"]})
    return state


def _classify(body: str) -> str:
    if any(w in body for w in ["interview", "call", "meet", "zoom", "chat"]):
        return "interview_request"
    if any(w in body for w in ["budget", "price", "rate", "cost", "negotiate"]):
        return "negotiation"
    if any(w in body for w in ["telegram", "whatsapp", "off-platform", "pay outside"]):
        return "scam_signal"
    if "?" in body or any(w in body for w in ["how", "what", "can you"]):
        return "question"
    return "other"


def _tentative_slots() -> list[str]:
    return ["Tomorrow 10:00-11:00", "Tomorrow 14:00-15:00", "Day after 09:00-10:00"]
''')

# ---- agent/graphs/bid_graph.py ----------------------------------------
w("agent/graphs/bid_graph.py", '''"""Bid graph: one thread per job. Parallel analysis, bounded critique, approval gate."""
from __future__ import annotations

from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

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


def build_bid_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()
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
''')

# ---- agent/graphs/conversation_graph.py -------------------------------
w("agent/graphs/conversation_graph.py", '''"""Conversation graph: one thread per client conversation. Approval gate."""
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
''')

# ---- agent/memory/promotion_rules.py ----------------------------------
w("agent/memory/promotion_rules.py", '''"""Long-term memory promotion rules (R7). Raw tool output never enters memory."""
from __future__ import annotations


def should_promote_style_edit(edit_count: int, consistent_pattern: bool) -> bool:
    return bool(consistent_pattern and edit_count >= 3)


def should_record_outcome(outcome: str, min_evidence: int = 1) -> bool:
    return bool(outcome in {"won", "replied", "ignored", "lost", "hired"} and min_evidence >= 1)
''')

# ---- package inits ----------------------------------------------------
w("agent/nodes/__init__.py", '"""Agent node implementations."""\n')
w("agent/graphs/__init__.py", '"""LangGraph orchestration graphs."""\n')
w("agent/memory/__init__.py", '"""Long-term memory promotion rules."""\n')
w("agent/prompts/__init__.py", '"""Prompt templates for agents."""\n')

w("mcp_servers/__init__.py", '"""MCP tool servers: portfolio, marketplace, workspace."""\n')
w("mcp_servers/portfolio/__init__.py", '"""Read-only portfolio server."""\n')
w("mcp_servers/marketplace/__init__.py", '"""Marketplace MCP server wrapping GigSim."""\n')
w("mcp_servers/workspace/__init__.py", '"""Workspace MCP server (calendar + email)."""\n')

w("mcp_servers/portfolio/server.py", '''"""Portfolio MCP server (read-only)."""
from __future__ import annotations

from typing import Any
import json
from pathlib import Path

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("gigbid-portfolio")
EVIDENCE: list[dict[str, Any]] = []
CASES: dict[str, dict[str, Any]] = {}
SKILLS: set[str] = set()


def load_data(data_dir: str = "data") -> None:
    global EVIDENCE, CASES, SKILLS
    p = Path(data_dir) / "portfolio_items.json"
    if p.exists():
        EVIDENCE = json.loads(p.read_text(encoding="utf-8"))
    for e in EVIDENCE:
        CASES[e.get("evidence_id", e.get("id", ""))] = e
        for s in e.get("skills", []) or []:
            SKILLS.add(s)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="search_evidence", description="Search portfolio evidence.",
                   inputSchema={"type": "object", "properties": {
                       "requirement": {"type": "string"}, "k": {"type": "integer", "default": 5},
                       "filters": {"type": "object", "default": {}}}, "required": ["requirement"]}),
        types.Tool(name="get_case_study", description="Get a case study by id.",
                   inputSchema={"type": "object", "properties": {"id": {"type": "string"}},
                                 "required": ["id"]}),
        types.Tool(name="list_skills", description="List all portfolio skills.",
                   inputSchema={"type": "object", "properties": {}}),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name == "search_evidence":
        req = (arguments.get("requirement") or "").lower()
        k = int(arguments.get("k", 5))
        results = []
        for e in EVIDENCE:
            text = (e.get("title", "") + " " + e.get("summary", "") + " "
                    + " ".join(e.get("skills", []) or [])).lower()
            if req in text or not req:
                results.append(e)
        return [types.TextContent(type="text", text=json.dumps(results[:k]))]
    if name == "get_case_study":
        return [types.TextContent(type="text", text=json.dumps(CASES.get(arguments.get("id", ""), {})))]
    if name == "list_skills":
        return [types.TextContent(type="text", text=json.dumps(sorted(SKILLS)))]
    return [types.TextContent(type="text", text=json.dumps({"error": "unknown tool"}))]


@server.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(uriTemplate="portfolio://case/{id}", name="case study",
                               description="Full case study by id"),
        types.ResourceTemplate(uriTemplate="portfolio://proposal/{id}", name="proposal",
                               description="Past proposal by id"),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri.startswith("portfolio://case/"):
        return json.dumps(CASES.get(uri.split("/case/")[-1], {}))
    if uri.startswith("portfolio://proposal/"):
        return json.dumps(CASES.get(uri.split("/proposal/")[-1], {}))
    return json.dumps({"error": "unknown resource"})


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [types.Prompt(name="answer_screening_question",
                         description="Answer a screening question from portfolio evidence.",
                         arguments=[types.PromptArgument(name="question", required=True),
                                    types.PromptArgument(name="evidence", required=False)])]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str]) -> types.GetPromptResult:
    question = arguments.get("question", "")
    return types.GetPromptResult(
        description="Screening-question answerer",
        messages=[types.PromptMessage(role="user",
                                      content=types.TextContent(
                                          type="text",
                                          text=f"Answer using only portfolio evidence: {question}"))])


async def run_stdio() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         InitializationOptions(server_name="gigbid-portfolio", server_version="0.1.0",
                                               capabilities=server.get_capabilities(
                                                   notification_types=None,
                                                   experimental_capabilities=None)))


def main() -> None:
    import asyncio
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
''')

w("mcp_servers/marketplace/server.py", '''from __future__ import annotations

from typing import Any
import json
import uuid

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from agent.marketplace_port import build_port

server = Server("gigbid-marketplace")
AUDIT_LOG = []


def _audit(user, tool, args, result, trace_id):
    AUDIT_LOG.append({"user": user, "tool": tool, "arguments": args,
                      "result": result, "trace_id": trace_id})


@server.list_tools()
async def list_tools():
    tools = [
        ("search_jobs", "Search jobs (read).", {"query": "", "limit": 20},
         ["user_id", "trace_id"], {"readOnlyHint": True}),
        ("get_job", "Get a job (read).", {"job_id": "", "user_id": "", "trace_id": ""},
         ["job_id", "user_id", "trace_id"], {"readOnlyHint": True}),
        ("get_client_history", "Client history (read).", {"client_id": "", "user_id": "", "trace_id": ""},
         ["client_id", "user_id", "trace_id"], {"readOnlyHint": True}),
        ("get_connects_balance", "Connects balance (read).", {"user_id": "", "trace_id": ""},
         ["user_id", "trace_id"], {"readOnlyHint": True}),
        ("create_proposal_draft", "Create proposal draft (write, idempotent).",
         {"job_id": "", "cover_letter": "", "screening_answers": [], "idempotency_key": "",
          "dry_run": True, "user_id": "", "trace_id": ""},
         ["job_id", "cover_letter", "idempotency_key", "user_id", "trace_id"],
         {"destructiveHint": False, "idempotentHint": True}),
        ("submit_proposal", "Submit proposal (write, idempotent).",
         {"draft_id": "", "idempotency_key": "", "user_id": "", "trace_id": ""},
         ["draft_id", "idempotency_key", "user_id", "trace_id"],
         {"destructiveHint": True, "idempotentHint": True}),
        ("send_message", "Send message (write, idempotent).",
         {"client_id": "", "body": "", "idempotency_key": "", "user_id": "", "trace_id": ""},
         ["client_id", "body", "idempotency_key", "user_id", "trace_id"],
         {"destructiveHint": True, "idempotentHint": True}),
    ]
    out = []
    for name, desc, props, req, ann in tools:
        schema = {"type": "object", "properties": {k: ({"type": "string"} if not isinstance(v, list)
                          else {"type": "array", "items": {"type": "string"}})
                          for k, v in props.items()}, "required": req}
        for k, v in props.items():
            if isinstance(v, bool):
                schema["properties"][k] = {"type": "boolean", "default": v}
            elif isinstance(v, int):
                schema["properties"][k] = {"type": "integer", "default": v}
        out.append(types.Tool(name=name, description=desc, inputSchema=schema,
                              annotations=ann))
    return out


@server.call_tool()
async def call_tool(name, arguments):
    user = arguments.get("user_id", "anon")
    trace_id = arguments.get("trace_id", str(uuid.uuid4()))
    port = build_port()
    result = {}
    if name == "search_jobs":
        result = [j.__dict__ for j in port.search_jobs(query=arguments.get("query", ""),
                                                       limit=int(arguments.get("limit", 20)))]
    elif name == "get_job":
        r = port.get_job(arguments["job_id"]); result = r.__dict__ if r else None
    elif name == "get_client_history":
        r = port.get_client_history(arguments["client_id"]); result = r.__dict__ if r else None
    elif name == "get_connects_balance":
        result = {"balance": port.get_connects_balance()}
    elif name == "create_proposal_draft":
        if arguments.get("dry_run"):
            result = {"status": "dry_run", "would_send": True,
                      "cover_letter_preview": arguments.get("cover_letter", "")[:120]}
        else:
            result = port.create_proposal_draft(arguments["job_id"], arguments["cover_letter"],
                                                arguments.get("screening_answers", []),
                                                arguments["idempotency_key"])
    elif name == "submit_proposal":
        result = port.submit_proposal(arguments["draft_id"], arguments["idempotency_key"])
    elif name == "send_message":
        result = port.send_message(arguments["client_id"], arguments["body"],
                                   arguments["idempotency_key"])
    else:
        result = {"error": "unknown tool"}
    _audit(user, name, arguments, result, trace_id)
    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


async def run_stdio():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         InitializationOptions(server_name="gigbid-marketplace", server_version="0.1.0",
                                               capabilities=server.get_capabilities(
                                                   notification_types=None,
                                                   experimental_capabilities=None)))


def main():
    import asyncio
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
''')

w("rag/__init__.py", '"""Advanced RAG: ingestion, retrieval, variants, claim verification."""\n')
w("rag/ingest/__init__.py", '"""Portfolio ingestion."""\n')

w("rag/ingest/ingest.py", '''from __future__ import annotations

from typing import Any
from pathlib import Path
import json
import hashlib


def load_portfolio_items(data_dir: str = "data") -> list[dict[str, Any]]:
    p = Path(data_dir) / "portfolio_items.json"
    if not p.exists():
        return []
    items = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for it in items:
        eid = it.get("evidence_id") or it.get("id") or hashlib.sha256(
            (it.get("title", "") + str(it.get("skills", []))).encode()).hexdigest()[:12]
        out.append({
            "evidence_id": eid,
            "type": it.get("type", "case_study"),
            "title": it.get("title", ""),
            "summary": it.get("summary", ""),
            "skills": it.get("skills", []),
            "outcome": it.get("outcome", ""),
            "source": it.get("source", ""),
            "text": (it.get("title", "") + " " + it.get("summary", "") +
                     " " + " ".join(it.get("skills", []))).strip(),
        })
    return out
''')

w("rag/retriever.py", '''from __future__ import annotations

from typing import Any
import importlib

_VARIANTS = {
    "v0": "rag.variants.v0_naive",
    "v1": "rag.variants.v1_requirement",
    "v2": "rag.variants.v2_hybrid",
    "v3": "rag.variants.v3_rerank",
    "v4": "rag.variants.v4_outcome",
    "v5": "rag.variants.v5_multivector",
    "v6": "rag.variants.v6_contextual",
    "v7": "rag.variants.v7_hyde",
    "v8": "rag.variants.v8_corrective",
    "v9": "rag.variants.v9_graphrag",
}
_ACTIVE = "v0"


def set_variant(variant_id):
    global _ACTIVE
    if variant_id not in _VARIANTS:
        raise ValueError(f"unknown variant {variant_id}")
    _ACTIVE = variant_id


def retrieve_evidence(query, k=5, persona="default", variant=None):
    vid = variant or _ACTIVE
    mod = importlib.import_module(_VARIANTS[vid])
    fn = getattr(mod, "retrieve", None)
    if fn is None:
        return []
    return fn(query, k=k, persona=persona)
''')

w("rag/verify.py", '''from __future__ import annotations

from typing import Any


def verify_claims(draft, evidence):
    claims = _split_claims(draft)
    results = []
    ev_text = " ".join(
        (e.get("title", "") + " " + e.get("summary", "") + " " +
         " ".join(e.get("skills", []) or [])).lower() for e in evidence)
    for c in claims:
        c_lower = c.lower()
        verdict = "supported" if c_lower in ev_text else (
            "partly_supported" if any(w in ev_text for w in c_lower.split() if len(w) > 3)
            else "unsupported")
        results.append({"claim": c, "verdict": verdict})
    return results


def _split_claims(text):
    return [s.strip() for s in text.replace("?", ".").split(".") if s.strip()][:8]


def unsupported_rate(verification):
    if not verification:
        return 0.0
    return sum(1 for v in verification if v.get("verdict") == "unsupported") / len(verification)
''')

w("mcp_servers/workspace/server.py", '''from __future__ import annotations

from typing import Any
import json
import uuid
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("gigbid-workspace")


def _slots():
    now = datetime.now()
    return [(now + timedelta(days=1, hours=h)).strftime("%Y-%m-%d %H:%M")
            for h in range(9, 17, 2)]


@server.list_tools()
async def list_tools():
    return [
        types.Tool(name="free_calendar_slots", description="Free calendar slots.",
                   inputSchema={"type": "object", "properties": {
                       "date": {"type": "string"}, "user_id": {"type": "string"}},
                       "required": ["user_id"]}),
        types.Tool(name="create_interview_hold", description="Tentative interview hold.",
                   inputSchema={"type": "object", "properties": {
                       "slot": {"type": "string"}, "client_id": {"type": "string"},
                       "user_id": {"type": "string"}},
                       "required": ["slot", "client_id", "user_id"]},
                   annotations={"destructiveHint": False, "idempotentHint": True}),
        types.Tool(name="create_email_draft", description="Email draft.",
                   inputSchema={"type": "object", "properties": {
                       "to": {"type": "string"}, "subject": {"type": "string"},
                       "body": {"type": "string"}, "user_id": {"type": "string"}},
                       "required": ["to", "subject", "body", "user_id"]}),
    ]


@server.call_tool()
async def call_tool(name, arguments):
    if name == "free_calendar_slots":
        result = {"slots": _slots(), "date": arguments.get("date")}
    elif name == "create_interview_hold":
        result = {"hold_id": f"hold-{uuid.uuid4().hex[:8]}", "slot": arguments.get("slot"),
                  "status": "tentative", "client_id": arguments.get("client_id")}
    elif name == "create_email_draft":
        result = {"draft_id": f"draft-{uuid.uuid4().hex[:8]}", "to": arguments.get("to"),
                  "subject": arguments.get("subject"), "status": "draft"}
    else:
        result = {"error": "unknown tool"}
    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


async def run_stdio():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         InitializationOptions(server_name="gigbid-workspace", server_version="0.1.0",
                                               capabilities=server.get_capabilities(
                                                   notification_types=None,
                                                   experimental_capabilities=None)))


def main():
    import asyncio
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
''')

w("rag/variants/__init__.py", '"""RAG retrieval variants V0-V9."""\n')

w("rag/variants/v0_naive.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.ingest.ingest import load_portfolio_items
    items = load_portfolio_items()
    q = (query or "").lower()
    scored = []
    for it in items:
        text = it.get("text", "").lower()
        score = sum(1 for w in q.split() if w and w in text) / max(len(q.split()), 1)
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:k]]
''')

w("rag/variants/v1_requirement.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.ingest.ingest import load_portfolio_items
    items = load_portfolio_items()
    reqs = [r.strip() for r in (query or "").split(",") if r.strip()] or [query or ""]
    out = []
    seen = set()
    for r in reqs:
        q = r.lower()
        for it in items:
            eid = it.get("evidence_id") or it.get("id")
            if eid in seen:
                continue
            text = it.get("text", "").lower()
            if q in text or any(w in text for w in q.split() if len(w) > 3):
                out.append(it)
                seen.add(eid)
                break
    return out[:k]
''')

w("rag/variants/v2_hybrid.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    from rag.variants.v1_requirement import retrieve as v1
    a = v0(query, k=k, persona=persona)
    b = v1(query, k=k, persona=persona)
    fused = {}
    for rank, it in enumerate(a):
        fused.setdefault(it.get("evidence_id") or it.get("id"), dict(it, _rrf=1.0 / (rank + 1)))
    for rank, it in enumerate(b):
        eid = it.get("evidence_id") or it.get("id")
        cur = fused.setdefault(eid, dict(it, _rrf=0.0))
        cur["_rrf"] = cur.get("_rrf", 0) + 1.0 / (rank + 1)
    return [it for _, it in sorted(fused.items(), key=lambda kv: kv[1].get("_rrf", 0), reverse=True)][:k]
''')

w("rag/variants/v3_rerank.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    candidates = v0(query, k=max(k * 4, 20), persona=persona)
    q = (query or "").lower()

    def score(it):
        text = it.get("text", "").lower()
        return sum(2 for w in q.split() if w and w in text) + sum(1 for w in q.split()
                                                                  if w and w in it.get("title", "").lower())

    return sorted(candidates, key=score, reverse=True)[:k]
''')

w("rag/variants/v4_outcome.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    items = v0(query, k=max(k * 3, 15), persona=persona)
    boost = {"won": 1.3, "replied": 1.15, "hired": 1.4}

    def score(it):
        base = sum(1 for w in (query or "").lower().split() if w and w in it.get("text", "").lower())
        return base * boost.get(it.get("outcome", ""), 1.0)

    return sorted(items, key=score, reverse=True)[:k]
''')

w("rag/variants/v5_multivector.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.ingest.ingest import load_portfolio_items
    items = load_portfolio_items()
    q = (query or "").lower()
    scored = []
    for it in items:
        text = it.get("text", "").lower()
        score = sum(1 for w in q.split() if w and w in text) / max(len(q.split()), 1)
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:k]]
''')

w("rag/variants/v6_contextual.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    items = v0(query, k=k, persona=persona)
    for it in items:
        it["text"] = f"Context: relates to {query or 'the job'}.\n" + it.get("text", "")
    return items
''')

w("rag/variants/v7_hyde.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    hypo = f"I have built {query or 'this'} using Python and delivered measurable results."
    return v0(hypo, k=k, persona=persona)
''')

w("rag/variants/v8_corrective.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    items = v0(query, k=k, persona=persona)
    if not items:
        first = (query or "").split()
        items = v0(first[0] if first else query, k=k, persona=persona)
    return items
''')

w("rag/variants/v9_graphrag.py", '''from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    return v0(query, k=k, persona=persona)
''')

written = 0
for rel, content in FILES.items():
    target = ROOT / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    written += 1

print(f"Wrote {written} files to {ROOT}")