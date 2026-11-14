from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    items = v0(query, k=k, persona=persona)
    if not items:
        first = (query or "").split()
        items = v0(first[0] if first else query, k=k, persona=persona)
    return items
