"""RAG & Verification Ablation Runner (R&D Question B).

Compares isolated architectural factors:
1. Dense-only (v0) vs BM25-only vs Hybrid RRF (v2)
2. Hybrid (v2) vs Hybrid + Skill/Type Rerank (v3)
3. Rerank (v3) vs Outcome-Aware Rerank (v4)
4. Proposal Claim Verification: No Verifier vs Verifier Pruning

Usage:
    python -m evals.runners.ablation
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from evals.runners.rag_eval import _load_dev_queries, _mock_proposal_from_evidence, _ndcg_at_k, _recall_at_k
from rag.index.hybrid_index import get_index
from rag.retriever import retrieve_evidence
from rag.verify import prune_unsupported_claims


def _eval_bm25_only(queries: list[dict[str, Any]]) -> dict[str, float]:
    recalls, ndcgs = [], []
    for job in queries:
        persona = job.get("persona", "default")
        idx = get_index(persona)
        q = f"{job.get('title', '')} {' '.join(job.get('required_skills', []))} {job.get('description', '')[:250]}"
        hits = idx.search_bm25(q, k=10)
        eids = [str(idx.items[i].get("evidence_id", "")) for i, _ in hits]
        gold = set(job.get("gold_evidence_ids", []))
        recalls.append(_recall_at_k(eids, gold, k=5))
        ndcgs.append(_ndcg_at_k(eids, gold, k=10))
    n = max(len(queries), 1)
    return {
        "evidence_recall_at_5": round(sum(recalls) / n, 4),
        "ndcg_at_10": round(sum(ndcgs) / n, 4),
    }


def _eval_variant(variant: str, queries: list[dict[str, Any]]) -> dict[str, float]:
    recalls, ndcgs, pre_unsupp, post_unsupp = [], [], [], []
    for job in queries:
        persona = job.get("persona", "default")
        q = f"{job.get('title', '')} {' '.join(job.get('required_skills', []))} {job.get('description', '')[:250]}"
        ev = retrieve_evidence(q, k=10, persona=persona, variant=variant)
        eids = [str(e.get("evidence_id") or "") for e in ev]
        gold = set(job.get("gold_evidence_ids", []))
        recalls.append(_recall_at_k(eids, gold, k=5))
        ndcgs.append(_ndcg_at_k(eids, gold, k=10))
        draft = _mock_proposal_from_evidence(job, ev[:5])
        _, _, pre_u, post_u = prune_unsupported_claims(draft, ev[:5])
        pre_unsupp.append(pre_u)
        post_unsupp.append(post_u)
    n = max(len(queries), 1)
    return {
        "evidence_recall_at_5": round(sum(recalls) / n, 4),
        "ndcg_at_10": round(sum(ndcgs) / n, 4),
        "unsupported_rate_before": round(sum(pre_unsupp) / n, 4),
        "unsupported_rate_after": round(sum(post_unsupp) / n, 4),
    }


def run_ablation() -> dict[str, Any]:
    queries = _load_dev_queries()
    bm25_metrics = _eval_bm25_only(queries)
    v0 = _eval_variant("v0", queries)
    v2 = _eval_variant("v2", queries)
    v3 = _eval_variant("v3", queries)
    v4 = _eval_variant("v4", queries)
    v8 = _eval_variant("v8", queries)

    return {
        "num_queries": len(queries),
        "factors": {
            "dense_only_v0": v0,
            "bm25_only": bm25_metrics,
            "hybrid_rrf_v2": v2,
            "hybrid_plus_rerank_v3": v3,
            "outcome_aware_v4": v4,
            "corrective_self_rag_v8": v8,
        },
        "deltas": {
            "hybrid_vs_dense_recall_delta": round(v2["evidence_recall_at_5"] - v0["evidence_recall_at_5"], 4),
            "rerank_vs_hybrid_ndcg_delta": round(v3["ndcg_at_10"] - v2["ndcg_at_10"], 4),
            "outcome_vs_rerank_ndcg_delta": round(v4["ndcg_at_10"] - v3["ndcg_at_10"], 4),
            "claim_verifier_unsupported_reduction": round(
                v3["unsupported_rate_before"] - v3["unsupported_rate_after"], 4
            ),
        },
    }


def main() -> None:
    res = run_ablation()
    print("\nRAG Ablation Study Results")
    print("=" * 72)
    for name, m in res["factors"].items():
        print(f"{name:<26} Recall@5={m['evidence_recall_at_5']:.4f}  nDCG@10={m['ndcg_at_10']:.4f}")
    print("\nKey Deltas:")
    for k, v in res["deltas"].items():
        print(f"  {k}: {v:+.4f}")

    out = ROOT / "evals" / "results" / "ablation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
