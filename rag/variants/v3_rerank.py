"""V3: Two-stage retrieval with cross-encoder / exact-skill & bigram reranking."""
from __future__ import annotations

import re
from rag.index.hybrid_index import get_index
from rag.variants.v2_hybrid import retrieve as v2_retrieve


def _rerank_score(query: str, item: dict) -> float:
    q_toks = set(re.findall(r"[a-z0-9_+#.-]+", (query or "").lower()))
    skills = {s.lower() for s in (item.get("skills") or [])}
    text_toks = set(re.findall(r"[a-z0-9_+#.-]+", (item.get("text") or "").lower()))
    skill_overlap = len(q_toks & skills) / max(len(skills), 1)
    lexical_overlap = len(q_toks & text_toks) / max(len(q_toks), 1)
    type_bonus = 0.25 if item.get("type") == "case_study" else (0.15 if item.get("type") == "repo_code" else 0.0)
    return float(item.get("_score", 0.0)) + 0.55 * skill_overlap + 0.35 * lexical_overlap + type_bonus


def retrieve(query: str, k: int = 5, persona: str = "default"):
    # Pull larger pool from hybrid V2, then rerank
    pool = v2_retrieve(query, k=max(k * 4, 20), persona=persona)
    if not pool:
        idx = get_index(persona)
        pool = idx.items[:k]
    scored = sorted(pool, key=lambda it: _rerank_score(query, it), reverse=True)
    return scored[:k]
