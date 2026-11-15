from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    items = v0(query, k=k, persona=persona)
    for it in items:
        it["text"] = f"Context: relates to {query or 'the job'}.
" + it.get("text", "")
    return items
