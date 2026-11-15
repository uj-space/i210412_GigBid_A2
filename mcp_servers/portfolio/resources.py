"""Portfolio MCP resource templates (A1)."""
from __future__ import annotations

import json
import mcp.types as types
from mcp_servers.portfolio.tools import CASES, load_data


def get_resource_templates() -> list[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(uriTemplate="portfolio://case/{id}", name="case_study", description="Full case study by id"),
        types.ResourceTemplate(uriTemplate="portfolio://proposal/{id}", name="past_proposal", description="Past proposal by id"),
    ]


def read_portfolio_resource(uri: str) -> str:
    if not CASES:
        load_data()
    uri_str = str(uri)
    if uri_str.startswith("portfolio://case/"):
        return json.dumps(CASES.get(uri_str.split("/case/")[-1], {}))
    if uri_str.startswith("portfolio://proposal/"):
        return json.dumps(CASES.get(uri_str.split("/proposal/")[-1], {}))
    return json.dumps({"error": "unknown resource"})
