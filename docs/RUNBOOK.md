# GigBid Operations Runbook

## 1. Local Development
- **Install Python deps:** `pip install -e ".[dev]"`
- **Install Web deps:** `cd apps/web && npm install`
- **Start FastAPI backend:** `uvicorn apps.api.main:app --reload --port 8000`
- **Start React frontend:** `cd apps/web && npm run dev`
- **Run single worker cycle:** `python -m worker.run --once`

## 2. Docker Compose Deployment
```bash
docker compose -f infra/docker-compose.yml up --build
```
Services: `postgres`, `mcp-portfolio`, `mcp-marketplace`, `mcp-workspace`, `api`, `worker`, `web`.

## 3. Degraded Mode & Outage Recovery
- If Marketplace MCP fails or is toggled into degraded mode (`POST /api/marketplace/degraded?flag=true`):
  - `GET /api/health` returns `"marketplace_degraded": true`.
  - The React UI renders `DegradedBanner` (`data-testid="degraded-banner"`).
  - Pending tool calls are queued in `agent/mcp_client.py` (`get_degraded_queue()`).
  - Recovery: restore Marketplace MCP and click **Retry Connection** (or `POST /api/marketplace/degraded?flag=false`).

## 4. Crash & Replay Recovery
- LangGraph checkpoints state at every node (`PostgresSaver` when `DATABASE_URL` is configured, `MemorySaver` locally).
- To replay a thread from a specific node (e.g., `writer`), call `replay_from_node(thread_id, as_node="writer")`.

## 5. Evaluation & Test Suite
- **Unit + Contract + Integration Tests:** `python -m pytest tests/unit tests/contract tests/integration mcp_servers/*/tests -q -p no:warnings`
- **RAG & Evals:** `python -m evals.runners.rag_eval`, `ablation`, `judge_calibration`, `decision_eval`, `rd_a_tool_design`, `rd_c_agent_comparison`, `gigsim_outcomes`, `proposal_experiments`.
