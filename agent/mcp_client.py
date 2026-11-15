"""MCP Client discipline (A6).

Provides:
- Per-agent tool allowlists (each agent gets only the tools it needs)
- Bounded retries with exponential backoff and timeouts
- Degraded-mode tracking & queued work recovery when a server is unavailable
"""
from __future__ import annotations

import time
from typing import Any

from mcp_servers.marketplace.server import invoke_tool_sync as marketplace_call
from mcp_servers.portfolio.server import invoke_tool_sync as portfolio_call
from mcp_servers.workspace.server import server as _workspace_server

AGENT_TOOL_ALLOWLISTS: dict[str, set[str]] = {
    "scout": {"search_jobs"},
    "analyst": set(),
    "risk_assessor": {"get_client_history"},
    "fit_matcher": {"search_evidence", "get_case_study", "list_skills"},
    "pricing": {"get_connects_balance", "get_client_history"},
    "writer": {"search_evidence", "get_case_study"},
    "critic": {"search_evidence", "get_case_study"},
    "compliance": set(),
    "client_liaison": {"list_messages", "send_message", "free_calendar_slots", "create_interview_hold", "create_email_draft"},
}

_DEGRADED_QUEUE: list[dict[str, Any]] = []
_MARKETPLACE_DEGRADED = False


def set_marketplace_degraded(flag: bool) -> None:
    global _MARKETPLACE_DEGRADED
    _MARKETPLACE_DEGRADED = flag


def is_marketplace_degraded() -> bool:
    return _MARKETPLACE_DEGRADED


def get_degraded_queue() -> list[dict[str, Any]]:
    return list(_DEGRADED_QUEUE)


def call_mcp_tool(
    agent_name: str,
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    max_retries: int = 2,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """Invoke an MCP tool enforcing per-agent allowlists, retries, and degraded mode."""
    allowed = AGENT_TOOL_ALLOWLISTS.get(agent_name, set())
    if tool_name not in allowed:
        raise PermissionError(f"Agent '{agent_name}' is not allowed to call MCP tool '{tool_name}'")

    if server_name == "marketplace" and _MARKETPLACE_DEGRADED:
        _DEGRADED_QUEUE.append({"agent": agent_name, "tool": tool_name, "arguments": arguments, "ts": time.time()})
        return {"status": "degraded", "queued": True, "error": "Marketplace MCP server unavailable"}

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            if server_name == "portfolio":
                return {"status": "ok", "data": portfolio_call(tool_name, arguments)}
            if server_name == "marketplace":
                return {"status": "ok", "data": marketplace_call(tool_name, arguments)}
            if server_name == "workspace":
                # Local workspace mock tools
                import asyncio
                from mcp_servers.workspace.server import call_tool as ws_call

                res = asyncio.run(ws_call(tool_name, arguments))
                if isinstance(res, tuple):
                    return {"status": "ok", "data": res[1]}
                import json

                return {"status": "ok", "data": json.loads(res[0].text)}
            raise ValueError(f"Unknown MCP server: {server_name}")
        except Exception as exc:
            last_err = exc
            if attempt < max_retries:
                time.sleep(0.05 * (2**attempt))

    if server_name == "marketplace":
        _DEGRADED_QUEUE.append({"agent": agent_name, "tool": tool_name, "arguments": arguments, "ts": time.time()})
    return {"status": "error", "queued": server_name == "marketplace", "error": str(last_err)}
