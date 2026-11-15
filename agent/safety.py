"""Safety guardrails: prompt-injection delimiting and PII masking (E4 / R9)."""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?(policy|rules|instructions)",
    r"system\s+override",
    r"reveal\s+your\s+(system\s+)?prompt",
    r"you\s+are\s+now\s+",
    r"<!--.*?ignore.*?-->",
]


def delimit_untrusted(text: str, label: str = "untrusted_job_post") -> str:
    """Wrap untrusted marketplace text in explicit XML-style data delimiters."""
    safe = (text or "").replace(f"</{label}>", f"&lt;/{label}&gt;")
    return f"<{label}>\n{safe}\n</{label}>"


def detect_injection(text: str) -> list[str]:
    lower = (text or "").lower()
    hits = []
    for pat in INJECTION_PATTERNS:
        if re.search(pat, lower, flags=re.IGNORECASE | re.DOTALL):
            hits.append(pat)
    return hits


def mask_pii(text: str) -> str:
    """Mask emails, phone numbers, and payment card/account numbers in logs & traces."""
    if not text:
        return ""
    masked = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL_REDACTED]", text)
    masked = re.sub(r"\b(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b", "[PHONE_REDACTED]", masked)
    masked = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "[PAYMENT_REDACTED]", masked)
    return masked
