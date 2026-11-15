"""V7: HyDE (Hypothetical Document Embeddings — generate ideal proposal snippet, then retrieve)."""
from __future__ import annotations

from rag.variants.v2_hybrid import retrieve as v2_retrieve


def _hypothetical_proposal(query: str) -> str:
    return (
        f"Case Study delivered production system for {query}. "
        f"Implemented architecture, testing, deployment, and measurable client outcome won."
    )


def retrieve(query: str, k: int = 5, persona: str = "default"):
    hyde_query = f"{query} {_hypothetical_proposal(query)}"
    return v2_retrieve(hyde_query, k=k, persona=persona)
