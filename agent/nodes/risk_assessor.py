"""Risk Assessor node: score client quality via Marketplace MCP and detect scams/injection."""
from __future__ import annotations

from agent.handoffs import RiskReport
from agent.llm import load_prompt
from agent.mcp_client import call_mcp_tool
from agent.safety import detect_injection
from agent.state import GigBidState


def risk_assessor_node(state: GigBidState) -> GigBidState:
    _ = load_prompt("risk_assessor")
    job = state.get("job", {}) or {}
    desc = (job.get("description", "") or "").lower()
    title = (job.get("title", "") or "").lower()
    full = f"{title} {desc}"
    signals = list(job.get("warning_signals", []) or [])

    # Fetch client history via allowlisted Marketplace MCP tool
    client = state.get("client_history") or {}
    cid = job.get("client_id")
    tool_calls = []
    if not client and cid:
        res = call_mcp_tool(
            "risk_assessor",
            "marketplace",
            "get_client_history",
            {"client_id": cid, "user_id": state.get("user_id", "default"), "trace_id": state.get("trace_id", "tr")},
        )
        tool_calls.append({"node": "risk_assessor", "tool": "get_client_history", "status": res.get("status")})
        if isinstance(res.get("data"), dict):
            client = res["data"]

    flags: list[str] = []
    unpaid = ("unpaid_work" in signals) or any(w in full for w in ["unpaid", "free trial", "test project", "for free", "no pay"])
    if unpaid:
        flags.append("unpaid_work")

    off_platform = ("off_platform_contact" in signals) or any(
        w in full for w in ["telegram", "whatsapp", "off-platform", "pay outside", "contact me directly"]
    )
    if off_platform:
        flags.append("off_platform_contact")

    if any(w in full for w in ["guarantee", "100% roi"]):
        flags.append("unverifiable_guarantee")

    inj_hits = detect_injection(full)
    injection = bool(inj_hits) or ("prompt_injection" in signals)
    if injection:
        flags.append("prompt_injection")

    scam = unpaid or off_platform or injection

    # Quality score: higher = safer/better client (0..1)
    quality = 0.55
    if client.get("payment_verified"):
        quality += 0.20
    if (client.get("completed_projects") or 0) >= 3:
        quality += 0.15
    if (client.get("average_rating") or 0) >= 4.5:
        quality += 0.10
    if scam:
        quality = max(0.0, quality - 0.65)
    quality = round(max(0.0, min(1.0, quality)), 3)

    report = RiskReport(
        score=quality,
        flags=flags,
        explanation=f"Client quality {quality:.2f}. " + ("; ".join(flags) if flags else "no major risk signals"),
        scam=scam,
        unpaid_work=unpaid,
        off_platform=off_platform,
        injection=injection,
    )
    return {"risk_report": report.model_dump(), "tool_calls": tool_calls}
