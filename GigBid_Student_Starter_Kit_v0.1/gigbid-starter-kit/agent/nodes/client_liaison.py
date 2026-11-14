"""Client Liaison node: classify client intent and draft replies/slots."""
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
