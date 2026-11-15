# GigBid — Multi-Agent Freelancer Copilot

**GigBid** is an end-to-end agentic AI system for freelance marketplace scouting, risk/scam screening, evidence-grounded proposal drafting, pricing strategy, client communication, and human-in-the-loop (HITL) approval.

## Architecture Highlights
- **Part A — Modular MCP Tool Layer (`mcp_servers/`, `gigsim/`)**: Three isolated MCP servers (`portfolio`, `marketplace`, `workspace`) with Pydantic input/output schemas, per-agent allowlists (`AGENT_TOOL_ALLOWLISTS`), Bearer auth, rate limiting, append-only audit logs (`mcp_audit.jsonl`), `idempotency_key` deduplication, `dry_run` previews, and `GigSimAdapter` vs draft-only `UpworkLiveAdapter`.
- **Part B — Advanced RAG & Claim Verification (`rag/`)**: Unified `HybridCorpusIndex` (TF-IDF+SVD dense, BM25, contextual, multi-vector, skill/industry graph), 10 retrieval variants (`v0`–`v9`), incremental re-indexing, and automated claim-by-claim verification/pruning (`rag/verify.py`).
- **Part C — LangGraph Multi-Agent Orchestration (`agent/`)**: Parallel `Send` fan-out (`analyst`, `risk_assessor`, `fit_matcher`), conditional `skip`/`bid` routing, bounded Critic revision loop (`max 2`), step/token budget guard (`needs_attention`), `interrupt()` approval gates, durable checkpointing, prompt-injection delimiting, PII masking, and thresholded Style/Outcome memory.
- **Part D — FastAPI Backend & 9-Screen React UI (`apps/api/`, `apps/web/`)**: 21 OpenAPI endpoints, live SSE run streaming, typed TypeScript client, `EvidenceHover` claim tooltips, and `DegradedBanner` outage handling.
- **Part E — Worker, Infra, CI & Academic Evals (`worker/`, `infra/`, `.github/`, `evals/`, `docs/`)**: Scheduled background worker, Docker Compose stack, GitHub Actions CI/Eval workflows, and full R&D evaluation suite.

## Quickstart

### 1. Local Python & Web Setup
```bash
pip install -e ".[dev]"
cd apps/web && npm install && npm run build
```

### 2. Run Backend & Frontend
```bash
uvicorn apps.api.main:app --reload --port 8000
cd apps/web && npm run dev
```

### 3. Run Tests & Evaluations
```bash
# Unit, Contract & Integration Tests
python -m pytest tests/unit tests/contract tests/integration mcp_servers/*/tests -q -p no:warnings

# R&D & Benchmark Evaluations
python -m evals.runners.rag_eval
python -m evals.runners.ablation
python -m evals.runners.judge_calibration
python -m evals.runners.decision_eval
python -m evals.runners.rd_a_tool_design
python -m evals.runners.rd_c_agent_comparison
python -m evals.runners.gigsim_outcomes
python -m evals.runners.proposal_experiments
```

## Datasets & Documentation
See [docs/DATA_CARD.md](docs/DATA_CARD.md) for full attribution of the 6 Kaggle datasets and synthetic persona/dev-set generation, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/TOOLS.md](docs/TOOLS.md), [docs/RUNBOOK.md](docs/RUNBOOK.md), [docs/AI_USAGE.md](docs/AI_USAGE.md), and [docs/R_AND_D_REPORT.md](docs/R_AND_D_REPORT.md).
