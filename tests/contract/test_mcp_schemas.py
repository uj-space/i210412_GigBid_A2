"""Contract tests: MCP tool schemas, annotations, idempotency, dry-run, and allowlists."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).parent / "mcp_schema_snapshot.json"


def _collect_schemas() -> dict[str, dict]:
    from mcp_servers.marketplace.server import list_tools as m_tools
    from mcp_servers.portfolio.server import list_tools as p_tools
    from mcp_servers.workspace.server import list_tools as w_tools

    async def _gather():
        out = {}
        for srv, fn in [("portfolio", p_tools), ("marketplace", m_tools), ("workspace", w_tools)]:
            tools = await fn()
            out[srv] = {
                t.name: {
                    "required": t.inputSchema.get("required", []),
                    "properties": sorted(t.inputSchema.get("properties", {}).keys()),
                    "annotations": t.annotations.model_dump() if t.annotations else {},
                }
                for t in tools
            }
        return out

    return asyncio.run(_gather())


def test_mcp_schema_snapshot():
    current = _collect_schemas()
    if not SNAPSHOT_PATH.exists():
        SNAPSHOT_PATH.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert current == expected, "MCP tool schemas drifted from snapshot!"


def test_marketplace_write_annotations_and_idempotency():
    from mcp_servers.marketplace.server import invoke_tool_sync

    dry = invoke_tool_sync(
        "create_proposal_draft",
        {
            "job_id": "dev-ai_ml_engineer-001",
            "cover_letter": "Delivered production churn pipeline [ai_ml_engineer-cs-01] with Python and scikit-learn.",
            "screening_answers": ["Two milestones."],
            "idempotency_key": "idem-test-001",
            "dry_run": True,
            "user_id": "u1",
            "trace_id": "tr-1",
        },
    )
    assert dry["status"] == "dry_run"
    assert dry["would_send"] is True

    d1 = invoke_tool_sync(
        "create_proposal_draft",
        {
            "job_id": "dev-ai_ml_engineer-001",
            "cover_letter": "Delivered production churn pipeline [ai_ml_engineer-cs-01] with Python and scikit-learn.",
            "screening_answers": ["Two milestones."],
            "idempotency_key": "idem-test-002",
            "dry_run": False,
            "user_id": "u1",
            "trace_id": "tr-2",
        },
    )
    d2 = invoke_tool_sync(
        "create_proposal_draft",
        {
            "job_id": "dev-ai_ml_engineer-001",
            "cover_letter": "Delivered production churn pipeline [ai_ml_engineer-cs-01] with Python and scikit-learn.",
            "screening_answers": ["Two milestones."],
            "idempotency_key": "idem-test-002",
            "dry_run": False,
            "user_id": "u1",
            "trace_id": "tr-3",
        },
    )
    assert d1["draft_id"] == d2["draft_id"]


def test_agent_allowlist_enforced():
    import pytest
    from agent.mcp_client import call_mcp_tool

    with pytest.raises(PermissionError):
        call_mcp_tool("analyst", "marketplace", "submit_proposal", {"draft_id": "x"})
