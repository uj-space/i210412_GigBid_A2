"""Pricing Strategist node: propose a bid and assess Connects value."""
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
