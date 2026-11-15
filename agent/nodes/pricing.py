"""Pricing Strategist node: compute PriceQuote from Kaggle contract stats, client spend, and Connects."""
from __future__ import annotations

import json
from pathlib import Path
from agent.handoffs import PriceQuote
from agent.llm import load_config, load_prompt
from agent.mcp_client import call_mcp_tool
from agent.state import GigBidState

ROOT = Path(__file__).resolve().parents[2]
PRICING_STATS_PATH = ROOT / "data" / "market" / "market_pricing_stats.json"


def _market_median() -> float:
    if PRICING_STATS_PATH.exists():
        try:
            d = json.loads(PRICING_STATS_PATH.read_text(encoding="utf-8"))
            return float((d.get("hourly_rate") or {}).get("median", 45.0))
        except Exception:
            pass
    return 45.0


def pricing_node(state: GigBidState) -> GigBidState:
    _ = load_prompt("pricing")
    cfg = load_config()
    policy = cfg.get("policy") or {}
    min_reserve = int(policy.get("min_connects_reserve", 4))
    max_connects = int(policy.get("max_connects_per_bid", 16))

    job = state.get("job", {}) or {}
    spec = state.get("job_spec", {}) or {}
    fit = state.get("fit_report", {}) or {}
    risk = state.get("risk_report", {}) or {}

    b = job.get("budget") if isinstance(job.get("budget"), dict) else {}
    b_min = spec.get("budget_min") if spec.get("budget_min") is not None else b.get("min")
    b_max = spec.get("budget_max") if spec.get("budget_max") is not None else b.get("max")

    median_hr = _market_median()
    floor = max(median_hr * 10.0, 250.0)
    if b_min and b_max:
        suggested = round((float(b_min) + float(b_max)) / 2.0, 2)
    elif b_max:
        suggested = round(float(b_max) * 0.85, 2)
    elif b_min:
        suggested = round(max(float(b_min), floor), 2)
    else:
        suggested = round(floor, 2)

    bal_res = call_mcp_tool(
        "pricing",
        "marketplace",
        "get_connects_balance",
        {"user_id": state.get("user_id", "default"), "trace_id": state.get("trace_id", "tr")},
    )
    balance = int((bal_res.get("data") or {}).get("balance", 50))
    connects_cost = int(job.get("connects_cost", 6) or 6)

    worth_it = (
        not risk.get("scam", False)
        and float(fit.get("score", 0.0)) >= float((cfg.get("thresholds") or {}).get("minimum_fit_score", 0.45))
        and connects_cost <= max_connects
        and (balance - connects_cost) >= min_reserve
        and suggested >= 100.0
    )

    quote = PriceQuote(
        job_id=job.get("job_id", ""),
        suggested_bid=suggested,
        currency=job.get("currency", "USD"),
        connects_cost=connects_cost,
        worth_it=worth_it,
        floor=floor,
        rationale=(
            f"Suggested ${suggested:.0f} (Kaggle market median ${median_hr:.0f}/hr, "
            f"fit={fit.get('score', 0)}, connects={connects_cost}/{balance})."
        ),
    )
    return {
        "price_quote": quote.model_dump(),
        "tool_calls": [{"node": "pricing", "tool": "get_connects_balance", "status": bal_res.get("status")}],
        "step_count": int(state.get("step_count", 0) or 0) + 1,
    }
