"""V8: Corrective / Self-RAG loop (grade evidence coverage, re-query when weak, refuse when unsupported)."""
from __future__ import annotations

import re
from rag.variants.v3_rerank import retrieve as v3_retrieve
from rag.variants.v1_requirement import retrieve as v1_retrieve


def _grade_coverage(query: str, items: list[dict]) -> float:
    q_toks = {t for t in re.findall(r"[a-z0-9_+#.-]+", (query or "").lower()) if len(t) > 2}
    if not q_toks or not items:
        return 0.0
    ev_toks: set[str] = set()
    for it in items[:5]:
        ev_toks.update(re.findall(r"[a-z0-9_+#.-]+", (it.get("text") or "").lower()))
        ev_toks.update(s.lower() for s in (it.get("skills") or []))
    return len(q_toks & ev_toks) / len(q_toks)


def retrieve(query: str, k: int = 5, persona: str = "default"):
    # Step 1: Hybrid + Rerank retrieval
    items = v3_retrieve(query, k=k, persona=persona)
    cov = _grade_coverage(query, items)

    # Step 2: Corrective re-query if coverage is weak (< 0.35)
    if cov < 0.35:
        alt_items = v1_retrieve(query, k=k, persona=persona)
        if _grade_coverage(query, alt_items) > cov:
            items = alt_items
            cov = _grade_coverage(query, items)

    # Annotate confidence so downstream Writer/Critic can refuse to claim when cov == 0
    return [{**it, "_corrective_coverage": round(cov, 3)} for it in items[:k]]
