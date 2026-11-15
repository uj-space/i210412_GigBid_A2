"""GigBid FastAPI backend entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.mcp_client import is_marketplace_degraded
from apps.api.routers import analytics, approvals, auth, jobs, messages, proposals, runs
from apps.api.schemas.api import HealthResponse

app = FastAPI(title="GigBid API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, jobs.router, proposals.router, approvals.router, messages.router, runs.router, analytics.router):
    app.include_router(r)


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
async def health():
    return {
        "status": "ok",
        "service": "gigbid-api",
        "marketplace_degraded": is_marketplace_degraded(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
