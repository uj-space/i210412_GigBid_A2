"""In-memory MCP client tests for Portfolio MCP server (A7)."""
from __future__ import annotations

import json
import pytest
from mcp.shared.memory import create_connected_server_and_client_session


@pytest.mark.asyncio
async def test_portfolio_mcp_in_memory_session():
    from mcp_servers.portfolio.server import server

    async with create_connected_server_and_client_session(server) as session:
        tools = (await session.list_tools()).tools
        names = {t.name for t in tools}
        assert {"search_evidence", "get_case_study", "list_skills"} <= names

        res = await session.call_tool(
            "search_evidence",
            {"requirement": "Python churn prediction", "k": 3, "filters": {"persona": "ai_ml_engineer"}},
        )
        items = json.loads(res.content[0].text)
        assert len(items) == 3

        cs = await session.call_tool("get_case_study", {"id": "ai_ml_engineer-cs-01"})
        assert json.loads(cs.content[0].text)["evidence_id"] == "ai_ml_engineer-cs-01"

        templates = (await session.list_resource_templates()).resourceTemplates
        assert {t.uriTemplate for t in templates} >= {"portfolio://case/{id}", "portfolio://proposal/{id}"}

        prompts = (await session.list_prompts()).prompts
        assert any(p.name == "answer_screening_question" for p in prompts)
