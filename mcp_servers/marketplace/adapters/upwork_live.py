"""Live Upwork MCP adapter (R1 / A4).

Connects to the official Upwork MCP server (https://mcp.upwork.com/mcp) via
langchain-mcp-adapters MultiServerMCPClient over Streamable HTTP with OAuth 2.1
per-user encrypted tokens. All write operations create drafts only and never
auto-submit without explicit user confirmation on Upwork.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from agent.marketplace_port import ClientHistory, Job, MarketplacePort


class UpworkLiveAdapter(MarketplacePort):
    """Live Upwork MCP adapter behind the same MarketplacePort interface."""

    MCP_URL = "https://mcp.upwork.com/mcp"

    def __init__(self, user_id: str = "default", oauth_token: Optional[str] = None, requests_per_minute: int = 6):
        # Conservative live-mode schedule/rate limit (R9 / E1: never look like scraping)
        super().__init__(mode="upwork_live", base_url=self.MCP_URL, api_token=oauth_token, requests_per_minute=requests_per_minute)
        self.user_id = user_id

    def _get_mcp_client(self):
        from langchain_mcp_adapters.client import MultiServerMCPClient

        token = self.api_token or os.environ.get("UPWORK_OAUTH_TOKEN", "")
        if not token:
            raise PermissionError("Upwork OAuth 2.1 token not configured for this user.")
        return MultiServerMCPClient(
            {
                "upwork": {
                    "url": self.MCP_URL,
                    "transport": "streamable_http",
                    "headers": {"Authorization": f"Bearer {token}"},
                }
            }
        )

    def _call_upwork_tool(self, tool_name: str, args: dict[str, Any]) -> Any:
        self._throttle()
        client = self._get_mcp_client()

        async def _run():
            tools = await client.get_tools()
            for t in tools:
                if t.name == tool_name:
                    return await t.ainvoke(args)
            raise RuntimeError(f"Upwork MCP tool '{tool_name}' not found")

        return asyncio.run(_run())

    def search_jobs(self, query: str = "", limit: int = 20) -> list[Job]:
        raw = self._call_upwork_tool("search_jobs", {"query": query, "limit": min(limit, 20)})
        items = raw if isinstance(raw, list) else (raw.get("jobs", []) if isinstance(raw, dict) else [])
        return [self._to_job(j) for j in items]

    def get_job(self, job_id: str) -> Optional[Job]:
        raw = self._call_upwork_tool("get_job", {"job_id": job_id})
        return self._to_job(raw) if isinstance(raw, dict) else None

    def get_client_history(self, client_id: str) -> Optional[ClientHistory]:
        raw = self._call_upwork_tool("get_client_history", {"client_id": client_id})
        if not isinstance(raw, dict):
            return None
        return ClientHistory(
            client_id=client_id,
            completed_projects=int(raw.get("completed_projects", 0)),
            average_rating=float(raw.get("average_rating", 0.0)),
            payment_verified=bool(raw.get("payment_verified", False)),
            total_spent=raw.get("total_spent"),
            notes=raw.get("notes", ""),
            raw=raw,
        )

    def get_connects_balance(self) -> int:
        raw = self._call_upwork_tool("get_connects_balance", {})
        return int(raw.get("balance", 0)) if isinstance(raw, dict) else 0

    def list_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        raw = self._call_upwork_tool("list_messages", {"limit": limit})
        return raw if isinstance(raw, list) else (raw.get("messages", []) if isinstance(raw, dict) else [])

    def create_proposal_draft(
        self, job_id: str, cover_letter: str, screening_answers: list[str], idempotency_key: str
    ) -> dict[str, Any]:
        # Live mode: creates a draft on Upwork; user confirms separately on Upwork.
        return self._call_upwork_tool(
            "create_proposal_draft",
            {
                "job_id": job_id,
                "cover_letter": cover_letter,
                "screening_answers": screening_answers,
                "idempotency_key": idempotency_key,
            },
        )

    def submit_proposal(self, draft_id: str, idempotency_key: str) -> dict[str, Any]:
        # Platform safety rule: live mode only creates drafts; final submit happens on Upwork UI.
        return {
            "status": "draft_ready_for_upwork_confirmation",
            "draft_id": draft_id,
            "submitted": False,
            "message": "Live mode creates drafts only. Confirm submission directly on Upwork.",
        }

    def send_message(self, client_id: str, body: str, idempotency_key: str) -> dict[str, Any]:
        return self._call_upwork_tool(
            "create_message_draft",
            {"client_id": client_id, "body": body, "idempotency_key": idempotency_key},
        )
