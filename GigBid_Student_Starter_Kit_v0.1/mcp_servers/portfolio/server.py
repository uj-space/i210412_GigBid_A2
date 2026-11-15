"""Portfolio MCP server (read-only)."""
from __future__ import annotations

from typing import Any
import json
from pathlib import Path

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("gigbid-portfolio")
EVIDENCE: list[dict[str, Any]] = []
CASES: dict[str, dict[str, Any]] = {}
SKILLS: set[str] = set()


def load_data(data_dir: str = "data") -> None:
    global EVIDENCE, CASES, SKILLS
    p = Path(data_dir) / "portfolio_items.json"
    if p.exists():
        EVIDENCE = json.loads(p.read_text(encoding="utf-8"))
    for e in EVIDENCE:
        CASES[e.get("evidence_id", e.get("id", ""))] = e
        for s in e.get("skills", []) or []:
            SKILLS.add(s)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name="search_evidence", description="Search portfolio evidence.",
                   inputSchema={"type": "object", "properties": {
                       "requirement": {"type": "string"}, "k": {"type": "integer", "default": 5},
                       "filters": {"type": "object", "default": {}}}, "required": ["requirement"]}),
        types.Tool(name="get_case_study", description="Get a case study by id.",
                   inputSchema={"type": "object", "properties": {"id": {"type": "string"}},
                                 "required": ["id"]}),
        types.Tool(name="list_skills", description="List all portfolio skills.",
                   inputSchema={"type": "object", "properties": {}}),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name == "search_evidence":
        req = (arguments.get("requirement") or "").lower()
        k = int(arguments.get("k", 5))
        results = []
        for e in EVIDENCE:
            text = (e.get("title", "") + " " + e.get("summary", "") + " "
                    + " ".join(e.get("skills", []) or [])).lower()
            if req in text or not req:
                results.append(e)
        return [types.TextContent(type="text", text=json.dumps(results[:k]))]
    if name == "get_case_study":
        return [types.TextContent(type="text", text=json.dumps(CASES.get(arguments.get("id", ""), {})))]
    if name == "list_skills":
        return [types.TextContent(type="text", text=json.dumps(sorted(SKILLS)))]
    return [types.TextContent(type="text", text=json.dumps({"error": "unknown tool"}))]


@server.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(uriTemplate="portfolio://case/{id}", name="case study",
                               description="Full case study by id"),
        types.ResourceTemplate(uriTemplate="portfolio://proposal/{id}", name="proposal",
                               description="Past proposal by id"),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri.startswith("portfolio://case/"):
        return json.dumps(CASES.get(uri.split("/case/")[-1], {}))
    if uri.startswith("portfolio://proposal/"):
        return json.dumps(CASES.get(uri.split("/proposal/")[-1], {}))
    return json.dumps({"error": "unknown resource"})


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [types.Prompt(name="answer_screening_question",
                         description="Answer a screening question from portfolio evidence.",
                         arguments=[types.PromptArgument(name="question", required=True),
                                    types.PromptArgument(name="evidence", required=False)])]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str]) -> types.GetPromptResult:
    question = arguments.get("question", "")
    return types.GetPromptResult(
        description="Screening-question answerer",
        messages=[types.PromptMessage(role="user",
                                      content=types.TextContent(
                                          type="text",
                                          text=f"Answer using only portfolio evidence: {question}"))])


async def run_stdio() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream,
                         InitializationOptions(server_name="gigbid-portfolio", server_version="0.1.0",
                                               capabilities=server.get_capabilities(
                                                   notification_types=None,
                                                   experimental_capabilities=None)))


def main() -> None:
    import asyncio
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
