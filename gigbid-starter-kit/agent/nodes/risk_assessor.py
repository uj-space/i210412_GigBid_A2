"""Risk Assessor node: score client quality and flag scams / injection."""
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
