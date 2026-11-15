from __future__ import annotations

from typing import Any
import json
import uuid

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from agent.marketplace_port import build_port

server = Server("gigbid-marketplace")
AUDIT_LOG = []


def _audit(user, tool, args, result, trace_id):
    AUDIT_LOG.append({"user": user, "tool": tool, "arguments": args,
                      "result": result, "trace_id": trace_id})


@server.list_tools()
async def list_tools():
    tools = [
        ("search_jobs", "Search jobs (read).", {"query": "", "limit": 20},
         ["user_id", "trace_id"], {"readOnlyHint": True}),
        ("get_job", "Get a job (read).", {"job_id": "", "user_id": "", "trace_id": ""},
         ["job_id", "user_id", "trace_id"], {"readOnlyHint": True}),
        ("get_client_history", "Client history (read).", {"client_id": "", "user_id": "", "trace_id": ""},
         ["client_id", "user_id", "trace_id"], {"readOnlyHint": True}),
        ("get_connects_balance", "Connects balance (read).", {"user_id": "", "trace_id": ""},
         ["user_id", "trace_id"], {"readOnlyHint": True}),
        ("create_proposal_draft", "Create proposal draft (write, idempotent).",
         {"job_id": "", "cover_letter": "", "screening_answers": [], "idempotency_key": "",
          "dry_run": True, "user_id": "", "trace_id": ""},
         ["job_id", "cover_letter", "idempotency_key", "user_id", "trace_id"],
         {"destructiveHint": False, "idempotentHint": True}),
        ("submit_proposal", "Submit proposal (write, idempotent).",
         {"draft_id": "", "idempotency_key": "", "user_id": "", "trace_id": ""},
         ["draft_id", "idempotency_key", "user_id", "trace_id"],
         {"destructiveHint": True, "idempotentHint": True}),
        ("send_message", "Send message (write, idempotent).",
         {"client_id": "", "body": "", "idempotency_key": "", "user_id": "", "trace_id": ""},
         ["client_id", "body", "idempotency_key", "user_id", "trace_id"],
         {"destructiveHint": True, "idempotentHint": True}),
    ]
    out = []
    for name, desc, props, req, ann in tools:
        schema = {"type": "object", "properties": {k: ({"type": "string"} if not isinstance(v, list)
                          else {"type": "array", "items": {"type": "string"}})
                          for k, v in props.items()}, "required": req}
        for k, v in props.items():
            if isinstance(v, bool):
                schema["properties"][k] = {"type": "boolean", "default": v}
            elif isinstance(v, int):
                schema["properties"][k] = {"type": "integer", "default": v}
        out.append(types.Tool(name=name, description=desc, inputSchema=schema,
                              annotations=ann))
    return out


@server.call_tool()
async def call_tool(name, arguments):
    user = arguments.get("user_id", "anon")
    trace_id = arguments.get("trace_id", str(uuid.uuid4()))
    port = build_port()
    result = {}
    if name == "search_jobs":
        result = [j.__dict__ for j in port.search_jobs(query=arguments.get("query", ""),
                                                       limit=int(arguments.get("limit", 20)))]
    elif name == "get_job":
        r = port.get_job(arguments["job_id"]); result = r.__dict__ if r else None
    elif name == "get_client_history":
        r = port.get_client_history(arguments["client_id"]); result = r.__dict__ if r else None
    elif name == "get_connects_balance":
        result = {"balance": port.get_connects_balance()}
    elif name == "create_proposal_draft":
        if arguments.get("dry_run"):
            result = {"status": "dry_run", "would_send": True,
                      "cover_letter_preview": arguments.get("cover_letter", "")[:120]}
        else:
            result = port.create_proposal_draft(arguments["job_id"], arguments["cover_letter"],
                                                arguments.get("screening_answers", []),
                                                arguments["idempotency_key"])
    elif name == "submit_proposal":
        result = port.submit_proposal(arguments["draft_id"], arguments["idempotency_key"])
    elif name == "send_message":
        result = port.send_message(arguments["client_id"], arguments["body"],
                                   arguments["idempotency_key"])
    else:
        result = {"error": "unknown tool"}
    _audit(user, name, arguments, result, trace_id)
    return [types.TextContent(type="text", text=json.dumps(result, default=str))]


async def run_stdio():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         InitializationOptions(server_name="gigbid-marketplace", server_version="0.1.0",
                                               capabilities=server.get_capabilities(
                                                   notification_types=None,
                                                   experimental_capabilities=None)))


def main():
    import asyncio
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
