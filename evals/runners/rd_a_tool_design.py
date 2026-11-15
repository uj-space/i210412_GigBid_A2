"""R&D Question A: MCP Tool Design Experiment.

Compares:
1. Monolithic / unconstrained tool design (single god-tool, no per-agent allowlist, no idempotency key, no dry-run)
2. Modular typed MCP design (Portfolio + Marketplace + Workspace separation, AGENT_TOOL_ALLOWLISTS,
   Pydantic schemas, idempotency_key dedup, and dry_run previews).

Usage:
    python -m evals.runners.rd_a_tool_design
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.mcp_client import AGENT_TOOL_ALLOWLISTS
from mcp_servers.marketplace.server import invoke_tool_sync


def _is_allowed(role: str, _server: str, tool: str) -> bool:
    return tool in (AGENT_TOOL_ALLOWLISTS.get(role) or set())


def run_rd_a_experiment() -> dict[str, Any]:
    # 1. Blast-radius / least-privilege check across 9 agent roles
    roles = list(AGENT_TOOL_ALLOWLISTS.keys())
    write_tools = ["create_proposal_draft", "submit_proposal", "send_message", "create_interview_hold"]

    mono_exposed = len(roles) * len(write_tools)
    modular_exposed = sum(
        1 for r in roles for t in write_tools if _is_allowed(r, "marketplace", t) or _is_allowed(r, "workspace", t)
    )

    # 2. Idempotency deduplication check on submit_proposal
    d1 = invoke_tool_sync(
        "create_proposal_draft",
        {
            "job_id": "sample-001",
            "cover_letter": "Grounded proposal referencing portfolio evidence.",
            "idempotency_key": "rda-draft-1",
            "dry_run": False,
            "user_id": "rda-user",
            "trace_id": "rda-trace",
        },
    )
    did = d1.get("draft_id", "")
    s1 = invoke_tool_sync(
        "submit_proposal",
        {"draft_id": did, "idempotency_key": "rda-sub-1", "dry_run": False, "user_id": "rda-user", "trace_id": "rda-trace"},
    )
    s2 = invoke_tool_sync(
        "submit_proposal",
        {"draft_id": did, "idempotency_key": "rda-sub-1", "dry_run": False, "user_id": "rda-user", "trace_id": "rda-trace"},
    )
    dedup_ok = (s1.get("submission_id") == s2.get("submission_id")) and bool(s1.get("submission_id"))

    # 3. Dry-run safety check (dry_run=True does not mutate/spend)
    dry_res = invoke_tool_sync(
        "submit_proposal",
        {"draft_id": did, "idempotency_key": "rda-sub-dry", "dry_run": True, "user_id": "rda-user", "trace_id": "rda-trace"},
    )
    dry_safe = dry_res.get("status") == "dry_run"

    return {
        "monolithic_unconstrained": {
            "write_tool_exposures_across_roles": mono_exposed,
            "duplicate_submit_prevented": False,
            "dry_run_preview_supported": False,
            "least_privilege_score": 0.0,
        },
        "modular_typed_mcp": {
            "write_tool_exposures_across_roles": modular_exposed,
            "blast_radius_reduction_pct": round((1.0 - modular_exposed / max(mono_exposed, 1)) * 100.0, 2),
            "duplicate_submit_prevented": dedup_ok,
            "dry_run_preview_supported": dry_safe,
            "least_privilege_score": round(1.0 - modular_exposed / max(mono_exposed, 1), 4),
        },
    }


def main() -> None:
    res = run_rd_a_experiment()
    print("\nR&D Question A: MCP Tool Design Results")
    print("=" * 60)
    print(json.dumps(res, indent=2))
    out = ROOT / "evals" / "results" / "rd_a_tool_design.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
