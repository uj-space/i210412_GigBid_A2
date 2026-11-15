"""V1: Requirement decomposition (split multi-requirement query, retrieve per requirement, merge)."""
from __future__ import annotations

import re
from rag.index.hybrid_index import get_index


def _decompose(query: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[,;\n•\-]+|\band\b", query or "", flags=re.I) if len(p.strip()) >= 3]
    return parts[:6] if parts else [query or ""]


def retrieve(query: str, k: int = 5, persona: str = "default"):
    idx = get_index(persona)
    subqueries = _decompose(query)
    merged: dict[int, float] = {}
    for sq in subqueries:
        for doc_idx, score in idx.search_dense(sq, k=max(k, 8)):
            merged[doc_idx] = max(merged.get(doc_idx, 0.0), score)
    ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:k]
    return [{**idx.items[i], "_score": round(s, 4)} for i, s in ranked]
