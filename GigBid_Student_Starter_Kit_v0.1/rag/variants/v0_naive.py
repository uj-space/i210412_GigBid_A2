from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.ingest.ingest import load_portfolio_items
    items = load_portfolio_items()
    q = (query or "").lower()
    scored = []
    for it in items:
        text = it.get("text", "").lower()
        score = sum(1 for w in q.split() if w and w in text) / max(len(q.split()), 1)
        scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:k]]
