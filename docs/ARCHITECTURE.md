# GigBid Architecture

GigBid is a multi-agent freelancer copilot built on **LangGraph**, **Model Context Protocol (MCP)**, **Hybrid + Rerank RAG**, **FastAPI**, and **React + TypeScript**.

## System Layers

```
+-----------------------+       SSE / REST        +---------------------------+
| React + TS Web UI     | <---------------------> | FastAPI Backend (apps/api)|
| (9 screens + HITL)    |                         | Auth, Approvals, Runs     |
+-----------------------+                         +-------------+-------------+
                                                                |
+-----------------------+                                       v
| Background Worker     |                         +---------------------------+
| (worker/run.py)       | ----------------------> | LangGraph Workflows       |
+-----------------------+                         | bid_graph & conv_graph    |
                                                  +-------------+-------------+
                                                                |
          +-----------------------+-----------------------------+-----------------------+
          v                       v                             v                       v
+-------------------+   +-------------------+       +-------------------+   +-------------------+
| Portfolio MCP     |   | Marketplace MCP   |       | Workspace MCP     |   | RAG & Verifier    |
| (Read-only)       |   | (GigSim / Upwork) |       | (Cal / Email)     |   | (V0-V9 + Verify)  |
+-------------------+   +-------------------+       +-------------------+   +-------------------+
```

## LangGraph Orchestration (`agent/graphs/bid_graph.py`)

1. **Scout (`scout_node`)**: Normalizes job posting and saved-search context.
2. **Parallel Fan-Out (`Send`)**: Runs `analyst_node`, `risk_assessor_node`, and `fit_matcher_node` concurrently.
3. **Decision (`_decision_node`)**: Routes scam or low-fit jobs directly to `skip -> END`; routes qualified jobs (`bid`/`watch`) to `pricing_node`.
4. **Pricing (`pricing_node`)**: Queries Kaggle contract market medians (`data/market/market_pricing_stats.json`) and Connects balance via Marketplace MCP.
5. **Writer (`writer_node`) & Critic (`critic_node`)**: Drafts grounded proposals using RAG (`rag/retriever.py`), prunes unsupported claims (`rag/verify.py`), and runs a bounded revision loop (`max 2` revisions) with a step/token budget guard (`needs_attention`).
6. **Compliance (`compliance_node`) & Approval Gate (`_approval_gate`)**: Enforces policy rules and pauses via LangGraph `interrupt()` until the human approves, edits (with compliance re-check), or rejects.

## Trust Boundaries & Safety

- Untrusted marketplace text is wrapped in `<untrusted_job_post>` delimiters (`agent/safety.py`).
- PII (`email`, `phone`, `payment`) is masked in logs and traces via `mask_pii()`.
- Per-agent allowlists (`AGENT_TOOL_ALLOWLISTS` in `agent/mcp_client.py`) restrict write tools exclusively to approved execution paths.
- Every marketplace write requires an `idempotency_key` and writes an append-only record to `data/processed/mcp_audit.jsonl`.
