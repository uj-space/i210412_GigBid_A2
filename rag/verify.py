"""Claim splitting, evidence verification, and unsupported-claim rewriting (B3 / R5)."""
from __future__ import annotations

import re
from typing import Any


def split_claims(text: str) -> list[str]:
    """Split a proposal into atomic declarative claim sentences."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) > 12]
    # Ignore pure salutations/closings
    ignored = ("dear ", "hello", "hi ", "thank you", "best regards", "sincerely", "happy to discuss")
    return [s for s in sents if not s.lower().startswith(ignored)]


def verify_claims(draft: str, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verify each claim sentence against retrieved portfolio evidence."""
    claims = split_claims(draft)
    ev_docs = []
    for e in evidence or []:
        eid = e.get("evidence_id") or e.get("id") or "unknown"
        txt = " ".join([
            str(e.get("title", "")),
            str(e.get("summary", "")),
            str(e.get("text", "")),
            " ".join(e.get("skills", []) or []),
            str(e.get("project", "")),
            str(e.get("client_industry", "")),
        ]).lower()
        toks = {t for t in re.findall(r"[a-z0-9_+#.-]+", txt) if len(t) > 2}
        ev_docs.append((eid, txt, toks))

    results: list[dict[str, Any]] = []
    for c in claims:
        c_lower = c.lower()
        c_toks = {t for t in re.findall(r"[a-z0-9_+#.-]+", c_lower) if len(t) > 2}
        # Remove generic filler words from overlap check
        filler = {"have", "with", "this", "that", "your", "for", "and", "the", "from", "can", "will", "delivered", "built"}
        meaningful = c_toks - filler
        best_eid = None
        best_ratio = 0.0
        for eid, txt, toks in ev_docs:
            if eid.lower() in c_lower:
                best_eid = eid
                best_ratio = 1.0
                break
            if meaningful:
                ratio = len(meaningful & toks) / len(meaningful)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_eid = eid

        if best_ratio >= 0.45:
            verdict = "supported"
        elif best_ratio >= 0.2:
            verdict = "partly_supported"
        else:
            verdict = "unsupported"
        results.append({"claim": c, "verdict": verdict, "evidence_id": best_eid, "overlap": round(best_ratio, 3)})
    return results


def prune_unsupported_claims(draft: str, evidence: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], float, float]:
    """Verify claims, remove unsupported sentences, and return (cleaned_draft, verification, before_rate, after_rate)."""
    before_ver = verify_claims(draft, evidence)
    before_rate = unsupported_rate(before_ver)
    unsupported_set = {v["claim"] for v in before_ver if v["verdict"] == "unsupported"}

    if not unsupported_set:
        return draft, before_ver, before_rate, before_rate

    lines = draft.splitlines()
    kept_lines = []
    for line in lines:
        cleaned = line
        for u in unsupported_set:
            cleaned = cleaned.replace(u, "").strip()
        if cleaned or line == "":
            kept_lines.append(cleaned)
    cleaned_draft = "\n".join(kept_lines).strip()
    after_ver = verify_claims(cleaned_draft, evidence)
    after_rate = unsupported_rate(after_ver)
    return cleaned_draft, after_ver, before_rate, after_rate


def unsupported_rate(verification: list[dict[str, Any]]) -> float:
    if not verification:
        return 0.0
    return sum(1 for v in verification if v.get("verdict") == "unsupported") / len(verification)
