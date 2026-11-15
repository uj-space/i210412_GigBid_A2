"""Agent runs & SSE streaming router."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from apps.api.routers.jobs import RUN_RECORDS
from apps.api.streaming import stream_bid_run

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs")
async def list_runs():
    return {"runs": list(RUN_RECORDS.values())}


@router.get("/runs/{thread_id}/stream")
async def stream_run(thread_id: str):
    return StreamingResponse(stream_bid_run(thread_id), media_type="text/event-stream")
