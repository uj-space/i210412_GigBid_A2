"""V9: Skill-Project-Client-Outcome GraphRAG traversal."""
from __future__ import annotations

import re
from rag.index.hybrid_index import get_index


def retrieve(query: str, k: int = 5, persona: str = "default"):
    idx = get_index(persona)
    q_toks = re.findall(r"[a-z0-9_+#.-]+", (query or "").lower())
    scores: dict[int, float] = {}

    for tok in q_toks:
        for doc_idx in idx.skill_graph.get(tok, []):
            it = idx.items[doc_idx]
            outcome_boost = 1.3 if it.get("outcome") in {"won", "verified"} else 1.0
            scores[doc_idx] = scores.get(doc_idx, 0.0) + 1.0 * outcome_boost
        for doc_idx in idx.industry_graph.get(tok, []):
            scores[doc_idx] = scores.get(doc_idx, 0.0) + 0.8

    if not scores:
        # Fallback to dense if no graph node matched
        return [{**idx.items[i], "_score": round(s, 4)} for i, s in idx.search_dense(query, k=k)]

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
    return [{**idx.items[i], "_score": round(s, 4)} for i, s in ranked]
