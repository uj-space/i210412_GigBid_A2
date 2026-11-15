"""Critic node: check grounding, personalisation, and length; loop back at most twice (C4)."""
from __future__ import annotations

from agent.handoffs import Critique
from agent.llm import load_config, load_prompt
from agent.state import GigBidState


def critic_node(state: GigBidState) -> GigBidState:
    _ = load_prompt("critic")
    cfg = load_config()
    max_revisions = int((cfg.get("budgets") or {}).get("max_revisions", 2))

    draft = state.get("proposal_draft", {}) or {}
    verification = state.get("claim_verification", []) or []
    revision_count = int(state.get("revision_count", 0) or 0)

    unsupported = [v for v in verification if v.get("verdict") == "unsupported"]
    partly = [v for v in verification if v.get("verdict") == "partly_supported"]
    cover = draft.get("cover_letter", "")

    grounded = len(unsupported) == 0
    length_ok = 80 <= len(cover) <= 1200
    generic_openers = ("i am writing to apply", "hardworking developer", "dear sir/madam")
    personalised = not any(g in cover.lower() for g in generic_openers) and len(cover) >= 80

    suggestions: list[str] = []
    if not grounded:
        suggestions.append("Remove or cite portfolio evidence for unsupported claims.")
    if not length_ok:
        suggestions.append("Adjust proposal length to 80-1200 characters.")
    if not personalised:
        suggestions.append("Replace generic opening with project-specific evidence.")
    if partly:
        suggestions.append("Tighten partly supported claims with exact case study IDs.")

    critique = Critique(
        grounded=grounded,
        unsupported_claims=[u.get("claim", "") for u in unsupported],
        suggestions=suggestions,
        length_ok=length_ok,
        personalised=personalised,
        revision_count=revision_count,
    )

    needs_rev = revision_count < max_revisions and (not grounded or not length_ok or not personalised)
    return {
        "critique": critique.model_dump(),
        "needs_revision": needs_rev,
        "revision_count": revision_count + (1 if needs_rev else 0),
        "critique_complete": not needs_rev,
        "step_count": int(state.get("step_count", 0) or 0) + 1,
    }
