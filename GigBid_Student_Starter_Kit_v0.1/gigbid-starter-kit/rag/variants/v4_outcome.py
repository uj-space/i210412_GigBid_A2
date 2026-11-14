from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    items = v0(query, k=max(k * 3, 15), persona=persona)
    boost = {"won": 1.3, "replied": 1.15, "hired": 1.4}

    def score(it):
        base = sum(1 for w in (query or "").lower().split() if w and w in it.get("text", "").lower())
        return base * boost.get(it.get("outcome", ""), 1.0)

    return sorted(items, key=score, reverse=True)[:k]
