"""Typed LangGraph state for the GigBid bid and conversation graphs."""
from __future__ import annotations

from typing import Any, Annotated, TypedDict, List
import operator


def _last_wins(a: Any, b: Any) -> Any:
    """Reducer: keep the most recent value (for scalar keys set once)."""
    return b


class GigBidState(TypedDict, total=False):
    # identity / routing
    thread_id: Annotated[str, _last_wins]
    mode: Annotated[str, _last_wins]  # "bid" | "conversation"
    user_id: Annotated[str, _last_wins]

    # job inputs
    saved_searches: Annotated[List[str], operator.add]
    new_jobs: Annotated[List[dict], operator.add]
    job: Annotated[dict[str, Any], _last_wins]
    seen_job_fingerprints: Annotated[List[str], operator.add]

    # analysis outputs
    job_spec: Annotated[dict[str, Any], _last_wins]
    risk_report: Annotated[dict[str, Any], _last_wins]
    fit_report: Annotated[dict[str, Any], _last_wins]
    evidence: Annotated[List[dict[str, Any]], operator.add]

    # decision / pricing
    decision: Annotated[str, _last_wins]
    price_quote: Annotated[dict[str, Any], _last_wins]

    # proposal flow
    proposal_draft: Annotated[dict[str, Any], _last_wins]
    claim_verification: Annotated[List[dict[str, Any]], operator.add]
    critique: Annotated[dict[str, Any], _last_wins]
    compliance_verdict: Annotated[dict[str, Any], _last_wins]
    revision_count: Annotated[int, _last_wins]
    approval_status: Annotated[str, _last_wins]  # pending | approved | edited | rejected
    approval_payload: Annotated[dict[str, Any], _last_wins]

    # conversation flow
    messages: Annotated[List[dict[str, Any]], operator.add]
    client_message: Annotated[dict[str, Any], _last_wins]
    intent: Annotated[str, _last_wins]
    reply_draft: Annotated[dict[str, Any], _last_wins]

    # outcomes / memory
    outcome: Annotated[dict[str, Any], _last_wins]
    style_memory: Annotated[List[dict[str, Any]], operator.add]
    outcome_memory: Annotated[List[dict[str, Any]], operator.add]

    # control
    errors: Annotated[List[str], operator.add]
    step_count: Annotated[int, _last_wins]
    token_budget: Annotated[int, _last_wins]
    needs_attention: Annotated[bool, _last_wins]

    # traces / audit
    trace_id: Annotated[str, _last_wins]
    tool_calls: Annotated[List[dict[str, Any]], operator.add]

    # transient loop control (not part of persisted schema)
    needs_revision: Annotated[bool, _last_wins]
    critique_complete: Annotated[bool, _last_wins]
    unsupported_claims: Annotated[List[dict[str, Any]], operator.add]
