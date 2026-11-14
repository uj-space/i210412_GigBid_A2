from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.ingest.ingest import load_portfolio_items
    items = load_portfolio_items()
    reqs = [r.strip() for r in (query or "").split(",") if r.strip()] or [query or ""]
    out = []
    seen = set()
    for r in reqs:
        q = r.lower()
        for it in items:
            eid = it.get("evidence_id") or it.get("id")
            if eid in seen:
                continue
            text = it.get("text", "").lower()
            if q in text or any(w in text for w in q.split() if len(w) > 3):
                out.append(it)
                seen.add(eid)
                break
    return out[:k]
