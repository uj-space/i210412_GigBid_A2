"""Client Liaison node: classify untrusted client message intent and draft reply via Workspace MCP."""
from __future__ import annotations

from agent.llm import load_prompt
from agent.mcp_client import call_mcp_tool
from agent.safety import delimit_untrusted, detect_injection
from agent.state import GigBidState


def client_liaison_node(state: GigBidState) -> GigBidState:
    _ = load_prompt("client_liaison")
    message = state.get("client_message", {}) or {}
    user_id = state.get("user_id", "default")
    body = message.get("body", "")
    _ = delimit_untrusted(body, "untrusted_message")
    lower = body.lower()

    intent = _classify(lower)
    slots: list[str] = []
    tool_calls = []

    if intent == "interview_request":
        res = call_mcp_tool(
            "client_liaison",
            "workspace",
            "free_calendar_slots",
            {"user_id": user_id, "date": "tomorrow"},
        )
        tool_calls.append({"node": "client_liaison", "tool": "free_calendar_slots", "status": res.get("status")})
        slots = (res.get("data") or {}).get("slots", [])[:3]
        reply_body = (
            "Thanks for reaching out! I would be glad to jump on a call. "
            f"Here are a few available slots: {', '.join(slots)}. Let me know what works best."
        )
    elif intent == "negotiation":
        reply_body = (
            "Thank you for sharing your budget target. I can scope a focused Phase 1 milestone "
            "that fits your budget while preserving test coverage and documentation."
        )
    elif intent == "scam_signal":
        reply_body = (
            "For both our protection, I keep all project communication, milestones, and payments "
            "strictly on-platform. Happy to proceed here!"
        )
    elif intent == "question":
        reply_body = (
            "Great question — happy to walk through the exact architecture, validation metrics, "
            "and past case study details here on-platform."
        )
    else:
        reply_body = "Thanks for your message. I have reviewed your note and will follow up with next steps shortly."

    draft = {
        "body": reply_body,
        "intent": intent,
        "interview_slots": slots,
        "needs_approval": True,
    }
    return {
        "intent": intent,
        "reply_draft": draft,
        "messages": [{"role": "assistant", "body": reply_body}],
        "tool_calls": tool_calls,
    }


def _classify(body: str) -> str:
    if detect_injection(body) or any(w in body for w in ["telegram", "whatsapp", "off-platform", "pay outside"]):
        return "scam_signal"
    if any(w in body for w in ["interview", "call", "meet", "zoom", "availability", "slots"]):
        return "interview_request"
    if any(w in body for w in ["budget", "price", "rate", "discount", "negotiate"]):
        return "negotiation"
    if "?" in body or any(w in body for w in ["how", "what", "can you", "could you"]):
        return "question"
    return "other"
