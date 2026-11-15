"""V0: Naive dense baseline (cosine similarity on raw chunks)."""
from __future__ import annotations

from rag.index.hybrid_index import get_index


def retrieve(query: str, k: int = 5, persona: str = "default"):
    idx = get_index(persona)
    hits = idx.search_dense(query, k=k)
    return [{**idx.items[i], "_score": round(s, 4)} for i, s in hits]
