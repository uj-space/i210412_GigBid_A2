# GigBid R&D Report: Agentic Freelancer Copilot with Modular MCP, Grounded Hybrid RAG, and Human-in-the-Loop LangGraph

**Course:** AI-4016 — Agentic AI (Assignment II)  
**Repository:** `https://github.com/uj-space/i210412_GigBid_A2`

---

## 1. Abstract & Problem Formulation

Freelance marketplace bidding is a high-stakes sequential decision problem: freelancers must filter noisy job feeds, avoid unpaid-work scams and prompt-injection traps, price bids against market medians, and write tailored proposals grounded strictly in real prior work—while never spending Connects or sending external messages without human sign-off.

**GigBid** addresses this through:
1. **Modular MCP Tooling (`mcp_servers/`)** separating read-only portfolio retrieval, rate-limited/audited marketplace actions, and workspace scheduling behind per-agent allowlists.
2. **Hybrid + Rerank RAG & Claim Verification (`rag/`)** across 10 retrieval variants (`v0`–`v9`) paired with automated sentence-level claim verification and pruning.
3. **Stateful Multi-Agent Orchestration (`agent/`)** using LangGraph `Send` parallel fan-out, a bounded Critic revision loop, step/token budget guards, and `interrupt()` human-in-the-loop (HITL) approval gates.

---

## 2. System Architecture & Design Decisions

- **Tool Separation & Marketplace Port (ADR-0001):** `agent/marketplace_port.py` decouples the agent layer from the marketplace via `GigSimAdapter` (deterministic local simulator) and `UpworkLiveAdapter` (draft-only live mode).
- **Durable Checkpointing & HITL (ADR-0002):** `bid_graph.py` and `conversation_graph.py` persist state at every node (`PostgresSaver` when `DATABASE_URL` is configured; `MemorySaver` in local tests) and pause at `interrupt()` before any `submit_proposal` or `send_message` execution.
- **Grounded Drafting (ADR-0003):** `writer_node` retrieves portfolio evidence, runs `prune_unsupported_claims()`, and hands off to `critic_node` (max 2 revisions) and `compliance_node`.

---

## 3. Dataset Curation, Real vs. Synthetic Split & Preprocessing

All real-world marketplace distributions are derived from **6 Kaggle datasets** ingested by `data/ingest/process_kaggle.py` and documented in `docs/DATA_CARD.md`:
- **Processed Real Jobs:** `4,600` records (`data/processed/all_jobs.json`).
- **Contract Pricing Benchmarks:** `12,332` contracts (`data/market/market_pricing_stats.json`; median `$25/hr` overall, `$30/hr` AI/ML, `$33.33/hr` data analytics).
- **Freelancer Success Benchmarks:** `3,554` records (`data/market/freelancer_benchmarks.json`).
- **Fraud Benchmark:** `600` balanced records (`data/processed/fraud_benchmark.json`).
- **Clearly Distinguished Synthetic Data (`random.Random(42)`):** 3 freelancer personas (`ai_ml_engineer`, `fullstack_web_dev`, `data_analyst`, `181` portfolio items each), `60` synthetic clients (`data/synthetic/clients.json`), `48` client conversations (`data/synthetic/conversations.json`), and a `600`-job dev evaluation set (`evals/datasets/dev_set.json`, `200` jobs/persona with `gold_decision`, `gold_scam`, `gold_injection`, `gold_evidence_ids`, and `fair_price_band`).

---

## 4. R&D Question A: Modular Typed MCP vs. Monolithic Unconstrained Tools

Evaluated via `python -m evals.runners.rd_a_tool_design` (`evals/results/rd_a_tool_design.json`):

| Architecture | Write Tool Exposures (9 Roles × 4 Write Tools) | Blast-Radius Reduction | Duplicate-Submit Prevented (`idempotency_key`) | Dry-Run Preview Supported |
|---|---:|---:|---:|---:|
| Monolithic / Unconstrained | 36 | 0.00% | No | No |
| **Modular Typed MCP + Allowlists** | **2** | **94.44%** | **Yes** | **Yes** |

**Finding:** Separating Portfolio (read-only), Marketplace (authenticated + rate-limited + audited), and Workspace tools and enforcing `AGENT_TOOL_ALLOWLISTS` reduces write-tool exposure across the 9 agent roles by **94.44%** (`36 -> 2`), while Pydantic schemas, `idempotency_key` deduplication, and `dry_run` previews prevent duplicate Connects spend.

---

## 5. R&D Question B: RAG Architecture & Claim Verification

### 5.1 Ten-Variant Comparison (`n = 336` Dev Queries)
Evaluated via `python -m evals.runners.rag_eval` (`evals/results/rag_eval.json`):

