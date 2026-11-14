from __future__ import annotations

from typing import Any


def retrieve(query, k=5, persona="default"):
    from rag.variants.v0_naive import retrieve as v0
    hypo = f"I have built {query or 'this'} using Python and delivered measurable results."
    return v0(hypo, k=k, persona=persona)
