"""End-to-End GigSim Outcome Simulation Runner.

Runs the full LangGraph bid workflow + simulated human approval across all 3 personas
on dev-set jobs inside GigSim, measuring reply rate, interview rate, hire rate,
Connects ROI, and safety incident rate.

Usage:
    python -m evals.runners.gigsim_outcomes
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from agent.graphs.bid_graph import build_bid_graph, run_bid


def run_gigsim_outcomes(jobs_per_persona: int = 10) -> dict[str, Any]:
    dev_jobs = json.loads((ROOT / "evals" / "datasets" / "dev_set.json").read_text(encoding="utf-8"))
    cp = MemorySaver()
    graph = build_bid_graph(checkpointer=cp)

    per_persona: dict[str, dict[str, Any]] = {}
    total_submitted = 0
    total_replies = 0
    total_interviews = 0
    total_hires = 0
    total_connects = 0
    safety_incidents = 0

    for persona in ("ai_ml_engineer", "fullstack_web_dev", "data_analyst"):
        p_jobs = [j for j in dev_jobs if j.get("persona") == persona and j.get("gold_decision") == "bid"][:jobs_per_persona]
        p_sub = p_rep = p_int = p_hire = p_conn = 0

        for idx, job in enumerate(p_jobs):
            tid = f"gs-{persona}-{idx}"
            res = run_bid(job, user_id=f"gs-{persona}-{idx}", thread_id=tid, checkpointer=cp)
            if "__interrupt__" in res:
                resumed = graph.invoke(Command(resume={"action": "approved"}), config={"configurable": {"thread_id": tid}})
                if not (resumed.get("compliance_verdict") or {}).get("passed", True):
                    safety_incidents += 1
                out = resumed.get("outcome") or {}
                if out.get("submitted") or out.get("submission_id"):
                    p_sub += 1
                    p_conn += int(out.get("connects_spent", job.get("connects_cost", 6)) or 6)
                    sim = out.get("simulated_outcome") or {}
                    if sim.get("replied") or sim.get("hired"):
                        p_rep += 1
                    if sim.get("replied") and sim.get("skill_hits", 0) >= 2:
                        p_int += 1
                    if sim.get("hired"):
                        p_hire += 1

        total_submitted += p_sub
        total_replies += p_rep
        total_interviews += p_int
        total_hires += p_hire
        total_connects += p_conn
        per_persona[persona] = {
            "submitted": p_sub,
            "replies": p_rep,
            "interviews": p_int,
            "hires": p_hire,
            "reply_rate": round(p_rep / max(p_sub, 1), 4),
            "hire_rate": round(p_hire / max(p_sub, 1), 4),
            "connects_spent": p_conn,
        }

    return {
        "total_submitted": total_submitted,
        "reply_rate": round(total_replies / max(total_submitted, 1), 4),
        "interview_rate": round(total_interviews / max(total_submitted, 1), 4),
        "hire_rate": round(total_hires / max(total_submitted, 1), 4),
        "total_connects_spent": total_connects,
        "safety_incidents": safety_incidents,
        "per_persona": per_persona,
    }


def main() -> None:
    res = run_gigsim_outcomes(jobs_per_persona=10)
    print("\nGigSim End-to-End Outcome Simulation")
    print("=" * 60)
    print(json.dumps(res, indent=2))
    out = ROOT / "evals" / "results" / "gigsim_outcomes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
