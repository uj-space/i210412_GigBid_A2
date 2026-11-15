"""Generate charts and academic <=10-page GigBid R&D Report PDF (docs/GigBid_RD_Report.pdf)."""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results"
IMG_DIR = ROOT / "docs" / "images"
IMG_DIR.mkdir(parents=True, exist_ok=True)


def _make_charts() -> tuple[Path, Path]:
    rag = json.loads((RESULTS / "rag_eval.json").read_text(encoding="utf-8"))["variants"]
    vids = list(rag.keys())
    recalls = [rag[v]["evidence_recall_at_5"] for v in vids]
    ndcgs = [rag[v]["ndcg_at_10"] for v in vids]

    fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=180)
    x = range(len(vids))
    w = 0.36
    ax.bar([i - w / 2 for i in x], recalls, width=w, label="Recall@5", color="#4f46e5")
    ax.bar([i + w / 2 for i in x], ndcgs, width=w, label="nDCG@10", color="#10b981")
    ax.set_xticks(list(x))
    ax.set_xticklabels([v.upper() for v in vids], fontsize=8)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Score", fontsize=8)
    ax.set_title("R&D-B: 10 RAG Variants on Dev Set (n = 336 queries)", fontsize=9, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    c1 = IMG_DIR / "rag_variants_comparison.png"
    fig.savefig(c1)
    plt.close(fig)

    rdc = json.loads((RESULTS / "rd_c_agent_comparison.json").read_text(encoding="utf-8"))
    sa = rdc["single_agent_baseline"]
    ma = rdc["multi_agent_langgraph"]
    metrics = ["Decision Acc", "Scam Recall", "Groundedness (1 - Unsupp)"]
    sa_vals = [sa["decision_accuracy"], sa["scam_recall"], 1.0 - sa["avg_unsupported_claim_rate"]]
    ma_vals = [ma["decision_accuracy"], ma["scam_recall"], 1.0 - ma["avg_unsupported_claim_rate"]]

    fig, ax = plt.subplots(figsize=(6.8, 2.4), dpi=180)
    x2 = range(len(metrics))
    ax.bar([i - w / 2 for i in x2], sa_vals, width=w, label="Single-Agent Baseline", color="#94a3b8")
    ax.bar([i + w / 2 for i in x2], ma_vals, width=w, label="Multi-Agent LangGraph", color="#4f46e5")
    ax.set_xticks(list(x2))
    ax.set_xticklabels(metrics, fontsize=8)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score", fontsize=8)
    ax.set_title("R&D-C: Single-Agent vs. Multi-Agent LangGraph (n = 90 dev jobs)", fontsize=9, fontweight="bold")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    c2 = IMG_DIR / "agent_comparison.png"
    fig.savefig(c2)
    plt.close(fig)

    return c1, c2


class ReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 116, 139)
            self.cell(0, 5, "AI-4016 Agentic AI | GigBid Engineering Design Review & R&D Report", align="L")
            self.cell(0, 5, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.ln(1)

    def h1(self, text: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 11.5)
        self.set_text_color(30, 41, 59)
        self.cell(0, 6.5, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(79, 70, 229)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def h2(self, text: str):
        self.ln(1)
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(51, 65, 85)
        self.cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")

    def body(self, text: str):
        self.set_font("Helvetica", "", 8.8)
        self.set_text_color(30, 41, 59)
        self.multi_cell(0, 4.3, text)
        self.ln(1.2)

    def bullet(self, lead: str, text: str):
        self.set_font("Helvetica", "B", 8.8)
        self.set_text_color(30, 41, 59)
        self.write(4.3, f"  * {lead}: ")
        self.set_font("Helvetica", "", 8.8)
        self.multi_cell(0, 4.3, text)

    def table(self, headers: list[str], rows: list[list[str]], widths: list[float]):
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(238, 242, 255)
        self.set_text_color(30, 41, 59)
        for h, w in zip(headers, widths):
            self.cell(w, 5.5, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("Helvetica", "", 7.8)
        for idx, row in enumerate(rows):
            fill = idx % 2 == 1
            self.set_fill_color(248, 250, 252)
            for val, w in zip(row, widths):
                self.cell(w, 5.0, val, border=1, fill=fill, align="C")
            self.ln()
        self.ln(1.5)


def build_pdf() -> Path:
    c1, c2 = _make_charts()
    rag = json.loads((RESULTS / "rag_eval.json").read_text(encoding="utf-8"))
    abl = json.loads((RESULTS / "ablation.json").read_text(encoding="utf-8"))
    jc = json.loads((RESULTS / "judge_calibration.json").read_text(encoding="utf-8"))
    dec = json.loads((RESULTS / "decision_eval.json").read_text(encoding="utf-8"))["metrics"]
    rda = json.loads((RESULTS / "rd_a_tool_design.json").read_text(encoding="utf-8"))
    rdc = json.loads((RESULTS / "rd_c_agent_comparison.json").read_text(encoding="utf-8"))
    gs = json.loads((RESULTS / "gigsim_outcomes.json").read_text(encoding="utf-8"))
    x2 = json.loads((RESULTS / "proposal_experiments.json").read_text(encoding="utf-8"))

    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=13)
    pdf.set_margins(14, 13, 14)
    pdf.add_page()

    # Title Banner
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(49, 46, 129)
    pdf.cell(0, 8, "GigBid: Engineering Design Review & R&D Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 5, "AI-4016 Agentic AI (Assignment II)  |  Repo: github.com/uj-space/i210412_GigBid_A2", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Live Deployment (open profile): https://gigbid-copilot-wnto.onrender.com  |  Reviewer Quick Login enabled", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # 1. Problem & Constraints
    pdf.h1("1. Problem and Constraints")
    pdf.body(
        "Freelance marketplace bidding is a high-stakes sequential workflow: scouting feeds, screening clients for "
        "scams or prompt injections, assessing skill fit, pricing against market rates, drafting evidence-grounded "
        "proposals, and managing client follow-ups. Automation reduces search toil, but irreversible external actions "
        "carry financial (Connects spend) and reputational (terms-of-service, hallucinated claims) risk."
    )
    pdf.bullet("Never Automated", "Spending Connects, submitting proposals, sending external client messages, or booking calendar holds. All external writes pause behind LangGraph interrupt() gates (agent/graphs/bid_graph.py, conversation_graph.py; commit f000631).")
    pdf.bullet("Declared Budgets (agent/config.yaml)", "max_graph_steps = 30, max_revisions = 2, max_tokens_per_job = 12,000, p95_latency_budget_s = 15.0s, cost_budget_usd = $0.05/job (open profile targets $0.00/job via Groq/NVIDIA/OpenRouter free tiers + local deterministic fallback).")

    # 2. Architecture
    pdf.h1("2. System Architecture")
    pdf.body(
        "GigBid separates orchestration, tools, retrieval, and UI across five bounded layers (docs/ARCHITECTURE.md, ADRs 0001-0003):"
    )
    pdf.bullet("Graphs (agent/graphs/)", "bid_graph (one thread per job) fans out via LangGraph Send to analyst, risk_assessor, and fit_matcher in parallel, routes skip -> END or bid/watch -> pricing -> writer <-> critic (bounded <=2 revisions) -> compliance -> _approval_gate (interrupt()). conversation_graph triages client messages via client_liaison -> _approve_message (interrupt()).")
    pdf.bullet("Why Each Agent Exists", "Scout (normalizes feed/searches), Analyst (extracts JobSpec), Risk Assessor (scam/injection scoring via client history), Fit Matcher (persona RAG evidence overlap), Pricing Strategist (Kaggle median + Connects check), Writer (grounded drafting + claim pruning), Critic (adversarial review), Compliance Guard (policy/PII enforcement), Client Liaison (intent + scheduling).")
    pdf.bullet("Marketplace Port & MCP Surface", "agent/marketplace_port.py abstracts GigSimAdapter (offline simulator, gigsim/simulator.py) and UpworkLiveAdapter (draft-only live mode). Three MCP servers (portfolio read-only, marketplace authenticated/rate-limited/audited, workspace calendar/email) enforce AGENT_TOOL_ALLOWLISTS (commit 8e/Step 2).")
    pdf.bullet("Stores", "HybridCorpusIndex (dense SVD + BM25 + graph, rag/index/hybrid_index.py), GigBidMemoryStore (JSON-backed style/outcome memory with >=3 edit promotion, agent/memory/store.py), Fernet-encrypted OAuth token store (apps/api/auth/tokens.py), and append-only mcp_audit.jsonl.")

    # 3. R&D Question A
    pdf.h1("3. R&D Question A: Tool Granularity")
    pdf.body(
        "Hypothesis: Splitting tools into three domain-scoped, Pydantic-typed MCP servers with per-agent allowlists, "
        "idempotency_key deduplication, and dry_run previews reduces write-action blast radius and prevents duplicate "
        "Connects spend without harming workflow completion (evals/runners/rd_a_tool_design.py -> evals/results/rd_a_tool_design.json)."
    )
    pdf.table(
        ["Design", "Write Exposures (9 Roles x 4 Tools)", "Blast-Radius Reduction", "Duplicate Submit Prevented", "Dry-Run Preview"],
        [
            ["Monolithic Unconstrained", str(rda["monolithic_unconstrained"]["write_tool_exposures_across_roles"]), "0.00%", "No", "No"],
            ["Modular Typed MCP + Allowlists", str(rda["modular_typed_mcp"]["write_tool_exposures_across_roles"]), f"{rda['modular_typed_mcp']['blast_radius_reduction_pct']}%", "Yes", "Yes"],
        ],
        [52, 46, 34, 30, 20],
    )
    pdf.body(
        "Conclusion: Enforcing AGENT_TOOL_ALLOWLISTS cut write-tool exposure across the 9 agent roles by 94.44% (36 -> 2), "
        "while idempotency_key deduplication and dry_run previews eliminated accidental double-submission."
    )

    # 4. R&D Question B
    pdf.h1("4. R&D Question B: RAG Variants, Claim Verification, and Ablation")
    pdf.body(
        "We evaluated all 10 retrieval variants (v0-v9) on n = 336 dev-set bid queries with gold_evidence_ids "
        "(evals/runners/rag_eval.py -> evals/results/rag_eval.json, commit 9f4852a) and 40 claims for judge calibration "
        "(evals/results/judge_calibration.json: Accuracy = 1.0000, Precision = 1.0000, Recall = 1.0000, F1 = 1.0000, Cohen's kappa = 1.0000)."
    )
    rows_b = []
    for vid in ["v0", "v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]:
        v = rag["variants"][vid]
        pp = v["per_persona_recall_at_5"]
        rows_b.append([
            vid.upper(),
            f"{v['evidence_recall_at_5']:.4f}",
            f"{v['ndcg_at_10']:.4f}",
            f"{v['mrr']:.4f}",
            f"{pp['ai_ml_engineer']:.2f} / {pp['data_analyst']:.2f} / {pp['fullstack_web_dev']:.2f}",
            f"{v['unsupported_rate_before_verify']:.2f}->{v['unsupported_rate_after_verify']:.2f}",
            f"{v['avg_latency_ms']:.2f}",
        ])
    pdf.table(
        ["Var", "Recall@5", "nDCG@10", "MRR", "Recall@5 (AI / Data / Web)", "Unsupp Pre->Post", "Lat (ms)"],
        rows_b,
        [14, 20, 20, 18, 52, 34, 24],
    )
    pdf.image(str(c1), w=168)
    pdf.ln(1)
    dlt = abl["deltas"]
    pdf.body(
        f"Ablation & Negative Results (evals/results/ablation.json): Hybrid RRF (v2) beats Dense-only (v0) by "
        f"+{dlt['hybrid_vs_dense_recall_delta']:.4f} Recall@5, and Skill/Type Reranking (v3 vs v2) adds "
        f"+{dlt['rerank_vs_hybrid_ndcg_delta']:.4f} nDCG@10. Negative results: (1) v4 Outcome-Aware reranking dropped "
        f"nDCG@10 by {dlt['outcome_vs_rerank_ndcg_delta']:.4f} (0.8697 vs 1.0000) because boosting 'won' items displaced "
        f"higher-relevance exact skill matches; (2) v5 Multi-Vector (0.0000) and v6 Contextual (0.0218) failed because "
        f"sub-field/header-only vectors missed main body tokens. Claim verification (rag/verify.py) reduced unsupported "
        f"claims from 0.5000 to 0.0000. Shipped choice: v8 (Corrective Self-RAG, Recall@5=1.0000, nDCG@10=1.0000, 5.63 ms)."
    )

    # 5. R&D Question C
    pdf.h1("5. R&D Question C: Single-Agent vs. Multi-Agent LangGraph")
    pdf.body(
        "We compared a single-pass baseline against our parallel Send + Critic + Compliance LangGraph bid_graph on "
        "n = 90 dev jobs (evals/runners/rd_c_agent_comparison.py -> evals/results/rd_c_agent_comparison.json)."
    )
    sa, ma = rdc["single_agent_baseline"], rdc["multi_agent_langgraph"]
    pdf.table(
        ["Architecture", "Decision Accuracy", "Scam Recall", "Unsupported Claim Rate", "Avg Latency (ms)"],
        [
            ["Single-Agent Baseline", f"{sa['decision_accuracy']:.4f}", f"{sa['scam_recall']:.4f}", f"{sa['avg_unsupported_claim_rate']:.4f}", f"{sa['avg_latency_ms']:.2f}"],
            ["Multi-Agent LangGraph (bid_graph)", f"{ma['decision_accuracy']:.4f}", f"{ma['scam_recall']:.4f}", f"{ma['avg_unsupported_claim_rate']:.4f}", f"{ma['avg_latency_ms']:.2f}"],
        ],
        [62, 30, 28, 36, 26],
    )
    pdf.image(str(c2), w=155)
    pdf.ln(1)
    pdf.body(
        "A prebuilt single-loop supervisor lacks deterministic parallel fan-out and typed state reducers; our explicit "
        "StateGraph improved decision accuracy by +36.67 pp (0.6222 -> 0.9889), scam recall from 0.0000 to 1.0000, "
        "and eliminated unsupported claims (0.1667 -> 0.0000) at 593.73 ms/job."
    )

    # 6. The Change Request
    pdf.h1("6. Change Request Readiness (Policy-Driven Config)")
    pdf.body(
        "To absorb late marketplace policy changes (Connects reserve floor, max Connects per bid, banned phrases, fit "
        "thresholds, active RAG variant) without altering graph topology, rules are externalized in agent/config.yaml "
        "(policy, thresholds, budgets) and data/policy_pack/marketplace_policy.md. Updating a rule requires a 1-line "
        "YAML/settings edit (<2 minutes, zero node-wiring changes; e.g., commit 724c5fa wired live RAG variant switching "
        "via PUT /api/settings -> rag.retriever.set_variant())."
    )

    # 7. Signature Extension
    pdf.h1("7. Signature Extension (X2: Proposal Strategy Experiment)")
    pdf.body(
        "We implemented X2 (evals/runners/proposal_experiments.py -> evals/results/proposal_experiments.json) comparing "
        "three proposal styles across 30 dev-set bid jobs, plus end-to-end GigSim outcome simulation (gigsim_outcomes.json):"
    )
    strats = x2["strategies"]
    pdf.table(
        ["Strategy", "Avg Word Count", "Avg Citations / Proposal", "Unsupported Rate (Post-Verify)"],
        [
            [s, str(m["avg_word_count"]), str(m["avg_citations_per_proposal"]), f"{m['unsupported_rate_after_verify']:.4f}"]
            for s, m in strats.items()
        ],
        [52, 40, 46, 44],
    )
    pdf.body(
        f"End-to-end GigSim outcomes (evals/results/gigsim_outcomes.json): total_submitted = {gs['total_submitted']}, "
        f"reply_rate = {gs['reply_rate']}, interview_rate = {gs['interview_rate']}, hire_rate = {gs['hire_rate']}, "
        f"total_connects_spent = {gs['total_connects_spent']}, safety_incidents = {gs['safety_incidents']}."
    )

    # 8. Failure Analysis
    pdf.h1("8. Failure Analysis Taxonomy (10 Observed Dev/System Failures)")
    pdf.table(
        ["#", "Category", "Observed Failure / Case", "Fix Applied & Outcome"],
        [
            ["1", "Missed Evidence", "v0 dense missed 43% of gold IDs (Recall@5=0.5685)", "Switched to v8/v3 Hybrid+Rerank -> Recall@5=1.0000"],
            ["2", "Missed Evidence", "v5/v6 sub-field indexing scored 0.0000 / 0.0218", "Retained full-text + skill graph; documented negative result"],
            ["3", "Wrong Skip", "Single-agent misclassified 37.8% of dev jobs (Acc=0.6222)", "Parallel Send + FitMatcher -> Acc=0.9833 (decision_eval)"],
            ["4", "Wrong Skip", "gigsim_outcomes data_analyst had 0 submissions in batch", "Verified Connects/fit threshold interaction; logged honestly"],
            ["5", "Mispriced", "Early decision_eval[::5] sampled only skips -> 0.0 band acc", "Stratified bid/skip/scam sampling -> price_in_band=1.0"],
            ["6", "Unsupported Claim", "Raw drafts had 0.5000 unsupported rate (mock/unverified)", "prune_unsupported_claims() -> 0.0000 post-verify"],
            ["7", "Generic Opening", "short_punchy averaged only 1.0 citation (11.9 words)", "evidence_bulleted raised citations to 3.0/proposal"],
            ["8", "Compliance Miss", "Human edit at interrupt() could inject WhatsApp/email", "Re-ran compliance_node post-edit -> blocked_by_compliance"],
            ["9", "Injection", "dev_set prompt-injection traps bypassed naive baseline", "delimit_untrusted + detect_injection -> 1.0 defense rate"],
            ["10", "Tool / API Error", "UI /messages sent 'message' instead of 'client_message' (422)", "Aligned client.ts & test_api_endpoints.py (commit 724c5fa)"],
        ],
        [8, 30, 74, 70],
    )

    # 9. Safety & Platform Respect
    pdf.h1("9. Safety and Platform Respect")
    pdf.body(
        "GigBid must never: (a) spend Connects or send proposals/messages without HITL interrupt() approval; (b) follow "
        "instructions inside untrusted job posts or client messages; (c) leak unmasked PII into logs; or (d) scrape or "
        "auto-submit on live Upwork. Enforcement: <untrusted_job_post> delimiters and regex/LLM injection checks "
        "(agent/safety.py), mask_pii() redaction, compliance_node post-edit re-checks, UpworkLiveAdapter draft-only guard, "
        "per-user rate limiting, and Fernet-encrypted OAuth tokens. What can still get through: novel zero-day paraphrased "
        "social-engineering requests that avoid known contact/injection patterns, which are mitigated by the mandatory human "
        "review gate before any external send."
    )

    # 10. Hidden Test Results vs Declared Budgets
    pdf.h1("10. Declared Budgets vs. Measured Results (and Hidden Test Readiness)")
    pdf.body(
        f"On the 120-job stratified dev benchmark (evals/results/decision_eval.json): decision_accuracy = {dec['decision_accuracy']}, "
        f"scam_precision = {dec['scam_precision']}, scam_recall = {dec['scam_recall']}, scam_f1 = {dec['scam_f1']}, "
        f"injection_defense_rate = {dec['injection_defense_rate']}, price_in_band_accuracy = {dec['price_in_band_accuracy']}, "
        f"proposal_groundedness_rate = {dec['proposal_groundedness_rate']}. Measured orchestration latency is 0.59s/job "
        f"(well under the 15.0s p95 budget) at $0.00/job on the open profile (under the $0.05/job cap). "
        f"Note on hidden test set: Per assignment rules, the instructor's unseen hidden test set is executed against "
        f"the live deployment (https://gigbid-copilot-wnto.onrender.com) after the deadline and is therefore not included here."
    )

    out_pdf = ROOT / "docs" / "GigBid_RD_Report.pdf"
    pdf.output(str(out_pdf))
    return out_pdf


if __name__ == "__main__":
    p = build_pdf()
    print(f"Generated: {p}")
