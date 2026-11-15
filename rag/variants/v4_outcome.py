"""V4: Outcome-aware ranking (boost won/replied evidence, penalize ignored)."""
from __future__ import annotations

from rag.variants.v3_rerank import retrieve as v3_retrieve

OUTCOME_WEIGHTS = {
    "won": 0.35,
    "verified": 0.20,
    "replied": 0.15,
    "ignored": -0.15,
}


def retrieve(query: str, k: int = 5, persona: str = "default"):
    pool = v3_retrieve(query, k=max(k * 3, 15), persona=persona)
    rescored = []
    for it in pool:
        bonus = OUTCOME_WEIGHTS.get(str(it.get("outcome", "")).lower(), 0.0)
        rescored.append((float(it.get("_score", 0.0)) + bonus, it))
    rescored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in rescored[:k]]
