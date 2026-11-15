"""Unit tests for Part B: RAG ingestion, 10 retrieval variants (v0-v9), and claim verification."""
from __future__ import annotations

import pytest

from rag.index.hybrid_index import get_index, invalidate_index
from rag.ingest import ingest
from rag.retriever import retrieve_evidence, set_variant
from rag.verify import prune_unsupported_claims, split_claims, unsupported_rate, verify_claims


def test_load_portfolio_items_has_required_metadata():
    items = ingest.load_portfolio_items(persona="ai_ml_engineer")
    assert len(items) >= 50
    sample = items[0]
    for field in ("evidence_id", "persona", "type", "project", "skills", "date", "client_industry", "outcome", "text"):
        assert field in sample, f"Missing metadata field: {field}"


def test_incremental_indexing_adds_item_immediately():
    custom_id = "inc-test-quantum-999"
    new_item = {
        "evidence_id": custom_id,
        "persona": "ai_ml_engineer",
        "type": "case_study",
        "title": "Xylophone Telemetry Pipeline",
        "summary": "Built custom xylophone acoustic telemetry pipeline with PyTorch.",
        "skills": ["XylophoneTelemetry", "PyTorch"],
        "outcome": "won",
    }
    try:
        ingest.add_portfolio_item(new_item)
        results = retrieve_evidence("XylophoneTelemetry acoustic pipeline", k=5, persona="ai_ml_engineer", variant="v2")
        ids = [r["evidence_id"] for r in results]
        assert custom_id in ids
    finally:
        if new_item in ingest._INCREMENTAL_ITEMS:
            ingest._INCREMENTAL_ITEMS.remove(new_item)
        invalidate_index()


@pytest.mark.parametrize("vid", ["v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"])
def test_all_ten_rag_variants_retrieve_evidence(vid: str):
    set_variant(vid)
    res = retrieve_evidence("Python LangGraph FastAPI RAG pipeline", k=5, persona="ai_ml_engineer")
    assert isinstance(res, list)
    assert len(res) > 0
    assert all("evidence_id" in r for r in res)


def test_set_variant_rejects_unknown():
    with pytest.raises(ValueError):
        set_variant("v99")


def test_claim_verification_and_pruning():
    ev = retrieve_evidence("Python LangGraph FastAPI", k=3, persona="ai_ml_engineer", variant="v3")
    eid = ev[0]["evidence_id"]
    skills = ", ".join(ev[0].get("skills", [])[:2]) or "Python"
    draft = (
        f"I delivered {ev[0]['title']} ({eid}) using {skills}.\n"
        f"I also built classified Mars rover propulsion firmware in Ada."
    )
    claims = split_claims(draft)
    assert len(claims) == 2

    ver = verify_claims(draft, ev)
    assert ver[0]["verdict"] == "supported"
    assert ver[1]["verdict"] == "unsupported"
    assert unsupported_rate(ver) == 0.5

    cleaned, after_ver, before_u, after_u = prune_unsupported_claims(draft, ev)
    assert before_u == 0.5
    assert after_u == 0.0
    assert "Mars rover" not in cleaned
    assert eid in cleaned


def test_hybrid_index_methods():
    idx = get_index("fullstack_web_dev")
    assert len(idx.search_dense("React TypeScript", k=3)) == 3
    assert len(idx.search_bm25("React TypeScript", k=3)) == 3
    assert len(idx.search_contextual("React TypeScript", k=3)) == 3
    assert len(idx.search_multivector("React TypeScript", k=3)) == 3
