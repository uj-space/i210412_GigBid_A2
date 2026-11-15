# Why Our Single-Agent Prompt Missed 100% of Scams—and Why Outcome-Aware Reranking Hurt Retrieval

When we started building **GigBid**, a multi-agent copilot for freelance marketplace bidding, our working assumptions felt almost boringly obvious. A well-structured single-agent prompt with access to portfolio tools should at least catch blatant marketplace scams. Adding outcome-aware signals—boosting portfolio case studies that previously won client replies—should strictly improve retrieval ranking over generic skill matching. And dense vector embeddings should comfortably beat lexical heuristics on semantic job descriptions.

Every single one of those assumptions turned out to be wrong when we measured them against our evaluation suites.

Across 336 retrieval queries, 90 comparative architecture runs, and 120 decision-and-safety benchmark jobs, the empirical results forced us to rethink how we separate reasoning roles, why naive outcome feedback loops corrupt retrieval precision, and why deterministic verification matters more than clever prompting. This post unpacks what actually happened in our experiments, what broke, and why simpler structural constraints outperformed more complex heuristics.

---

## Surprise 1: The Single-Agent Baseline Had 0.00% Scam Recall

Our first real shock came in `evals/results/rd_c_agent_comparison.json`, where we benchmarked a monolithic single-agent baseline against our LangGraph multi-agent graph (`bid_graph`) across 90 development jobs spanning legitimate high-fit contracts, off-platform payment scams, and prompt-injection traps.

On paper, the single-agent baseline had every instruction it needed: screen for red flags, check client verification, match skills, and only draft a proposal if the job is safe. In practice, **its scam recall was `0.0000`**, its overall decision accuracy was **`0.6222`**, and **`16.67%`** of its drafted claims were unsupported by portfolio evidence. Meanwhile, our multi-agent LangGraph pipeline achieved **`0.9889` decision accuracy**, **`1.0000` scam recall**, and **`0.0000` unsupported claim rate** (and **`0.9833` decision accuracy** with **`1.0000` scam recall** and **`1.0000` injection defense rate** across the full 120-job `decision_eval.json` benchmark).

Why did a single agent fail so completely on scams despite having explicit instructions?

The failure was not a knowledge gap; it was **task-interference bias**. When one context window is simultaneously responsible for *screening risk* and *drafting a persuasive proposal*, the generative objective dominates. A suspicious job post that mentions "urgent Python/AI automation, $4,500 fixed budget, message on Telegram for upfront crypto milestone" contains plenty of tempting skill keywords (`Python`, `AI`, `automation`) alongside two disqualifying risk signals (`Telegram`, `upfront crypto`). In a single-pass prompt, the model latches onto the skill overlap and rationalizes the risk away—or worse, skips straight into helpful proposal-drafting mode.

Splitting the workflow into isolated parallel fan-out nodes (`analyst`, `risk_assessor`, `fit_matcher`) followed by a deterministic routing gate changed the dynamic completely. The `risk_assessor` node never sees a proposal template and has zero incentive to be "helpful" toward a bad client; its only job is to emit structured red-flag and injection signals. When `risk_assessor` flags an off-platform contact request or suspicious payment pattern, the graph routes directly to `skip` before the `drafter` node is ever invoked.

There was a clear cost to this isolation: average latency jumped from **`27.95 ms`** (single-agent) to **`593.73 ms`** (multi-agent graph). Even so, ~0.59s is well inside our 15-second p95 budget, and trading half a second of latency to eliminate 100% of missed scams and 100% of unsupported claims was an easy engineering call.

---

## Surprise 2: Outcome-Aware Reranking (`v4`) Dropped nDCG@10 by 0.1303

Our second counterintuitive result came from our 10-variant RAG ablation (`evals/results/rag_eval.json` and `evals/results/ablation.json`, `n = 336` dev queries across three freelancer personas: `ai_ml_engineer`, `data_analyst`, and `fullstack_web_dev`).

We expected **Outcome-Aware Reranking (`v4`)**—which boosts portfolio items linked to historical wins and client replies—to sit at the top of our leaderboard. Instead, it **underperformed** our simpler **Hybrid + Skill/Type Rerank (`v3`)** baseline:

- **`v3` (Hybrid + Skill/Type Rerank):** `Recall@5 = 1.0000`, `nDCG@10 = 1.0000`, `MRR = 1.0000`, latency `4.870 ms`
- **`v4` (Outcome-Aware Rerank):** `Recall@5 = 0.9673`, `nDCG@10 = 0.8697`, `MRR = 0.8633`, latency `9.794 ms`

That is a **`-0.1303` drop in nDCG@10** and double the retrieval latency (`9.794 ms` vs `4.870 ms`) purely from adding historical outcome weights!

Looking closely at the per-persona breakdown explained why. In a small portfolio (~10–20 verified case studies per persona), historical outcomes are heavily skewed toward whichever skills happened to appear in early test runs. In our `gigsim_outcomes.json` simulation, 9 of 10 submitted jobs were `ai_ml_engineer` contracts (`100%` reply/hire rate), whereas `data_analyst` had 0 submissions. When `v4` applied an outcome-score bonus during retrieval, previously successful `ai_ml_engineer` case studies—like a LangGraph RAG pipeline—were pushed above more exact `data_analyst` or `fullstack_web_dev` matches whenever queries shared generic terms like `"API"`, `"dashboard"`, or `"SQL"`. That matched what we saw per persona: `v4` stayed at `1.0000` Recall@5 for `ai_ml_engineer`, but fell to `0.9405` for `data_analyst` and `0.9613` for `fullstack_web_dev`.

