from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    from rag.variants.v1_requirement import retrieve as v1
    a = v0(query, k=k, persona=persona)
    b = v1(query, k=k, persona=persona)
    fused = {}
    for rank, it in enumerate(a):
        fused.setdefault(it.get("evidence_id") or it.get("id"), dict(it, _rrf=1.0 / (rank + 1)))
    for rank, it in enumerate(b):
        eid = it.get("evidence_id") or it.get("id")
        cur = fused.setdefault(eid, dict(it, _rrf=0.0))
        cur["_rrf"] = cur.get("_rrf", 0) + 1.0 / (rank + 1)
    return [it for _, it in sorted(fused.items(), key=lambda kv: kv[1].get("_rrf", 0), reverse=True)][:k]
