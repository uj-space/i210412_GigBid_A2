from __future__ import annotations

from typing import Any
import json
import uuid
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("gigbid-workspace")


def _slots():
    now = datetime.now()
    return [(now + timedelta(days=1, hours=h)).strftime("%Y-%m-%d %H:%M")
            for h in range(9, 17, 2)]


@server.list_tools()
async def list_tools():
    return [
        types.Tool(name="free_calendar_slots", description="Free calendar slots.",
                   inputSchema={"type": "object", "properties": {
                       "date": {"type": "string"}, "user_id": {"type": "string"}},
                       "required": ["user_id"]}),
        types.Tool(name="create_interview_hold", description="Tentative interview hold.",
                   inputSchema={"type": "object", "properties": {
                       "slot": {"type": "string"}, "client_id": {"type": "string"},
                       "user_id": {"type": "string"}},
                       "required": ["slot", "client_id", "user_id"]},
                   annotations={"destructiveHint": False, "idempotentHint": True}),
        types.Tool(name="create_email_draft", description="Email draft.",
                   inputSchema={"type": "object", "properties": {
                       "to": {"type": "string"}, "subject": {"type": "string"},
                       "body": {"type": "string"}, "user_id": {"type": "string"}},
                       "required": ["to", "subject", "body", "user_id"]}),
    ]


@server.call_tool()
async def call_tool(name, arguments):
    if name == "free_calendar_slots":
        result = {"slots": _slots(), "date": arguments.get("date")}
    elif name == "create_interview_hold":
        result = {"hold_id": f"hold-{uuid.uuid4().hex[:8]}", "slot": arguments.get("slot"),
                  "status": "tentative", "client_id": arguments.get("client_id")}
    elif name == "create_email_draft":
        result = {"draft_id": f"draft-{uuid.uuid4().hex[:8]}", "to": arguments.get("to"),
                  "subject": arguments.get("subject"), "status": "draft"}
    else:
        result = {"error": "unknown tool"}
    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


async def run_stdio():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         InitializationOptions(server_name="gigbid-workspace", server_version="0.1.0",
                                               capabilities=server.get_capabilities(
                                                   notification_types=None,
                                                   experimental_capabilities=None)))


def main():
    import asyncio
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
