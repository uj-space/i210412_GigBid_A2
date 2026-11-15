"""Decision Evaluation Script.

Evaluates bid-or-skip decisions, scam detection, and pricing accuracy
on the dev set.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.graphs.bid_graph import run_bid


def run_decision_eval():
    """Evaluate bid decisions on dev set jobs."""
    dev_jobs = [
        {
            "job_id": "dev-001",
            "title": "Build ML churn prediction model",
            "description": "Need ML engineer for customer churn prediction using Python/pandas/scikit-learn. Fixed price $500.",
            "required_skills": ["Python", "pandas", "scikit-learn"],
            "budget": {"min": 500, "max": 2000},
            "connects_cost": 6,
            "warning_signals": [],
            "client_id": "client-001",
        },
        {
            "job_id": "dev-002",
            "title": "React dashboard for analytics",
            "description": "Build a modern dashboard with React, TypeScript, D3.js charts.",
            "required_skills": ["React", "TypeScript", "D3.js"],
            "budget": {"min": 800, "max": 3000},
            "connects_cost": 8,
            "warning_signals": [],
            "client_id": "client-002",
        },
        {
            "job_id": "dev-003",
            "title": "SCAM - Free work needed",
            "description": "Unpaid test project first. Need work done for free.",
            "required_skills": ["Python", "React"],
            "budget": {"min": 0, "max": 0},
            "connects_cost": 4,
            "warning_signals": ["unpaid_work"],
            "client_id": "client-003",
        },
        {
            "job_id": "dev-004",
            "title": "FastAPI API development",
            "description": "Create REST APIs for SaaS platform with PostgreSQL.",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "budget": {"min": 1000, "max": 4000},
            "connects_cost": 10,
            "warning_signals": [],
            "client_id": "client-004",
        },
    ]

    results = []
    for job in dev_jobs:
        result = run_bid(job, user_id="eval-user", thread_id=f"eval-{job['job_id']}")
        results.append({
            "job_id": job["job_id"],
            "title": job["title"],
            "decision": result.get("decision", "unknown"),
            "risk_score": result.get("risk_report", {}).get("score", 0),
            "fit_score": result.get("fit_report", {}).get("score", 0),
            "scam_detected": result.get("risk_report", {}).get("scam", False),
            "is_scam_job": bool(job.get("warning_signals")),
            "price": result.get("price_quote", {}).get("suggested_bid", 0),
            "budget_min": job.get("budget", {}).get("min", 0),
            "budget_max": job.get("budget", {}).get("max", 0),
        })

    # Calculate metrics
    total = len(results)
    scam_caught = sum(1 for r in results if r["is_scam_job"] and r["scam_detected"])
    total_scams = sum(1 for r in results if r["is_scam_job"])
    scam_precision = scam_caught / total_scams if total_scams > 0 else 0

    price_in_band = sum(
        1 for r in results
        if not r["is_scam_job"] and r["budget_min"] <= r["price"] <= r["budget_max"]
    )
    non_scam = total - total_scams
    price_accuracy = price_in_band / non_scam if non_scam > 0 else 0

    metrics = {
        "total_jobs": total,
        "total_scams": total_scams,
        "scam_detected": scam_caught,
        "scam_precision": round(scam_precision, 3),
        "price_in_band": price_in_band,
        "non_scam_jobs": non_scam,
        "price_accuracy": round(price_accuracy, 3),
    }

    return results, metrics


def main():
    results, metrics = run_decision_eval()

    print("\nDecision Evaluation Results")
    print("=" * 80)
    print(f"{'Job ID':<10} {'Decision':<10} {'Risk':<8} {'Fit':<8} {'Scam':<8} {'Price':<8} {'Budget':<10}")
    print("-" * 80)
    for r in results:
        print(f"{r['job_id']:<10} {r['decision']:<10} {r['risk_score']:<8.2f} {r['fit_score']:<8.2f} "
              f"{str(r['scam_detected']):<8} {r['price']:<8} {f'{r[\"budget_min\"]}-{r[\"budget_max\"]}':<10}")

    print("\nMetrics:")
    print("-" * 40)
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    results_dir = Path(__file__).resolve().parents[2] / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "decision_eval.json", "w") as f:
        json.dump({"results": results, "metrics": metrics}, f, indent=2)
    print(f"\nResults saved to {results_dir / 'decision_eval.json'}")


if __name__ == "__main__":
    main()