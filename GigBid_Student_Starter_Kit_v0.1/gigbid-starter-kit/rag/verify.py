from __future__ import annotations

from typing import Any


def verify_claims(draft, evidence):
    claims = _split_claims(draft)
    results = []
    ev_text = " ".join(
        (e.get("title", "") + " " + e.get("summary", "") + " " +
         " ".join(e.get("skills", []) or [])).lower() for e in evidence)
    for c in claims:
        c_lower = c.lower()
        verdict = "supported" if c_lower in ev_text else (
            "partly_supported" if any(w in ev_text for w in c_lower.split() if len(w) > 3)
            else "unsupported")
        results.append({"claim": c, "verdict": verdict})
    return results


def _split_claims(text):
    return [s.strip() for s in text.replace("?", ".").split(".") if s.strip()][:8]


def unsupported_rate(verification):
    if not verification:
        return 0.0
    return sum(1 for v in verification if v.get("verdict") == "unsupported") / len(verification)
