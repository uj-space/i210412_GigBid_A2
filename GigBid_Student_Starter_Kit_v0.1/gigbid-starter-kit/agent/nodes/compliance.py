"""Compliance Guard: enforce policy pack; block with reason shown in UI."""
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