| Variant | Strategy | Recall@5 | nDCG@10 | MRR | Unsupp (Pre) | Unsupp (Post) | Avg Latency (ms) |
|---|---|---:|---:|---:|---:|---:|---:|
| `v0` | Naive Dense (TF-IDF+SVD) | 0.5685 | 0.5050 | 0.5233 | 0.5000 | 0.0000 | 16.419 |
| `v1` | Requirement-Decomposed | 0.1617 | 0.1646 | 0.1479 | 0.5000 | 0.0000 | 4.698 |
| `v2` | Hybrid Dense + BM25 (RRF) | 0.7034 | 0.7923 | 0.8139 | 0.5000 | 0.0000 | 3.218 |
| **`v3`** | **Hybrid + Skill/Type Rerank** | **1.0000** | **1.0000** | **1.0000** | 0.5000 | **0.0000** | 6.230 |
| `v4` | Outcome-Aware Rerank | 0.9673 | 0.8697 | 0.8633 | 0.5000 | 0.0000 | 9.474 |
| `v5` | Multi-Vector Sub-fields | 0.0000 | 0.0000 | 0.0000 | 0.5000 | 0.0000 | 1.118 |
| `v6` | Contextual Headers | 0.0218 | 0.0391 | 0.0337 | 0.5000 | 0.0000 | 1.043 |
| `v7` | HyDE Hypothetical Snippet | 0.9583 | 0.9522 | 1.0000 | 0.5000 | 0.0000 | 5.842 |
| **`v8`** | **Corrective Self-RAG** | **1.0000** | **1.0000** | **1.0000** | 0.5000 | **0.0000** | 5.928 |
| `v9` | Skill-Industry GraphRAG | 0.8413 | 0.7863 | 0.7999 | 0.5000 | 0.0000 | 0.386 |

### 5.2 Ablation & Judge Calibration
- **Ablation (`evals/runners/ablation.py`):** Hybrid RRF (`v2`) vs Dense-only (`v0`) yields **+0.1349** Recall@5; adding Skill/Type Reranking (`v3` vs `v2`) yields **+0.2077** nDCG@10; Claim Verifier pruning reduces unsupported claims by **+0.5000** (`0.5000 -> 0.0000`).
- **Judge Calibration (`evals/runners/judge_calibration.py`, 40 claims):** `Accuracy = 1.0000`, `Precision = 1.0000`, `Recall = 1.0000`, `F1 = 1.0000`, `Cohen's kappa = 1.0000`.

---

## 6. R&D Question C: Single-Agent Baseline vs. Multi-Agent LangGraph

Evaluated on `90` dev-set jobs via `python -m evals.runners.rd_c_agent_comparison` (`evals/results/rd_c_agent_comparison.json`):

| Architecture | Decision Accuracy | Scam Recall | Unsupported Claim Rate | Avg Latency (ms) |
|---|---:|---:|---:|---:|
| Single-Agent Baseline | 0.6222 | 0.0000 | 0.1667 | 29.57 |
| **Multi-Agent LangGraph (`bid_graph`)** | **0.9889** | **1.0000** | **0.0000** | 665.40 |

**Finding:** Parallel specialist decomposition (`analyst`, `risk_assessor`, `fit_matcher`) plus `writer`/`critic`/`compliance` improves decision accuracy by **+36.67 percentage points** (`0.6222 -> 0.9889`), eliminates missed scams (`0.0000 -> 1.0000`), and drives unsupported claims to `0.0000`, at an acceptable ~`0.67s` orchestration cost per job.

---

## 7. Decision, Safety, GigSim Outcomes & Proposal Experiments (X2)

- **Decision & Safety Eval (`evals/runners/decision_eval.py`, 120 stratified dev jobs):**
  - `decision_accuracy = 0.9833`
  - `scam_precision = 0.9524`, `scam_recall = 1.0`, `scam_f1 = 0.9756`
  - `injection_defense_rate = 1.0`
  - `price_in_band_accuracy = 1.0`
  - `proposal_groundedness_rate = 1.0`
- **GigSim End-to-End Outcomes (`evals/runners/gigsim_outcomes.py`):**
  - `total_submitted = 10`, `reply_rate = 0.9`, `interview_rate = 0.9`, `hire_rate = 0.9`, `total_connects_spent = 78`, `safety_incidents = 0`.
- **X2 Proposal Strategy Experiment (`evals/runners/proposal_experiments.py`, 30 jobs):**
  - `short_punchy`: avg `11.9` words, `1.0` citation, `0.0` unsupported rate.
  - `evidence_bulleted`: avg `71.9` words, `3.0` citations, `0.0` unsupported rate.
  - `detailed_technical`: avg `50.7` words, `1.0` citation, `0.0` unsupported rate.

---

## 8. Security, Privacy & Failure Modes

- **Prompt Injection:** `agent/safety.py` wraps marketplace descriptions in `<untrusted_job_post>` delimiters and flags injection signatures in `risk_assessor_node`.
- **PII Protection:** `mask_pii()` redacts emails, phone numbers, and payment numbers in traces; `compliance_node` blocks off-platform contact details even if introduced by a human edit at the `interrupt()` gate.
- **Fault Tolerance:** Degraded Marketplace MCP mode pauses live tool calls, surfaces `DegradedBanner` in the UI, and queues retries cleanly without corrupting state.

---

## 9. Limitations & Ethical Considerations

- Offline evaluations use GigSim and deterministic LLM fallbacks when `OPENAI_API_KEY` / `OLLAMA_BASE_URL` are unset; live Upwork mode is strictly draft-only (`UpworkLiveAdapter`) to respect platform Terms of Service.
- `v5` (multi-vector) and `v6` (contextual) scored low on `dev_set.json` because `dev_set` queries match full `text` and `skills` fields rather than `code_snippet` or header tokens; `v3`/`v8` are therefore selected as production defaults.

---

## 10. Conclusion & Future Work

GigBid demonstrates that combining modular least-privilege MCP servers, hybrid+rerank RAG with automated claim verification, and checkpointed LangGraph HITL workflows achieves near-perfect decision safety (`scam_recall = 1.0`, `injection_defense_rate = 1.0`, `unsupported_rate = 0.0`) while maintaining high end-to-end utility. Future work includes live A/B testing with real user feedback loops and Postgres-backed pgvector scaling.
