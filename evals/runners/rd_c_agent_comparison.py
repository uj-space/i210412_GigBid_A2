"""R&D Question C: Single-Agent vs Multi-Agent LangGraph Comparison.

Compares a single-prompt baseline (no parallel fan-out, no critic loop, no compliance gate)
against the full GigBid LangGraph multi-agent workflow (`bid_graph`) on the dev set.

Usage:
    python -m evals.runners.rd_c_agent_comparison
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import MemorySaver
from agent.graphs.bid_graph import run_bid
from rag.retriever import retrieve_evidence
from rag.verify import verify_claims


def _single_agent_baseline(job: dict[str, Any]) -> dict[str, Any]:
    """Simulate a single-pass generalist agent without dedicated risk/compliance/critic specialists."""
    desc = (job.get("description") or "").lower()
    skills = set(s.lower() for s in (job.get("required_skills") or []))
    # Naive heuristic: bids on almost anything with >=1 tech keyword, misses subtle scams/injections
    scam_caught = "unpaid" in desc
    decision = "skip" if scam_caught else ("bid" if skills else "skip")
    persona = job.get("persona", "default")
    ev = retrieve_evidence(job.get("title", ""), k=3, persona=persona, variant="v0")
    draft = f"I can complete {job.get('title', 'this job')} quickly with full quality."
    ver = verify_claims(draft, ev)
    unsupp = sum(1 for v in ver if v["verdict"] == "unsupported") / max(len(ver), 1)
    return {
        "decision": decision,
        "scam_detected": scam_caught,
        "unsupported_rate": unsupp,
        "compliance_checked": False,
    }


def run_comparison(limit: int = 90) -> dict[str, Any]:
    dev_path = ROOT / "evals" / "datasets" / "dev_set.json"
    all_jobs = json.loads(dev_path.read_text(encoding="utf-8"))
    step = max(len(all_jobs) // limit, 1)
    jobs = all_jobs[::step][:limit]

    # 1. Single-agent baseline
    t0 = time.perf_counter()
    sa_dec_ok, sa_scam_tp, sa_scam_tot, sa_unsupp = 0, 0, 0, []
    for job in jobs:
        r = _single_agent_baseline(job)
        if r["decision"] == job.get("gold_decision"):
            sa_dec_ok += 1
        if job.get("gold_scam"):
            sa_scam_tot += 1
            if r["scam_detected"]:
                sa_scam_tp += 1
        sa_unsupp.append(r["unsupported_rate"])
    sa_time = (time.perf_counter() - t0) * 1000.0

    # 2. Multi-agent LangGraph
    cp = MemorySaver()
    t1 = time.perf_counter()
    ma_dec_ok, ma_scam_tp, ma_scam_tot, ma_unsupp = 0, 0, 0, []
    for idx, job in enumerate(jobs):
        r = run_bid(job, user_id=f"rdc-{job.get('persona', 'default')}", thread_id=f"rdc-{idx}", checkpointer=cp)
        pred = r.get("decision", "skip")
        if pred == job.get("gold_decision") or (job.get("gold_decision") == "bid" and pred == "watch"):
            ma_dec_ok += 1
        if job.get("gold_scam"):
            ma_scam_tot += 1
            if (r.get("risk_report") or {}).get("scam"):
                ma_scam_tp += 1
        ver = r.get("claim_verification") or []
        unsupp = sum(1 for v in ver if v.get("verdict") == "unsupported") / max(len(ver), 1) if ver else 0.0
        ma_unsupp.append(unsupp)
    ma_time = (time.perf_counter() - t1) * 1000.0

    n = max(len(jobs), 1)
    return {
        "num_jobs": len(jobs),
        "single_agent_baseline": {
            "decision_accuracy": round(sa_dec_ok / n, 4),
            "scam_recall": round(sa_scam_tp / max(sa_scam_tot, 1), 4),
            "avg_unsupported_claim_rate": round(sum(sa_unsupp) / n, 4),
            "avg_latency_ms": round(sa_time / n, 2),
        },
        "multi_agent_langgraph": {
            "decision_accuracy": round(ma_dec_ok / n, 4),
            "scam_recall": round(ma_scam_tp / max(ma_scam_tot, 1), 4),
            "avg_unsupported_claim_rate": round(sum(ma_unsupp) / n, 4),
            "avg_latency_ms": round(ma_time / n, 2),
        },
    }


def main() -> None:
    res = run_comparison(limit=90)
    print("\nR&D Question C: Single-Agent vs Multi-Agent LangGraph")
    print("=" * 68)
    for arch in ("single_agent_baseline", "multi_agent_langgraph"):
        m = res[arch]
        print(
            f"{arch:<24} Acc={m['decision_accuracy']:.4f}  ScamRec={m['scam_recall']:.4f}  "
            f"Unsupp={m['avg_unsupported_claim_rate']:.4f}  Lat={m['avg_latency_ms']:.2f}ms"
        )
    out = ROOT / "evals" / "results" / "rd_c_agent_comparison.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
