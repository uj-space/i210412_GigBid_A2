"""Worker module: scheduled scouting and long-running agent runs.

Runs scouting jobs from saved searches on a schedule and processes
long-running agent runs idempotently.
"""
from __future__ import annotations

import os
import time
import uuid
import json
from typing import Any, Dict, List

from agent.graphs.bid_graph import run_bid
from agent.marketplace_port import build_port


def run_scouting_cycle(user_id: str = "default", saved_searches: List[str] | None = None):
    """Run a scouting cycle: pull new jobs and analyze each one."""
    port = build_port()
    searches = saved_searches or ["python developer", "react developer", "data analyst"]
    
    for query in searches:
        try:
            jobs = port.search_jobs(query=query, limit=10)
            for job in jobs:
                job_dict = {
                    "job_id": job.job_id,
                    "title": job.title,
                    "description": job.description,
                    "required_skills": job.required_skills,
                    "budget_min": job.budget_min,
                    "budget_max": job.budget_max,
                    "currency": job.currency,
                    "connects_cost": job.connects_cost,
                    "client_id": job.client_id,
                    "warning_signals": job.warning_signals,
                }
                # Run bid analysis (idempotent via thread_id based on job_id)
                thread_id = f"worker-{job.job_id}"
                try:
                    result = run_bid(job_dict, user_id=user_id, thread_id=thread_id)
                    print(f"Analyzed job {job.job_id}: decision={result.get('decision')}")
                except Exception as e:
                    print(f"Error analyzing job {job.job_id}: {e}")
        except Exception as e:
            print(f"Scouting error for query '{query}': {e}")


def run_forever(poll_interval_seconds: int = 300):
    """Run scouting loop forever (for worker process)."""
    print(f"Worker started. Polling every {poll_interval_seconds}s...")
    while True:
        try:
            run_scouting_cycle()
        except Exception as e:
            print(f"Scouting cycle failed: {e}")
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    import sys
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    run_forever(interval)