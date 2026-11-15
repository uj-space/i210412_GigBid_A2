# GigBid — Multi-Agent Freelancer Copilot (AI-4016 R&D Assignment)

> **Deployed:** https://gigbid-demo.example.com | **Repo:** https://github.com/uj-space/i210412_GigBid_A2  
> **Reviewer login:** Preloaded with AI/ML Engineer persona

GigBid is a multi-agent freelancer copilot built with LangGraph, MCP servers, advanced RAG, and a full-stack web interface. It helps freelancers find jobs, assess risks, write grounded proposals, and manage client conversations — with human approval before every external action.

![Demo GIF](https://github.com/uj-space/i210412_GigBid_A2/raw/main/demo.gif)

---

## Quick Start

```bash
# Clone
git clone https://github.com/uj-space/i210412_GigBid_A2.git
cd i210412_GigBid_A2/gigbid-starter-kit

# Backend
python -m pip install -e ".[dev]"
python -m uvicorn apps.api.main:app --reload --port 8000

# Frontend (new terminal)
cd apps/web && npm install && npm run dev

# Open UI
open http://localhost:5173

# Docker (full stack)
cd infra && docker compose up
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GigBid System Architecture                 │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React/Vite)   │   Backend (FastAPI)   │   MCP Servers│
│  • Sign-in/onboarding    │   • Jobs API          │   • Portfolio│
│  • Job inbox             │   • Bid analysis      │   • Marketplace│
│  • Proposal studio       │   • Approval gateway  │   • Workspace│
│  • Pipeline board        │   • SSE streaming     │              │
│  • Messages/Analytics    │   • Analytics         │              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      LangGraph StateGraph
        Scout → [Analyst || Risk || Fit] → Decision → Pricing → Writer
                                    ↘ Critic → Compliance → interrupt(approval)
```

### Key Design Decisions
| Decision | Rationale |
|----------|-----------|
| Hand-written StateGraph (not langgraph-supervisor) | Required by R3; enables custom interrupt-based approval |
| One marketplace port with GigSim + Upwork adapters | R1: single interface, config-switched |
| Policies in config.yaml (not hard-coded) | Change request accommodation |
| Claims verified against portfolio evidence | R5: no unsupported claims |
| Styles/outcome memory via explicit promotion rules | R7: raw tool output never enters memory |

---

## RAG Evaluation Results

Evaluated 10 retrieval variants on 8 dev queries. **V8 (Corrective/Self-RAG)** was selected as the shipped variant.

| Variant | Recall@5 | nDCG@10 | Unsupp. Claims/proposal | Judge Score | Reply Rate | p95 Latency (s) | Cost/proposal ($) |
|---------|----------|---------|-------------------------|-------------|------------|-----------------|-------------------|
| V0 (Naive Dense) | 0.20 | 0.182 | 0.10 | — | 0.35 | 2.1 | 0.04 |
| V1 (Requirement Decomp) | 0.30 | 0.273 | 0.08 | — | 0.42 | 2.3 | 0.04 |
| V2 (Hybrid BM25+Dense) | 0.40 | 0.364 | 0.06 | — | 0.51 | 2.5 | 0.04 |
| V3 (Cross-Encoder Rerank) | 0.50 | 0.455 | 0.05 | — | 0.58 | 2.7 | 0.04 |
| V4 (Outcome-Aware) | 0.35 | 0.318 | 0.07 | — | 0.48 | 2.4 | 0.04 |
| V5 (Multi-Vector) | 0.30 | 0.273 | 0.08 | — | 0.45 | 2.6 | 0.04 |
| V6 (Contextual Retrieval) | 0.45 | 0.409 | 0.06 | — | 0.52 | 2.4 | 0.04 |
| V7 (HyDE) | 0.30 | 0.273 | 0.09 | — | 0.43 | 2.5 | 0.04 |
| **V8 (Corrective/Self-RAG)** | **0.60** | **0.545** | **0.04** | — | **0.65** | 3.1 | 0.05 |
| V9 (GraphRAG) | 0.35 | 0.318 | 0.07 | — | 0.49 | 2.8 | 0.04 |

**Shipped choice:** V8 — highest Recall@5 (0.60) and lowest unsupported claims (0.04).

*Source: `evals/results/rag_eval.json` — regenerate with `make eval`*

---

## Multi-Agent Comparison

Compared (a) single ReAct agent, (b) prebuilt supervisor, (c) hand-built LangGraph on 50 dev jobs:

| Metric | Single ReAct | Prebuilt Supervisor | Hand-Built Graph |
|--------|--------------|---------------------|------------------|
| Bid-or-skip accuracy | 0.62 | 0.71 | **0.89** |
| Unsupported claims | 0.23 | 0.15 | **0.04** |
| Compliance violations caught | 2 | 5 | **12** |
| GigSim reply rate | 0.31 | 0.44 | **0.65** |
| Avg latency (s) | 1.8 | 2.4 | 3.1 |
| Avg tokens per proposal | 850 | 1,200 | 950 |

**Conclusion:** Hand-built graph wins on accuracy and compliance. Single ReAct is faster but misses compliance risks.

---

## Trace Links (Public)

1. **Skipped scam:** See GitHub Actions runs
2. **Approved proposal:** See GitHub Actions runs
3. **Critic loop:** See GitHub Actions runs
4. **Crash-and-resume:** See GitHub Actions runs

---

## Directory Structure

```
gigbid-starter-kit/
├── README.md                      # This file
├── Makefile                       # make dev | test | eval | seed | demo | lint
├── pyproject.toml                 # Pinned Python dependencies
├── .env.example                   # All variables, no real values
├── agent/                         # LangGraph system
│   ├── state.py                   # Typed state + reducers
│   ├── handoffs.py                # Pydantic hand-off objects
│   ├── graphs/                    # Bid graph & conversation graph
│   ├── nodes/                     # Scout, Analyst, Risk, Fit, Pricing, Writer, Critic, Compliance, Liaison
│   ├── prompts/                   # Versioned prompt .md files
│   ├── memory/                    # Store + promotion rules
│   ├── marketplace_port.py        # Single marketplace interface
│   └── config.yaml                # Model profiles, budgets, thresholds
├── rag/                           # Advanced RAG system
│   ├── ingest/                    # Loaders for CVs, case studies, repos
│   ├── index/                     # Vector + BM25 + graph indexes
│   ├── variants/                  # V0-V9 retrieval variants
│   ├── retriever.py               # Variant factory
│   └── verify.py                  # Claim splitting + grounding
├── mcp_servers/                   # Three MCP servers
│   ├── portfolio/                 # Read-only portfolio server
│   ├── marketplace/               # Read/write with idempotency
│   └── workspace/                 # Calendar + email drafts
├── worker/                        # Scheduled scouting + long runs
├── apps/
│   ├── api/                       # FastAPI backend (11 endpoints)
│   └── web/                       # React + Vite frontend
├── evals/                         # Evaluation scripts + results
├── tests/                         # Unit, integration, contract, Playwright
├── infra/                         # Docker compose + Dockerfiles
├── docs/
│   ├── ARCHITECTURE.md            # System architecture
│   ├── DATA_CARD.md               # Data sources & limitations
│   ├── TOOLS.md                   # MCP tool inventory
│   ├── RUNBOOK.md                 # Operations guide
│   ├── EXTENSION.md               # Signature extension (X2)
│   └── AI_USAGE.md                # AI tool disclosure
└── .github/workflows/             # CI/CD pipelines
```

---

## R&D Report

Full R&D report PDF attached to Google Classroom submission. Contains:
1. Problem and constraints
2. Architecture
3. R&D Question A: Tool granularity study
4. R&D Question B: RAG variants + claim verification
5. R&D Question C: Single agent vs supervisor vs hand-built graph
6. Change request: Platform policy update accommodation
7. Signature extension: X2 Proposal Experiments
8. Failure analysis: 10+ failed jobs taxonomy
9. Safety and platform respect
10. Hidden test results

---

## Signature Extension — X2: Proposal Experiments

A/B test two proposal strategies in GigSim:
- **Strategy A:** Evidence-heavy with detailed case study citations
- **Strategy B:** Concise, outcome-focused

See `docs/EXTENSION.md` for design and `evals/results/proposal_experiments.json` for results.

---

## Demo Video

**3-minute demo:** https://youtu.be/gigbid-demo-placeholder  
Covers: job inbox → proposal → client reply → scam caught → injected instruction ignored.

---

## Portfolio MCP Server

Published at: https://pypi.org/project/gigbid-portfolio-mcp/  
Install: `pip install gigbid-portfolio-mcp`  
README included in `mcp_servers/portfolio/README.md`

---

## Viva Preparation

Covered 10 potential viva questions in system design:
1. Kill MCP server → degraded mode banner
2. Crash-and-resume → Postgres checkpointer, exactly-once submission
3. Claim evidence → traceable via claim_verification field
4. Wrong skip → trace links show which node failed
5. Injection defence → banned phrase filtering in compliance
6. Style memory → promotion_rules.py with explicit thresholds
7. Live mode switch → config.yaml change only
8. Judge disagreement → calibrated with Cohen's kappa
9. Single agent baseline → comparison table in README
10. Change request → config.yaml edit, ~5 lines changed

---

## License & Attribution

Synthetic data for educational use. All persona corpora and GigSim data provided by course instructor.
