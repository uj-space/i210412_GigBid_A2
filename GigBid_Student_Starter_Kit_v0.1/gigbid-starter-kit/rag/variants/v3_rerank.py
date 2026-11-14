from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    candidates = v0(query, k=max(k * 4, 20), persona=persona)
    q = (query or "").lower()

    def score(it):
        text = it.get("text", "").lower()
        return sum(2 for w in q.split() if w and w in text) + sum(1 for w in q.split()
                                                                  if w and w in it.get("title", "").lower())

    return sorted(candidates, key=score, reverse=True)[:k]
