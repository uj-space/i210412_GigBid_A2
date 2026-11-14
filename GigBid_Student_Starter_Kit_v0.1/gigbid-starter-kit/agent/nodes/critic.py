"""Critic node: review grounding/specificity/length; max two revisions (C4)."""
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
