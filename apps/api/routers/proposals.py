"""Proposals & paragraph regeneration router."""
from __future__ import annotations

from fastapi import APIRouter
from apps.api.routers.jobs import RUN_RECORDS

router = APIRouter(prefix="/api", tags=["proposals"])


@router.get("/proposals/{job_id}")
async def get_proposal_for_job(job_id: str):
    for rec in reversed(list(RUN_RECORDS.values())):
        if rec.get("job_id") == job_id or rec.get("thread_id") == job_id:
            return {"thread_id": rec["thread_id"], "result": rec["result"]}
    return {"thread_id": None, "result": None}


@router.post("/proposals/regenerate")
async def regenerate_paragraph(payload: dict):
    text = payload.get("cover_letter", "")
    evidence = payload.get("evidence", []) or []
    if evidence:
        e = evidence[0]
        eid = e.get("evidence_id") or "ev-1"
        para = f"In {e.get('project', 'a recent project')} [{eid}], {e.get('summary', 'delivered production results')}."
        return {"cover_letter": f"{text}\n\n{para}".strip()}
    return {"cover_letter": text}
