"""Portfolio MCP server entrypoint (stdio + Streamable HTTP, A1)."""
from __future__ import annotations

import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from mcp_servers.portfolio.prompts import get_prompt_definitions, render_prompt
from mcp_servers.portfolio.resources import get_resource_templates, read_portfolio_resource
from mcp_servers.portfolio.tools import CASES, EVIDENCE, SKILLS, get_tool_definitions, invoke_portfolio_tool, load_data

server = Server("gigbid-portfolio")


def invoke_tool_sync(name: str, arguments: dict[str, Any]) -> Any:
    return invoke_portfolio_tool(name, arguments)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return get_tool_definitions()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> tuple[list[types.TextContent], dict[str, Any]]:
    res = invoke_portfolio_tool(name, arguments or {})
    if name == "search_evidence":
        structured = {"items": res}
    elif name == "list_skills":
        structured = {"skills": res}
    else:
        structured = res if isinstance(res, dict) else {"result": res}
    return [types.TextContent(type="text", text=json.dumps(res, default=str))], structured


@server.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return get_resource_templates()


@server.read_resource()
async def read_resource(uri: str) -> str:
    return read_portfolio_resource(uri)


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return get_prompt_definitions()


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> types.GetPromptResult:
    return render_prompt(name, arguments)


def create_http_app():
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    session_mgr = StreamableHTTPSessionManager(app=server, stateless=True)

    async def health(_request):
        return JSONResponse({"status": "ok", "server": "gigbid-portfolio"})

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
                server_name="gigbid-portfolio",
                server_version="0.2.0",
                capabilities=server.get_capabilities(notification_types=None, experimental_capabilities=None),
            ),
        )


def main() -> None:
    if os.environ.get("MCP_TRANSPORT") == "http":
        import uvicorn

        uvicorn.run(create_http_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8090")))
    else:
        import asyncio

        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
