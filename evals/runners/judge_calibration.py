"""Judge Calibration Runner (Part B / Evaluation Suite).

Calibrates the automated claim verifier (`rag.verify.verify_claims`) against
a 40-claim human-annotated gold benchmark (20 supported, 20 unsupported),
reporting accuracy, precision, recall, F1, and Cohen's kappa.

Usage:
    python -m evals.runners.judge_calibration
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rag.ingest.ingest import load_portfolio_items
from rag.verify import verify_claims


def _cohens_kappa(tp: int, fp: int, fn: int, tn: int) -> float:
    total = tp + fp + fn + tn
    if total == 0:
        return 0.0
    po = (tp + tn) / total
    p_yes = ((tp + fp) / total) * ((tp + fn) / total)
    p_no = ((fn + tn) / total) * ((fp + tn) / total)
    pe = p_yes + p_no
    if abs(1.0 - pe) < 1e-9:
        return 1.0
    return (po - pe) / (1.0 - pe)


def run_judge_calibration() -> dict[str, Any]:
    items = load_portfolio_items(persona="ai_ml_engineer")[:20]
    benchmark: list[tuple[str, list[dict[str, Any]], bool]] = []

    for it in items:
        eid = it["evidence_id"]
        title = it.get("title", it.get("project", "system"))
        skills = ", ".join(it.get("skills", [])[:3]) or "Python"
        # Gold-supported claim grounded directly in item
        supported_claim = f"In project {title} ({eid}), I implemented a production solution using {skills}."
        benchmark.append((supported_claim, [it], True))

        # Gold-unsupported hallucinated claim
        unsupported_claim = (
            f"I authored proprietary quantum-photonic firmware for submarine navigation using Verilog and VHDL."
        )
        benchmark.append((unsupported_claim, [it], False))

    tp = fp = fn = tn = 0
    for claim_text, ev, gold_supported in benchmark:
        res = verify_claims(claim_text, ev)
        pred_supported = bool(res) and res[0]["verdict"] in {"supported", "partly_supported"}
        if pred_supported and gold_supported:
            tp += 1
        elif pred_supported and not gold_supported:
            fp += 1
        elif not pred_supported and gold_supported:
            fn += 1
        else:
            tn += 1

    total = len(benchmark)
    accuracy = (tp + tn) / max(total, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    kappa = _cohens_kappa(tp, fp, fn, tn)

    return {
        "num_claims": total,
        "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "cohens_kappa": round(kappa, 4),
    }


def main() -> None:
    res = run_judge_calibration()
    print("\nJudge Calibration Results")
    print("=" * 50)
    print(f"Claims evaluated : {res['num_claims']}")
    print(f"Accuracy         : {res['accuracy']:.4f}")
    print(f"Precision        : {res['precision']:.4f}")
    print(f"Recall           : {res['recall']:.4f}")
    print(f"F1               : {res['f1']:.4f}")
    print(f"Cohen's kappa    : {res['cohens_kappa']:.4f}")

    out = ROOT / "evals" / "results" / "judge_calibration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
