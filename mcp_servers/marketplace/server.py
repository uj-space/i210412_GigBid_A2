"""Marketplace MCP server (wrapping GigSim/Upwork via MarketplacePort).

Features (A2):
- Read tools: search_jobs, get_job, get_client_history, get_connects_balance, list_messages
- Write tools: create_proposal_draft, submit_proposal, send_message
- Pydantic input schemas with real constraints, declared output schemas, and MCP annotations
- Idempotency key deduplication on every write
- dry_run flag returning preview and cost without mutating state
- Bearer-token validation, per-user rate limiter, and append-only audit log
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from pydantic import BaseModel, Field

from agent.marketplace_port import build_port

ROOT = Path(__file__).resolve().parents[2]
AUDIT_LOG_PATH = ROOT / "data" / "processed" / "mcp_audit.jsonl"

server = Server("gigbid-marketplace")
AUDIT_LOG: list[dict[str, Any]] = []
_RATE_BUCKETS: dict[str, list[float]] = {}
_IDEMPOTENCY_RESULTS: dict[str, dict[str, Any]] = {}


class SearchJobsInput(BaseModel):
    query: str = ""
    limit: int = Field(default=20, ge=1, le=100)
    user_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)


class CreateProposalDraftInput(BaseModel):
    job_id: str = Field(min_length=1)
    cover_letter: str = Field(min_length=20, max_length=5000)
    screening_answers: list[str] = Field(default_factory=list)
    idempotency_key: str = Field(min_length=4)
    dry_run: bool = True
    user_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)


class SubmitProposalInput(BaseModel):
    draft_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=4)
    dry_run: bool = False
    user_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)


class SendMessageInput(BaseModel):
    client_id: str = Field(min_length=1)
    body: str = Field(min_length=1, max_length=4000)
    idempotency_key: str = Field(min_length=4)
    dry_run: bool = False
    user_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)


def verify_bearer_token(token: str | None) -> bool:
    expected = os.environ.get("MCP_MARKETPLACE_TOKEN", "")
    if not expected:
        return True
    return token == expected


def _check_rate_limit(user_id: str, max_per_minute: int = 30) -> None:
    now = time.time()
    bucket = [t for t in _RATE_BUCKETS.get(user_id, []) if now - t < 60.0]
    if len(bucket) >= max_per_minute:
        raise RuntimeError(f"Rate limit exceeded for user {user_id}")
    bucket.append(now)
    _RATE_BUCKETS[user_id] = bucket


def _audit(user: str, tool: str, args: dict[str, Any], result: Any, trace_id: str) -> None:
    entry = {
        "ts": time.time(),
        "user": user,
        "tool": tool,
        "arguments": {k: ("***" if "token" in k.lower() else v) for k, v in args.items()},
        "result_summary": str(result)[:300],
        "trace_id": trace_id,
    }
    AUDIT_LOG.append(entry)
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


TOOL_SPECS = [
    (
        "search_jobs",
        "Search marketplace jobs (read-only).",
        SearchJobsInput.model_json_schema(),
        {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object"}}}},
        types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    ),
    (
        "get_job",
        "Fetch a single job by ID (read-only).",
        {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "minLength": 1},
                "user_id": {"type": "string", "minLength": 1},
                "trace_id": {"type": "string", "minLength": 1},
            },
            "required": ["job_id", "user_id", "trace_id"],
        },
        {"type": "object"},
        types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    ),
    (
        "get_client_history",
        "Fetch client history and quality metrics (read-only).",
        {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "minLength": 1},
                "user_id": {"type": "string", "minLength": 1},
                "trace_id": {"type": "string", "minLength": 1},
            },
            "required": ["client_id", "user_id", "trace_id"],
        },
        {"type": "object"},
        types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    ),
    (
        "get_connects_balance",
        "Get current Connects balance (read-only).",
        {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "minLength": 1},
                "trace_id": {"type": "string", "minLength": 1},
            },
            "required": ["user_id", "trace_id"],
        },
        {"type": "object", "properties": {"balance": {"type": "integer"}}},
        types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    ),
    (
        "list_messages",
        "List recent client messages (read-only).",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 100},
                "user_id": {"type": "string", "minLength": 1},
                "trace_id": {"type": "string", "minLength": 1},
            },
            "required": ["user_id", "trace_id"],
        },
        {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object"}}}},
        types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
    ),
    (
        "create_proposal_draft",
        "Create a proposal draft (write, idempotent, supports dry_run).",
        CreateProposalDraftInput.model_json_schema(),
        {"type": "object", "properties": {"draft_id": {"type": "string"}, "status": {"type": "string"}}},
        types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
    ),
    (
        "submit_proposal",
        "Submit an approved proposal draft and spend Connects (write, idempotent).",
        SubmitProposalInput.model_json_schema(),
        {"type": "object", "properties": {"submitted": {"type": "boolean"}, "connects_spent": {"type": "integer"}}},
        types.ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
    ),
    (
        "send_message",
        "Send a client reply message (write, idempotent).",
        SendMessageInput.model_json_schema(),
        {"type": "object", "properties": {"sent": {"type": "boolean"}, "message_id": {"type": "string"}}},
        types.ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
    ),
]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name=name, description=desc, inputSchema=inp, outputSchema=out, annotations=ann)
        for name, desc, inp, out, ann in TOOL_SPECS
    ]


def invoke_tool_sync(name: str, arguments: dict[str, Any]) -> Any:
    """Synchronous helper usable by both MCP stdio handler and in-process tests."""
    user = arguments.get("user_id", "anon")
    trace_id = arguments.get("trace_id", str(uuid.uuid4()))
    _check_rate_limit(user)
    port = build_port(user_id=user)

    if name in {"create_proposal_draft", "submit_proposal", "send_message"}:
        idem = arguments.get("idempotency_key", "")
        if not arguments.get("dry_run") and idem and f"{name}:{idem}" in _IDEMPOTENCY_RESULTS:
            return _IDEMPOTENCY_RESULTS[f"{name}:{idem}"]

    result: Any = {}
    if name == "search_jobs":
        inp = SearchJobsInput(**arguments)
        result = [j.__dict__ for j in port.search_jobs(query=inp.query, limit=inp.limit)]
    elif name == "get_job":
        r = port.get_job(arguments["job_id"])
        result = r.__dict__ if r else None
    elif name == "get_client_history":
        r = port.get_client_history(arguments["client_id"])
        result = r.__dict__ if r else None
    elif name == "get_connects_balance":
        result = {"balance": port.get_connects_balance()}
    elif name == "list_messages":
        result = port.list_messages(limit=int(arguments.get("limit", 50)))
    elif name == "create_proposal_draft":
        inp = CreateProposalDraftInput(**arguments)
        job = port.get_job(inp.job_id)
        cost = job.connects_cost if job else 6
        if inp.dry_run:
            result = {
                "status": "dry_run",
                "would_send": True,
                "job_id": inp.job_id,
                "connects_cost": cost,
                "cover_letter_preview": inp.cover_letter[:200],
            }
        else:
            result = port.create_proposal_draft(inp.job_id, inp.cover_letter, inp.screening_answers, inp.idempotency_key)
            _IDEMPOTENCY_RESULTS[f"{name}:{inp.idempotency_key}"] = result
    elif name == "submit_proposal":
        inp = SubmitProposalInput(**arguments)
        if inp.dry_run:
            result = {"status": "dry_run", "draft_id": inp.draft_id, "would_spend_connects": True}
        else:
            result = port.submit_proposal(inp.draft_id, inp.idempotency_key)
            _IDEMPOTENCY_RESULTS[f"{name}:{inp.idempotency_key}"] = result
    elif name == "send_message":
        inp = SendMessageInput(**arguments)
        if inp.dry_run:
            result = {"status": "dry_run", "client_id": inp.client_id, "body_preview": inp.body[:120]}
        else:
            result = port.send_message(inp.client_id, inp.body, inp.idempotency_key)
            _IDEMPOTENCY_RESULTS[f"{name}:{inp.idempotency_key}"] = result
    else:
        result = {"error": f"unknown tool: {name}"}

    _audit(user, name, arguments, result, trace_id)
    return result


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> tuple[list[types.TextContent], dict[str, Any]]:
    result = invoke_tool_sync(name, arguments)
    if name in {"search_jobs", "list_messages"}:
        structured = {"items": result if isinstance(result, list) else []}
    elif isinstance(result, dict):
        structured = result
    else:
        structured = {"result": result}
    return [types.TextContent(type="text", text=json.dumps(result, default=str))], structured


def create_http_app():
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    class BearerAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path == "/health":
                return await call_next(request)
            auth = request.headers.get("Authorization", "")
            token = auth.split(" ", 1)[1] if auth.startswith("Bearer ") else None
            if not verify_bearer_token(token):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            return await call_next(request)

    session_mgr = StreamableHTTPSessionManager(app=server, stateless=True)

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "gigbid-marketplace"})

    app = Starlette(
        routes=[Route("/health", health), Mount("/mcp", app=session_mgr.handle_request)],
        lifespan=lambda _app: session_mgr.run(),
    )
    app.add_middleware(BearerAuthMiddleware)
    return app


async def run_stdio() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gigbid-marketplace",
                server_version="0.2.0",
                capabilities=server.get_capabilities(notification_types=None, experimental_capabilities=None),
            ),
        )


def main() -> None:
    if os.environ.get("MCP_TRANSPORT") == "http":
        import uvicorn

        uvicorn.run(create_http_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8091")))
    else:
        import asyncio

        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
