"""V2: Hybrid BM25 + Dense retrieval with Reciprocal Rank Fusion (RRF)."""
from __future__ import annotations

from rag.index.hybrid_index import get_index


def retrieve(query: str, k: int = 5, persona: str = "default"):
    idx = get_index(persona)
    dense_hits = idx.search_dense(query, k=max(k * 3, 15))
    bm25_hits = idx.search_bm25(query, k=max(k * 3, 15))

    rrf: dict[int, float] = {}
    for rank, (doc_idx, _) in enumerate(dense_hits):
        rrf[doc_idx] = rrf.get(doc_idx, 0.0) + 1.0 / (60.0 + rank + 1.0)
    for rank, (doc_idx, _) in enumerate(bm25_hits):
        rrf[doc_idx] = rrf.get(doc_idx, 0.0) + 1.2 / (60.0 + rank + 1.0)

    ranked = sorted(rrf.items(), key=lambda x: x[1], reverse=True)[:k]
    return [{**idx.items[i], "_score": round(s, 4)} for i, s in ranked]