In short: **popularity bias masquerading as relevance**. Outcome signals belong in *style memory* (which tone or opening structure gets replies) or *bidding policy* (which job categories are worth Connects), not as a raw ranking multiplier inside evidence retrieval where factual fit to the job's exact stack is non-negotiable.

---

## Surprise 3: Naive Dense Retrieval Lost to BM25, and Chunk-Size Extremes Collapsed

Equally humbling was how badly naive dense retrieval (`v0`, TF-IDF + SVD) performed compared to lexical matching on freelance job specs:

- **`v0` (Naive Dense):** `Recall@5 = 0.5685`, `nDCG@10 = 0.5050`, `MRR = 0.5233`
- **`bm25_only` (Ablation Factor):** `Recall@5 = 0.9623`, `nDCG@10 = 0.9543`
- **`v2` (Hybrid Dense + BM25 RRF):** `Recall@5 = 0.7034`, `nDCG@10 = 0.7923`

Why did `v0` struggle so much—especially on `data_analyst` (`0.4583` Recall@5) and `fullstack_web_dev` (`0.4435` Recall@5)? Because technical hiring is brutally lexical. When a client asks for `dbt`, `Looker`, `Next.js 14`, or `FastAPI`, a compressed dense vector tends to smear `"BI dashboard tool"` across unrelated analytics projects, whereas BM25 locks onto exact stack tokens immediately. Meanwhile, variants that broke context or over-compressed representations—`v5` (`0.0000` Recall@5) and `v6` (`0.0218` Recall@5)—collapsed almost completely.

Combining Hybrid RRF with explicit **skill-tag and artifact-type reranking (`v3`)** solved the remaining gap, hitting **`1.0000` Recall@5 and `1.0000` nDCG@10** across all three personas in `4.870 ms`. We also tested **Corrective Self-RAG (`v8`)**, which tied `v3` at `1.0000` Recall@5 and `1.0000` nDCG@10, but took `5.634 ms` with extra corrective passes—making `v3` our clear shipped default for low-latency precision, with `v8` retained as an optional high-rigor toggle.

---

## Surprise 4: Retrieval Perfection Didn't Stop Unsupported Claims—Only Post-Draft Verification Did

Perhaps the most important lesson across the whole project is what *didn't* change when retrieval hit `1.0000`: **before running our claim verifier, the unsupported-claim rate was still `0.5000` (50%) across every single RAG variant (`v0` through `v9`).**

Perfect retrieval does not guarantee faithful generation. Even when the exact right case study sits in the top-3 context chunks, an LLM drafter routinely extrapolates: turning "built a FastAPI microservice" into "built a high-throughput Kubernetes-deployed FastAPI platform" or inventing a metric like "reduced latency by 40%" when the portfolio only said "reduced latency."

Our fix (`rag/verify.py`) treats every sentence in a draft proposal as a verifiable claim against the retrieved portfolio evidence, calibrated against 40 labeled claims (`evals/results/judge_calibration.json`: `1.0000` F1 and Cohen's κ). Any sentence lacking direct lexical/semantic support in a cited `portfolio://case/{id}` chunk is flagged and pruned before the draft reaches the human approval screen. That single deterministic step dropped the unsupported claim rate from **`0.5000` to `0.0000`** across all 10 RAG variants and yielded **`1.0000` proposal groundedness** on the 120-job decision suite.

---

## Surprise 5: Tool Governance Matters as Much as Prompt Defense

Finally, we measured the security impact of tool-surface design (`evals/results/rd_a_tool_design.json`). In a naive monolithic agent setup where all 9 roles can see all 4 write-capable tools, there are **36 write-tool exposures** across the system. By splitting tools into three isolated MCP servers (`portfolio`, `marketplace`, `workspace`) with strict per-agent allowlists (`AGENT_TOOL_ALLOWLISTS`), mandatory `idempotency_key` deduplication, `dry_run` previews, and LangGraph `interrupt()` gates before any external action, we cut write-tool exposures from **36 down to 2**—a **`94.44%` blast-radius reduction** (`least_privilege_score = 0.9444`).

Even if a prompt injection inside a job post somehow bypassed our `risk_assessor` delimiters (which held a `1.0000` defense rate across 120 jobs), the `analyst` and `drafter` nodes literally do not have marketplace submission or messaging tools in their schemas. They cannot spend Connects or message a client even if compromised.

---

## Takeaways for Agentic System Builders

If there is one unifying thread across these five surprises, it is that **structural boundaries beat prompt cleverness**:

1. **Separate skeptics from writers.** Never ask the same prompt pass to both detect scams and sell a candidate.
2. **Keep outcome feedback out of factual retrieval.** Use historical wins to tune tone and bidding strategy, not to override skill-exact portfolio matching.
3. **Verify claims after generation, not just before.** Perfect RAG (`1.0000` Recall@5) still hallucinates half its claims without deterministic post-draft pruning.
4. **Enforce least privilege at the MCP boundary.** Reducing write-tool exposure by `94.44%` turns prompt injection from a catastrophic exploit into a harmless no-op.

All code, evaluation runners, and raw JSON result logs are open-source in the [GigBid repository](https://github.com/uj-space/i210412_GigBid_A2).
