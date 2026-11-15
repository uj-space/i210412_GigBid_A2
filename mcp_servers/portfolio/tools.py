"""Portfolio MCP tools and corpus loader (A1)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mcp.types as types

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE: list[dict[str, Any]] = []
CASES: dict[str, dict[str, Any]] = {}
SKILLS: set[str] = set()


def load_data(data_dir: str | None = None) -> None:
    global EVIDENCE, CASES, SKILLS
    EVIDENCE, CASES, SKILLS = [], {}, set()
    base = Path(data_dir) if data_dir else ROOT / "data"
    personas_dir = base / "personas"
    if personas_dir.exists():
        for pf in sorted(personas_dir.glob("*.json")):
            EVIDENCE.extend(json.loads(pf.read_text(encoding="utf-8")).get("items", []))
    sample_file = base / "sample" / "portfolio_items.json"
    if sample_file.exists():
        EVIDENCE.extend(json.loads(sample_file.read_text(encoding="utf-8")))
    direct_file = base / "portfolio_items.json"
    if direct_file.exists():
        EVIDENCE.extend(json.loads(direct_file.read_text(encoding="utf-8")))

    for e in EVIDENCE:
        eid = e.get("evidence_id") or e.get("id") or ""
        if eid:
            CASES[eid] = e
        for s in e.get("skills", []) or []:
            SKILLS.add(s)


load_data()


def get_tool_definitions() -> list[types.Tool]:
    ann = types.ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
    return [
        types.Tool(
            name="search_evidence",
            description="Search portfolio evidence items with optional metadata filters (persona, type, outcome, client_industry).",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirement": {"type": "string", "minLength": 1},
                    "k": {"type": "integer", "default": 5, "minimum": 1, "maximum": 25},
                    "filters": {"type": "object", "default": {}},
                },
                "required": ["requirement"],
            },
            outputSchema={
                "type": "object",
                "properties": {"items": {"type": "array", "items": {"type": "object"}}},
            },
            annotations=ann,
        ),
        types.Tool(
            name="get_case_study",
            description="Get a full portfolio case study or past proposal by evidence_id.",
            inputSchema={
                "type": "object",
                "properties": {"id": {"type": "string", "minLength": 1}},
                "required": ["id"],
            },
            outputSchema={"type": "object"},
            annotations=ann,
        ),
        types.Tool(
            name="list_skills",
            description="List all verified skills across the portfolio corpus.",
            inputSchema={"type": "object", "properties": {}},
            outputSchema={"type": "object", "properties": {"skills": {"type": "array", "items": {"type": "string"}}}},
            annotations=ann,
        ),
    ]


def invoke_portfolio_tool(name: str, arguments: dict[str, Any]) -> Any:
    if not EVIDENCE:
        load_data()
    if name == "search_evidence":
        req = arguments.get("requirement", "")
        k = int(arguments.get("k", 5))
        filters = arguments.get("filters") or {}
        persona = filters.get("persona", "default")
        try:
            from rag.retriever import retrieve_evidence

            results = retrieve_evidence(req, k=k * 2, persona=persona)
        except Exception:
            req_l = req.lower()
            results = [
                e for e in EVIDENCE
                if any(w in (e.get("title", "") + " " + e.get("summary", "") + " " + " ".join(e.get("skills", []) or [])).lower()
                       for w in req_l.split() if len(w) > 2)
            ]
        for key in ("type", "outcome", "client_industry"):
            if filters.get(key):
                results = [r for r in results if r.get(key) == filters[key]]
        return results[:k]
    if name == "get_case_study":
        return CASES.get(arguments.get("id", ""), {})
    if name == "list_skills":
        return sorted(SKILLS)
    return {"error": f"unknown tool: {name}"}
