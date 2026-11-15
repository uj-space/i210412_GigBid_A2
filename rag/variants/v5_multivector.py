"""V5: Multi-vector retrieval (summary, README, and code chunks indexed together, grouped by project)."""
from __future__ import annotations

from rag.index.hybrid_index import get_index


def retrieve(query: str, k: int = 5, persona: str = "default"):
    idx = get_index(persona)
    hits = idx.search_multivector(query, k=max(k * 3, 15))
    seen_projects: set[str] = set()
    out = []
    for doc_idx, score in hits:
        it = idx.items[doc_idx]
        proj = it.get("project") or it.get("evidence_id")
        if proj not in seen_projects or len(out) < k:
            seen_projects.add(proj)
            out.append({**it, "_score": round(score, 4)})
        if len(out) >= k:
            break
    return out
