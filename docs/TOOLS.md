# MCP Tool Inventory (`docs/TOOLS.md`)

All capabilities in GigBid are exposed as typed MCP tools behind `agent/mcp_client.py` with per-agent allowlists, bounded retries with exponential backoff, and degraded-mode queueing.

## Own MCP Servers

| Tool | Server | Read / Write | Annotations | Auth |
|---|---|---|---|---|
| `search_evidence` | `gigbid-portfolio` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Local / None |
| `get_case_study` | `gigbid-portfolio` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Local / None |
| `list_skills` | `gigbid-portfolio` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Local / None |
| `search_jobs` | `gigbid-marketplace` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Bearer token (`MCP_MARKETPLACE_TOKEN`) |
| `get_job` | `gigbid-marketplace` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Bearer token (`MCP_MARKETPLACE_TOKEN`) |
| `get_client_history` | `gigbid-marketplace` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Bearer token (`MCP_MARKETPLACE_TOKEN`) |
| `get_connects_balance` | `gigbid-marketplace` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Bearer token (`MCP_MARKETPLACE_TOKEN`) |
| `list_messages` | `gigbid-marketplace` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Bearer token (`MCP_MARKETPLACE_TOKEN`) |
| `create_proposal_draft` | `gigbid-marketplace` | Write | `readOnlyHint=false, destructiveHint=false, idempotentHint=true` | Bearer token + `idempotency_key` + `dry_run` |
| `submit_proposal` | `gigbid-marketplace` | Write | `readOnlyHint=false, destructiveHint=true, idempotentHint=true` | Bearer token + `idempotency_key` + human approval |
| `send_message` | `gigbid-marketplace` | Write | `readOnlyHint=false, destructiveHint=true, idempotentHint=true` | Bearer token + `idempotency_key` + human approval |
| `free_calendar_slots` | `gigbid-workspace` | Read | `readOnlyHint=true, destructiveHint=false, idempotentHint=true` | Local / None |
| `create_interview_hold` | `gigbid-workspace` | Write | `readOnlyHint=false, destructiveHint=false, idempotentHint=True` | Local / None |
| `create_email_draft` | `gigbid-workspace` | Write | `readOnlyHint=false, destructiveHint=false, idempotentHint=false` | Local / None |

## Third-Party MCP Servers (A5)

| Server | Endpoint / Package | Purpose | Trust Rationale |
|---|---|---|---|
| **Upwork Official MCP** | `https://mcp.upwork.com/mcp` | Live job search, draft proposals & messaging behind `MarketplacePort` | Official Upwork-operated OAuth 2.1 Streamable HTTP server; write tools create drafts only and require explicit user confirmation on Upwork. |
| **GitHub MCP** | `@modelcontextprotocol/server-github` | Read-only repository README & code ingestion into Portfolio corpus | Official GitHub MCP server scoped to read-only public/user-authorized repo scopes with no write permissions. |

## Per-Agent Tool Allowlists (`agent/mcp_client.py`)

- `scout`: `search_jobs`
- `analyst`: *(none)*
- `risk_assessor`: `get_client_history`
- `fit_matcher`: `search_evidence`, `get_case_study`, `list_skills`
- `pricing`: `get_connects_balance`, `get_client_history`
- `writer`: `search_evidence`, `get_case_study`
- `critic`: `search_evidence`, `get_case_study`
- `compliance`: *(none)*
- `client_liaison`: `list_messages`, `send_message`, `free_calendar_slots`, `create_interview_hold`, `create_email_draft`
