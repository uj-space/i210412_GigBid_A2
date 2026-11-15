# GigBid — Multi-Agent Freelancer Copilot

**Live Demo:** [https://gigbid-copilot-wnto.onrender.com](https://gigbid-copilot-wnto.onrender.com) *(Click **Reviewer Quick Login (AI/ML Engineer)** on the sign-in screen for preloaded persona access)*

**GigBid** is an end-to-end agentic AI system for freelance marketplace scouting, risk/scam screening, evidence-grounded proposal drafting, pricing strategy, client communication, and human-in-the-loop (HITL) approval.

## Architecture Highlights
- **Part A — Modular MCP Tool Layer (`mcp_servers/`, `gigsim/`)**: Three isolated MCP servers (`portfolio`, `marketplace`, `workspace`) with Pydantic input/output schemas, per-agent allowlists (`AGENT_TOOL_ALLOWLISTS`), Bearer auth, rate limiting, append-only audit logs (`mcp_audit.jsonl`), `idempotency_key` deduplication, `dry_run` previews, and `GigSimAdapter` vs draft-only `UpworkLiveAdapter`.
- **Part B — Advanced RAG & Claim Verification (`rag/`)**: Unified `HybridCorpusIndex` (TF-IDF+SVD dense, BM25, contextual, multi-vector, skill/industry graph), 10 retrieval variants (`v0`–`v9`), incremental re-indexing, and automated claim-by-claim verification/pruning (`rag/verify.py`).
- **Part C — LangGraph Multi-Agent Orchestration (`agent/`)**: Parallel `Send` fan-out (`analyst`, `risk_assessor`, `fit_matcher`), conditional `skip`/`bid` routing, bounded Critic revision loop (`max 2`), step/token budget guard (`needs_attention`), `interrupt()` approval gates, durable checkpointing, prompt-injection delimiting, PII masking, and thresholded Style/Outcome memory.
- **Part D — FastAPI Backend & 9-Screen React UI (`apps/api/`, `apps/web/`)**: 21 OpenAPI endpoints, live SSE run streaming, typed TypeScript client, `EvidenceHover` claim tooltips, and `DegradedBanner` outage handling.
- **Part E — Worker, Infra, CI & Academic Evals (`worker/`, `infra/`, `.github/`, `evals/`, `docs/`)**: Scheduled background worker, Docker Compose stack, GitHub Actions CI/Eval workflows, and full R&D evaluation suite.

## Measured Evaluation Results

### RAG Variants (`evals/results/rag_eval.json`, `n = 336` dev queries)
| Variant | Strategy | Recall@5 | nDCG@10 | MRR | Unsupp (Pre -> Post) | Latency (ms) |
|---|---|---:|---:|---:|---:|---:|
| `v0` | Naive Dense (TF-IDF+SVD) | 0.5685 | 0.5050 | 0.5233 | 0.5000 -> 0.0000 | 7.717 |
| `v2` | Hybrid Dense + BM25 (RRF) | 0.7034 | 0.7923 | 0.8139 | 0.5000 -> 0.0000 | 2.140 |
| **`v3`** | **Hybrid + Skill/Type Rerank** | **1.0000** | **1.0000** | **1.0000** | **0.5000 -> 0.0000** | **4.870** |
| `v4` | Outcome-Aware Rerank | 0.9673 | 0.8697 | 0.8633 | 0.5000 -> 0.0000 | 9.794 |
| `v7` | HyDE Hypothetical Snippet | 0.9583 | 0.9522 | 1.0000 | 0.5000 -> 0.0000 | 4.297 |
| **`v8`** | **Corrective Self-RAG** | **1.0000** | **1.0000** | **1.0000** | **0.5000 -> 0.0000** | **5.634** |
| `v9` | Skill-Industry GraphRAG | 0.8413 | 0.7863 | 0.7999 | 0.5000 -> 0.0000 | 0.259 |

### Single-Agent vs. Multi-Agent LangGraph (`evals/results/rd_c_agent_comparison.json`, `n = 90`)
| Architecture | Decision Accuracy | Scam Recall | Unsupported Rate | Avg Latency (ms) |
|---|---:|---:|---:|---:|
| Single-Agent Baseline | 0.6222 | 0.0000 | 0.1667 | 27.95 |
| **Multi-Agent LangGraph (`bid_graph`)** | **0.9889** | **1.0000** | **0.0000** | **593.73** |

### MCP Tool Design (`evals/results/rd_a_tool_design.json`) & Safety (`evals/results/decision_eval.json`)
- **Blast-Radius Reduction:** `94.44%` (`36` → `2` write-tool exposures across 9 agent roles), `100%` duplicate-submit prevention (`idempotency_key`), `dry_run` preview supported.
- **Decision & Safety (`n = 120`):** `decision_accuracy = 0.9833`, `scam_recall = 1.0`, `injection_defense_rate = 1.0`, `price_in_band_accuracy = 1.0`, `proposal_groundedness_rate = 1.0`.

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
