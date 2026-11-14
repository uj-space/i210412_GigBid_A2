from __future__ import annotations

from typing import Any
import importlib

_VARIANTS = {
    "v0": "rag.variants.v0_naive",
    "v1": "rag.variants.v1_requirement",
    "v2": "rag.variants.v2_hybrid",
    "v3": "rag.variants.v3_rerank",
    "v4": "rag.variants.v4_outcome",
    "v5": "rag.variants.v5_multivector",
    "v6": "rag.variants.v6_contextual",
    "v7": "rag.variants.v7_hyde",
    "v8": "rag.variants.v8_corrective",
    "v9": "rag.variants.v9_graphrag",
}
_ACTIVE = "v0"


def set_variant(variant_id):
    global _ACTIVE
    if variant_id not in _VARIANTS:
        raise ValueError(f"unknown variant {variant_id}")
    _ACTIVE = variant_id


def retrieve_evidence(query, k=5, persona="default", variant=None):
    vid = variant or _ACTIVE
    mod = importlib.import_module(_VARIANTS[vid])
    fn = getattr(mod, "retrieve", None)
    if fn is None:
        return []
    return fn(query, k=k, persona=persona)
