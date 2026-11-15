"""Worker module: scheduled scouting, degraded-queue retry, and idempotent agent runs."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import time
from typing import Any, List

from agent.graphs.bid_graph import run_bid
from agent.marketplace_port import build_port
from agent.mcp_client import get_degraded_queue, is_marketplace_degraded


def run_scouting_cycle(
    user_id: str = "default",
    saved_searches: List[str] | None = None,
    limit_per_query: int = 5,
) -> list[dict[str, Any]]:
    """Run one scouting cycle: pull new jobs and analyze each idempotently."""
    if is_marketplace_degraded():
        queued = get_degraded_queue()
        return [{"status": "degraded_skipped", "queued_count": len(queued)}]

    port = build_port(user_id=user_id)
    searches = saved_searches or ["python developer", "react developer", "data analyst"]
    outcomes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for query in searches:
        try:
            jobs = port.search_jobs(query=query, limit=limit_per_query)
            for job in jobs:
                if job.job_id in seen_ids:
                    continue
                seen_ids.add(job.job_id)
                job_dict = asdict(job)
                thread_id = f"worker-{job.job_id}"
                res = run_bid(job_dict, user_id=user_id, thread_id=thread_id)
                outcomes.append({"job_id": job.job_id, "decision": res.get("decision")})
        except Exception as exc:
            outcomes.append({"query": query, "error": str(exc)})
    return outcomes


def run_forever(poll_interval_seconds: int = 300) -> None:
    """Run scouting loop forever (for worker container)."""
    print(f"Worker started. Polling every {poll_interval_seconds}s...")
    while True:
        try:
            res = run_scouting_cycle()
            print(f"Scouting cycle processed {len(res)} items")
        except Exception as exc:
            print(f"Scouting cycle failed: {exc}")
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GigBid Background Worker")
    parser.add_argument("--once", action="store_true", help="Run a single scouting cycle and exit")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds")
    args = parser.parse_args()
    if args.once:
        out = run_scouting_cycle(limit_per_query=2)
        print(f"Single cycle complete: {len(out)} jobs processed")
    else:
        run_forever(args.interval)
