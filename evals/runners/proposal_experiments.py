"""X2: Controlled Proposal Strategy Experiment in GigSim.

Compares 3 proposal styles (short_punchy, evidence_bulleted, detailed_technical)
across personas using verified portfolio evidence and claim verification.

Usage:
    python -m evals.runners.proposal_experiments
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rag.retriever import retrieve_evidence
from rag.verify import prune_unsupported_claims


def _render_style(style: str, job: dict[str, Any], ev: list[dict[str, Any]]) -> str:
    skills = ", ".join(job.get("required_skills", [])[:3]) or "Python"
    e0 = ev[0] if ev else {"evidence_id": "none", "title": "prior system", "summary": "delivered production code"}
    eid = e0.get("evidence_id", "none")
    title = e0.get("title", "prior project")
    summary = e0.get("summary", "")

    if style == "short_punchy":
        return f"Built {title} ({eid}) using {skills}. Ready to deliver production code and tests immediately."
    if style == "evidence_bulleted":
        bullets = "\n".join(f"- {e.get('title')} ({e.get('evidence_id')}): {e.get('summary', '')[:90]}" for e in ev[:3])
        return f"Relevant verified work for {job.get('title')} ({skills}):\n{bullets}"
    return (
        f"Architecture Plan for {job.get('title')}:\n"
        f"1. Relevant experience: {title} ({eid}) — {summary}\n"
        f"2. Stack alignment: {skills} with automated tests and CI verification."
    )


def run_proposal_experiments() -> dict[str, Any]:
    dev_jobs = json.loads((ROOT / "evals" / "datasets" / "dev_set.json").read_text(encoding="utf-8"))
    sample_jobs = [j for j in dev_jobs if j.get("gold_decision") == "bid"][:30]
    styles = ("short_punchy", "evidence_bulleted", "detailed_technical")
    summary: dict[str, Any] = {}

    for style in styles:
        word_counts = []
        unsupported_rates = []
        citation_counts = []
        for job in sample_jobs:
            persona = job.get("persona", "default")
            ev = retrieve_evidence(f"{job.get('title')} {' '.join(job.get('required_skills', []))}", k=3, persona=persona, variant="v3")
            draft = _render_style(style, job, ev)
            cleaned, ver, _, after_u = prune_unsupported_claims(draft, ev)
            word_counts.append(len(cleaned.split()))
            unsupported_rates.append(after_u)
            citation_counts.append(sum(1 for e in ev if e.get("evidence_id", "") in cleaned))
        n = max(len(sample_jobs), 1)
        summary[style] = {
            "avg_word_count": round(sum(word_counts) / n, 1),
            "avg_citations_per_proposal": round(sum(citation_counts) / n, 2),
            "unsupported_rate_after_verify": round(sum(unsupported_rates) / n, 4),
        }

    return {"num_jobs": len(sample_jobs), "strategies": summary}


def main() -> None:
    res = run_proposal_experiments()
    print("\nX2 Proposal Strategy Experiment")
    print("=" * 60)
    print(json.dumps(res, indent=2))
    out = ROOT / "evals" / "results" / "proposal_experiments.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
