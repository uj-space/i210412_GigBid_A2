"""In-memory MCP client tests for Workspace MCP server (A7)."""
from __future__ import annotations

import json
import pytest
from mcp.shared.memory import create_connected_server_and_client_session


@pytest.mark.asyncio
async def test_workspace_mcp_in_memory_session():
    from mcp_servers.workspace.server import server

    async with create_connected_server_and_client_session(server) as session:
        tools = (await session.list_tools()).tools
        assert {t.name for t in tools} == {"free_calendar_slots", "create_interview_hold", "create_email_draft"}

        slots = await session.call_tool("free_calendar_slots", {"user_id": "u-test"})
        data = json.loads(slots.content[0].text)
        assert len(data["slots"]) >= 2

        h1 = await session.call_tool("create_interview_hold", {"slot": data["slots"][0], "client_id": "c1", "user_id": "u-test"})
        h2 = await session.call_tool("create_interview_hold", {"slot": data["slots"][0], "client_id": "c1", "user_id": "u-test"})
        assert json.loads(h1.content[0].text)["hold_id"] == json.loads(h2.content[0].text)["hold_id"]
