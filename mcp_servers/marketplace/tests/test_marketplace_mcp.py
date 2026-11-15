"""In-memory MCP client tests for Marketplace MCP server (A7)."""
from __future__ import annotations

import json
import pytest
from mcp.shared.memory import create_connected_server_and_client_session


@pytest.mark.asyncio
async def test_marketplace_mcp_in_memory_session():
    from mcp_servers.marketplace.server import server

    async with create_connected_server_and_client_session(server) as session:
        tools = (await session.list_tools()).tools
        names = {t.name for t in tools}
        assert {
            "search_jobs",
            "get_job",
            "get_client_history",
            "get_connects_balance",
            "list_messages",
            "create_proposal_draft",
            "submit_proposal",
            "send_message",
        } <= names

        bal = await session.call_tool("get_connects_balance", {"user_id": "u-test", "trace_id": "tr-test"})
        assert "balance" in json.loads(bal.content[0].text)

        msgs = await session.call_tool("list_messages", {"limit": 5, "user_id": "u-test", "trace_id": "tr-test"})
        assert isinstance(json.loads(msgs.content[0].text), list)
