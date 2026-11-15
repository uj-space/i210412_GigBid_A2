"""SSE streaming bridge to LangGraph run events."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from agent.graphs.bid_graph import build_bid_graph


async def stream_bid_run(thread_id: str, job: dict | None = None, user_id: str = "ai_ml_engineer") -> AsyncGenerator[str, None]:
    yield f"data: {json.dumps({'type': 'run_start', 'thread_id': thread_id})}\n\n"
    graph = build_bid_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        if job:
            init_state = {
                "thread_id": thread_id,
                "mode": "bid",
                "user_id": user_id,
                "job": job,
                "saved_searches": [""],
                "step_count": 0,
                "token_budget": 12000,
                "revision_count": 0,
                "errors": [],
                "trace_id": f"trace-{thread_id}",
                "tool_calls": [],
            }
            async for event in graph.astream(init_state, config=config, stream_mode="updates"):
                for node_name, node_out in event.items():
                    yield f"data: {json.dumps({'type': 'node_update', 'node': node_name, 'keys': list((node_out or {}).keys()) if isinstance(node_out, dict) else []})}\n\n"
                    await asyncio.sleep(0.02)
        else:
            snap = graph.get_state(config)
            yield f"data: {json.dumps({'type': 'state_snapshot', 'next': list(snap.next or ()), 'values_keys': list((snap.values or {}).keys())})}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
    yield f"data: {json.dumps({'type': 'run_end', 'thread_id': thread_id})}\n\n"
