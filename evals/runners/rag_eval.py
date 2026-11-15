"""RAG Evaluation Script (Part B / R&D Question B).

Evaluates all 10 retrieval variants (v0-v9) on the dev set jobs with gold
evidence IDs, computing Evidence Recall@5, nDCG@10, MRR, claim verification
unsupported rate (before/after pruning), and retrieval latency.

Usage:
    python -m evals.runners.rag_eval
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rag.retriever import retrieve_evidence, set_variant
from rag.verify import prune_unsupported_claims

VARIANTS = ["v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]


def _load_dev_queries() -> list[dict[str, Any]]:
    dev_path = ROOT / "evals" / "datasets" / "dev_set.json"
    jobs = json.loads(dev_path.read_text(encoding="utf-8"))
    return [j for j in jobs if j.get("gold_decision") == "bid" and j.get("gold_evidence_ids")]


def _recall_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int = 5) -> float:
    if not gold_ids:
        return 0.0
    hits = len(set(retrieved_ids[:k]) & gold_ids)
    return hits / len(gold_ids)


def _ndcg_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int = 10) -> float:
    if not gold_ids:
        return 0.0
    dcg = 0.0
    for rank, eid in enumerate(retrieved_ids[:k], start=1):
        if eid in gold_ids:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(len(gold_ids), k)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def _mrr(retrieved_ids: list[str], gold_ids: set[str]) -> float:
    for rank, eid in enumerate(retrieved_ids, start=1):
        if eid in gold_ids:
            return 1.0 / rank
    return 0.0


def _mock_proposal_from_evidence(job: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    """Construct a proposal draft mixing grounded evidence citations with one ungrounded claim."""
    skills = ", ".join(job.get("required_skills", [])[:4]) or "Python"
    if evidence:
        top = evidence[0]
        eid = top.get("evidence_id", "unknown")
        title = top.get("title", top.get("project", "prior project"))
        return (
            f"I previously delivered {title} ({eid}) using {skills} with verified production results.\n"
            f"I also hold a secret NASA orbital certification from 2099 that is unrelated to this portfolio."
        )
    return (
        f"I can build this {job.get('title', 'project')} using {skills}.\n"
        f"I also hold a secret NASA orbital certification from 2099."
    )


def run_rag_eval(limit_per_persona: int | None = None) -> dict[str, Any]:
    """Evaluate all 10 RAG variants on dev set queries with gold evidence IDs."""
    queries = _load_dev_queries()
    if limit_per_persona is not None:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for j in queries:
            p = j.get("persona", "default")
            if len(grouped.get(p, [])) < limit_per_persona:
                grouped.setdefault(p, []).append(j)
        queries = [j for sub in grouped.values() for j in sub]

    results: dict[str, Any] = {"num_queries": len(queries), "variants": {}}

    for vid in VARIANTS:
        set_variant(vid)
        recalls: list[float] = []
        ndcgs: list[float] = []
        mrrs: list[float] = []
        before_rates: list[float] = []
        after_rates: list[float] = []
        latencies_ms: list[float] = []
        per_persona: dict[str, list[float]] = {}

        for job in queries:
            persona = job.get("persona", "default")
            query_text = f"{job.get('title', '')} {' '.join(job.get('required_skills', []))} {job.get('description', '')[:250]}"
            gold_ids = set(job.get("gold_evidence_ids", []))

            t0 = time.perf_counter()
            ev_10 = retrieve_evidence(query_text, k=10, persona=persona, variant=vid)
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

            retrieved_ids = [str(e.get("evidence_id") or e.get("id") or "") for e in ev_10]
            rec5 = _recall_at_k(retrieved_ids, gold_ids, k=5)
            recalls.append(rec5)
            ndcgs.append(_ndcg_at_k(retrieved_ids, gold_ids, k=10))
            mrrs.append(_mrr(retrieved_ids, gold_ids))
            per_persona.setdefault(persona, []).append(rec5)

            draft = _mock_proposal_from_evidence(job, ev_10[:5])
            _, _, before_u, after_u = prune_unsupported_claims(draft, ev_10[:5])
            before_rates.append(before_u)
            after_rates.append(after_u)

        n = max(len(queries), 1)
        results["variants"][vid] = {
            "evidence_recall_at_5": round(sum(recalls) / n, 4),
            "ndcg_at_10": round(sum(ndcgs) / n, 4),
            "mrr": round(sum(mrrs) / n, 4),
            "unsupported_rate_before_verify": round(sum(before_rates) / n, 4),
            "unsupported_rate_after_verify": round(sum(after_rates) / n, 4),
            "avg_latency_ms": round(sum(latencies_ms) / n, 3),
            "per_persona_recall_at_5": {
                p: round(sum(vals) / max(len(vals), 1), 4)
                for p, vals in sorted(per_persona.items())
            },
        }

    best_vid = max(
        results["variants"],
        key=lambda v: (results["variants"][v]["ndcg_at_10"], results["variants"][v]["evidence_recall_at_5"]),
    )
    results["best_variant"] = best_vid
    return results


def main() -> None:
    results = run_rag_eval()
    print(f"\nRAG Variant Evaluation Results (n={results['num_queries']} dev queries)")
    print("=" * 95)
    print(
        f"{'Variant':<8} {'Recall@5':<10} {'nDCG@10':<10} {'MRR':<8} "
        f"{'Unsupp(Pre)':<13} {'Unsupp(Post)':<13} {'Latency(ms)':<12}"
    )
    print("-" * 95)
    for vid, r in results["variants"].items():
        print(
            f"{vid:<8} {r['evidence_recall_at_5']:<10.4f} {r['ndcg_at_10']:<10.4f} {r['mrr']:<8.4f} "
            f"{r['unsupported_rate_before_verify']:<13.4f} {r['unsupported_rate_after_verify']:<13.4f} "
            f"{r['avg_latency_ms']:<12.3f}"
        )
    print(f"\nBest variant by nDCG@10: {results['best_variant']}")

    out = ROOT / "evals" / "results" / "rag_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Results saved to {out}")


if __name__ == "__main__":
    main()
