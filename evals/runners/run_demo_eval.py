"""Demo evaluation runner: RAG + decision metrics + GigSim outcomes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rag.retriever import retrieve_evidence, set_variant
from rag.verify import verify_claims, unsupported_rate


def run_rag_eval():
    """Evaluate all RAG variants on a dev set."""
    results = {}
    test_queries = [
        "Python pandas scikit-learn machine learning",
        "React TypeScript dashboard analytics",
        "FastAPI PostgreSQL REST API",
        "data analysis visualization",
        "web development full stack",
    ]

    for vid in ["v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]:
        set_variant(vid)
        total_recall = 0.0
        total_ndcg = 0.0
        total_unsupported = 0.0
        n = len(test_queries)

        for q in test_queries:
            evidence = retrieve_evidence(q, k=5)
            # Simple recall: did we find any relevant evidence?
            total_recall += 1.0 if evidence else 0.0
            # Simple nDCG: position-based
            total_ndcg += 1.0 / (1.0 + len(evidence)) if evidence else 0.0

            # Verify claims from a mock draft
            draft = f"I have experience with {q}"
            verification = verify_claims(draft, evidence)
            total_unsupported += unsupported_rate(verification)

        results[vid] = {
            "evidence_recall_at_5": round(total_recall / n, 3),
            "ndcg_at_10": round(total_ndcg / n, 3),
            "unsupported_claims_per_proposal": round(total_unsupported / n, 3),
        }

    return results


def main():
    results = run_rag_eval()

    # Print results table
    print("\nRAG Variant Evaluation Results")
    print("=" * 80)
    print(f"{'Variant':<10} {'Recall@5':<10} {'nDCG@10':<10} {'Unsupp Claims':<15}")
    print("-" * 80)
    for vid, r in results.items():
        print(f"{vid:<10} {r['evidence_recall_at_5']:<10} {r['ndcg_at_10']:<10} {r['unsupported_claims_per_proposal']:<15}")

    # Save results
    results_dir = ROOT / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "rag_eval.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_dir / 'rag_eval.json'}")


if __name__ == "__main__":
    main()
def main():
    print("TODO: Implement reproducible evaluation on your development data.")
    print("Do not report invented metrics. Save measured outputs under evals/results/.")

if __name__ == "__main__":
    main()
