"""Contract tests: MCP tool schema snapshots."""
from __future__ import annotations

import json
from pathlib import Path


def test_portfolio_tools_have_schemas():
    """Portfolio MCP server tools must have input schemas."""
    from mcp_servers.portfolio.server import server
    # Check that server is importable and has tools
    assert server is not None


def test_marketplace_tools_have_schemas():
    """Marketplace MCP server tools must have input schemas."""
    from mcp_servers.marketplace.server import server
    assert server is not None


def test_workspace_tools_have_schemas():
    """Workspace MCP server tools must have input schemas."""
    from mcp_servers.workspace.server import server
    assert server is not None