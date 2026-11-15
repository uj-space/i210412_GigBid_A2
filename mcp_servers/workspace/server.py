"""Workspace MCP server: calendar slots, tentative interview holds, and email drafts (A3)."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("gigbid-workspace")
HOLDS: dict[str, dict[str, Any]] = {}
EMAIL_DRAFTS: dict[str, dict[str, Any]] = {}


def _slots() -> list[str]:
    now = datetime.now()
    return [(now + timedelta(days=1, hours=h)).strftime("%Y-%m-%d %H:%M") for h in range(9, 17, 2)]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="free_calendar_slots",
            description="Return available calendar interview slots (read-only).",
            inputSchema={
                "type": "object",
                "properties": {"date": {"type": "string"}, "user_id": {"type": "string", "minLength": 1}},
                "required": ["user_id"],
            },
            outputSchema={
                "type": "object",
                "properties": {"slots": {"type": "array", "items": {"type": "string"}}, "date": {"type": "string"}},
            },
            annotations=types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        ),
        types.Tool(
            name="create_interview_hold",
            description="Create a tentative interview calendar hold (write, idempotent).",
            inputSchema={
                "type": "object",
                "properties": {
                    "slot": {"type": "string", "minLength": 4},
                    "client_id": {"type": "string", "minLength": 1},
                    "user_id": {"type": "string", "minLength": 1},
                },
                "required": ["slot", "client_id", "user_id"],
            },
            outputSchema={"type": "object", "properties": {"hold_id": {"type": "string"}, "status": {"type": "string"}}},
            annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True),
        ),
        types.Tool(
            name="create_email_draft",
            description="Create an email draft for user review (write, non-destructive).",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "minLength": 3},
                    "subject": {"type": "string", "minLength": 1},
                    "body": {"type": "string", "minLength": 1},
                    "user_id": {"type": "string", "minLength": 1},
                },
                "required": ["to", "subject", "body", "user_id"],
            },
            outputSchema={"type": "object", "properties": {"draft_id": {"type": "string"}, "status": {"type": "string"}}},
            annotations=types.ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> tuple[list[types.TextContent], dict[str, Any]]:
    args = arguments or {}
    if name == "free_calendar_slots":
        result = {"slots": _slots(), "date": args.get("date", "")}
    elif name == "create_interview_hold":
        key = f"{args.get('user_id')}:{args.get('client_id')}:{args.get('slot')}"
        if key not in HOLDS:
            HOLDS[key] = {
                "hold_id": f"hold-{uuid.uuid4().hex[:8]}",
                "slot": args.get("slot"),
                "client_id": args.get("client_id"),
                "status": "tentative",
            }
        result = HOLDS[key]
    elif name == "create_email_draft":
        did = f"email-{uuid.uuid4().hex[:8]}"
        EMAIL_DRAFTS[did] = {
            "draft_id": did,
            "to": args.get("to"),
            "subject": args.get("subject"),
            "status": "draft",
        }
        result = EMAIL_DRAFTS[did]
    else:
        result = {"error": f"unknown tool: {name}"}
    return [types.TextContent(type="text", text=json.dumps(result, default=str))], result


def create_http_app():
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    session_mgr = StreamableHTTPSessionManager(app=server, stateless=True)

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "gigbid-workspace"})

    return Starlette(
        routes=[Route("/health", health), Mount("/mcp", app=session_mgr.handle_request)],
        lifespan=lambda _app: session_mgr.run(),
    )


async def run_stdio() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gigbid-workspace",
                server_version="0.2.0",
                capabilities=server.get_capabilities(notification_types=None, experimental_capabilities=None),
            ),
        )


def main() -> None:
    if os.environ.get("MCP_TRANSPORT") == "http":
        import uvicorn

        uvicorn.run(create_http_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8092")))
    else:
        import asyncio

        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
