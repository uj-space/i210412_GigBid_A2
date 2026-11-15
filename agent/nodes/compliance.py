"""Compliance Guard: enforce configurable policy pack & rules (C4 / E4)."""
from __future__ import annotations

from agent.handoffs import ComplianceVerdict
from agent.llm import load_config, load_prompt
from agent.safety import mask_pii
from agent.state import GigBidState


def compliance_node(state: GigBidState) -> GigBidState:
    _ = load_prompt("compliance")
    cfg = load_config()
    banned_phrases = (cfg.get("policy") or {}).get(
        "banned_phrases",
        ["guarantee", "100% refund", "pay me outside", "telegram", "whatsapp", "contact me directly", "off-platform"],
    )

    draft = state.get("proposal_draft", {}) or {}
    cover = draft.get("cover_letter", "")
    answers = draft.get("screening_answers", []) or []
    text = f"{cover} {' '.join(answers)}"
    lowered = text.lower()

    violations: list[str] = []
    redacted = False
    for phrase in banned_phrases:
        if phrase.lower() in lowered:
            violations.append(f"banned_phrase:{phrase}")
            redacted = True

    # Block any leaked PII (emails/phones) in outbound draft
    masked = mask_pii(text)
    if "[EMAIL_REDACTED]" in masked or "[PHONE_REDACTED]" in masked:
        violations.append("off_platform_contact_pii")
        redacted = True

    verdict = ComplianceVerdict(
        passed=len(violations) == 0,
        violations=violations,
        reason="; ".join(violations) if violations else "policy OK",
        redacted=redacted,
    )
    return {
        "compliance_verdict": verdict.model_dump(),
        "step_count": int(state.get("step_count", 0) or 0) + 1,
    }
