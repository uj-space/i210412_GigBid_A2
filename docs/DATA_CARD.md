# GigBid Data Card

This card documents every dataset used by GigBid: selection rationale, preprocessing, attribution, licensing, limitations, and the strict separation between **real-world (Kaggle) data** and **synthetic data**.

> **Provenance rule.** Every record carries `is_real_data` (bool) and `provenance` (string). Real Kaggle records use `provenance: "kaggle_real"`; synthetic records use a `synthetic_*` provenance tag. Unit test `tests/unit/test_data.py::test_synthetic_data_is_clearly_labelled` enforces this in CI.

---

## 1. Reproducing the data

```bash
export KAGGLE_API_TOKEN=...                        # never committed; or ~/.kaggle/access_token
python -m data.ingest.download_kaggle              # -> data/raw/            (git-ignored, ~700 MB)
python -m data.ingest.process_kaggle               # -> data/processed/      (git-ignored)
                                                   # -> data/market/         (small aggregates, committed)
python -m data.ingest.generate_personas_and_devset # -> data/personas/, data/synthetic/, evals/datasets/
```
`make seed` runs the last two steps. All generators are deterministic (`random.Random(42)`).

---

## 2. Real-world datasets (Kaggle)

| # | Kaggle dataset | Raw file(s) | GigBid role | Used |
|---|---|---|---|---|
| 1 | `asaniczka/upwork-job-postings-dataset-2024-50k-records` | `upwork-jobs.csv` | Job titles, full descriptions, hourly/fixed budgets, country | 1,500 jobs |
| 2 | `asaniczka/all-jobs-on-upwork-200k-plus` | `all_upwork_jobs_2024-*.csv` (3 splits) | Temporal 2024 job stream; budget distributions | 2,100 jobs |
| 3 | `ahmedmyalo/upwork-freelance-jobs-60k` | `Final_Upwork_Dataset.csv` | Category, search keyword and experience-level metadata | 1,000 jobs |
| 4 | `asaniczka/freelance-contracts-dataset-1-3-million-entries` | `contracts.csv` | Realised hourly rates and contract totals: market prior for the **Pricing Strategist** | 12,332 valid rates / 22,471 valid totals (first 25k rows) |
| 5 | `sarveshchhetri/freelancer-success-earnings-and-churn-prediction` | `freelancer_gig_success_dataset.csv` | Freelancer hourly-rate benchmarks by primary skill | 3,554 records |
| 6 | `adityammantri/trial-1` | `processed_labeled_dataset_without_encoding.xlsx` | Labelled fraudulent vs legitimate postings: external scam-detection benchmark | 600 (300 / 300 balanced) |

**Total real jobs in the GigSim job pool: 4,600** (`data/processed/all_jobs.json`). This exceeds the brief's "about 1,500 historical jobs" for pricing statistics.

### 2.1 Measured market prior (`data/market/market_pricing_stats.json`)

| Segment | n | p25 | median | p75 (USD/h) |
|---|---|---|---|---|
| All contracts | 12,332 | 14.0 | 25.0 | 45.0 |
| AI / ML | 1,324 | 15.0 | 30.0 | 50.0 |
| Web development | 1,860 | 15.0 | 25.0 | 40.0 |
| Data analytics | 309 | 18.0 | 33.3 | 60.0 |

### 2.2 Preprocessing
1. **Encoding & text.** Files are read as `utf-8-sig` (strips the BOM in `Final_Upwork_Dataset.csv`) with whitespace collapsed. Descriptions are truncated to 2,000 characters.
2. **Identifiers.** Deterministic SHA-256 IDs (`kgl-*` jobs, `cli-*` clients, `frd-*` fraud records), so re-runs are idempotent.
3. **Budget harmonisation.** Fixed `budget` is used when present. Otherwise the hourly range (`hourly_low`, `hourly_high`) is converted to a 20-hour engagement band.
4. **Connects cost.** The Kaggle data has no Connects field, so cost is derived from the budget band: <\$500 → 6, <\$2,000 → 8, otherwise 12. This is a documented assumption.
5. **Outlier filtering (contracts).** `hourly_rate` ∈ [3, 300] and `total_paid` ∈ [10, 100,000]. Percentiles are computed per domain bucket, using job-title keywords.
6. **Skill extraction.** Explicit `Search_Keyword` tags are combined with word-boundary regex matching against a 30-skill lexicon.
7. **Weak risk labels.** Regex flags (`unpaid_work`, `off_platform_contact`, `suspicious_claim`) are added as `warning_signals`. These are heuristics, not ground truth.

### 2.3 Attribution & licensing
All six datasets are publicly hosted on Kaggle and used here for **non-commercial academic research** (AI-4016 coursework), under each dataset's Kaggle licence and the Kaggle Terms of Use. Credit goes to the dataset authors: *asaniczka*, *ahmedmyalo*, *sarveshchhetri* and *adityammantri*. Raw files are **not redistributed** in this repository (`data/raw/` is git-ignored). Only derived aggregate statistics (`data/market/`) are committed. Check each dataset page for its exact licence before reusing it outside this context.

### 2.4 Limitations
- **No private signals.** The Upwork snapshots lack client–freelancer messages, actual Connects spend, proposal outcomes and freelancer portfolios. These gaps motivate the synthetic corpora in §3.
- **Rate skew.** `contracts.csv` is dominated by low-rate hourly work (median \$25/h), which is likely below the target personas' rates. Pricing therefore applies the freelancer's floor on top of the market prior.
- **Domain shift.** `adityammantri/trial-1` is an EMSCAD-style general employment-fraud corpus, not Upwork-specific. It is used only as an external robustness benchmark, never for training.
- **Temporal coverage.** Jobs span Feb–Jul 2024. Market rates may have drifted since then.
- **Weak labels.** Regex `warning_signals` on real jobs are noisy. Gold scam and injection labels exist only in the synthetic dev set.

---

## 3. Synthetic data (clearly distinguished)

Generated by `data/ingest/generate_personas_and_devset.py`. All names, companies and client IDs are fictitious.

| Asset | Path | Contents | `provenance` |
|---|---|---|---|
| AI/ML Engineer persona | `data/personas/ai_ml_engineer.json` | 1 CV, 18 case studies, 6 repo README+code items, 6 reviews, 150 past proposals (25 won / 45 replied / 80 ignored) = 181 items | `synthetic_persona_corpus` |
| Full-Stack Web Dev persona | `data/personas/fullstack_web_dev.json` | same structure, 181 items | `synthetic_persona_corpus` |
| Data Analyst persona | `data/personas/data_analyst.json` | same structure, 181 items | `synthetic_persona_corpus` |
| Client histories | `data/synthetic/clients.json` | 60 clients with public history plus **hidden preferences** (must-have skills, budget ceiling, dislike of generic openings) for the GigSim client simulator | `synthetic_client_history` |
| Client conversations | `data/synthetic/conversations.json` | 48 messages with gold intent (question, interview, negotiation, scam signal, injection attempt) | `synthetic_conversation` |
| Dev evaluation set | `evals/datasets/dev_set.json` | 600 jobs (200 per persona: 112 good-fit, 28 skill-mismatch, 30 scam, 30 planted prompt-injection). Gold `gold_decision`, `gold_scam`, `gold_injection`, `gold_evidence_ids`, `fair_price_band` | `synthetic_dev_eval_with_kaggle_context` |

### 3.1 Design choices for realism (and to defeat naive RAG)
- **Each project is described three ways** (architecture, implementation, outcomes), so naive top-k returns near-duplicates.
- **Skills are implied in repo code** rather than always named in prose. This tests multi-vector (V5) retrieval.
- **Past proposals carry outcome labels.** Winning ones are specific and evidence-led; ignored ones are generic. This tests outcome-aware ranking (V4).
- **Dev jobs embed real Kaggle description text** as context, mixing synthetic structure with real-world noise.
- **Injection jobs** contain three planted attack styles: a system override, an HTML comment and a policy bypass.

### 3.2 Limitations of synthetic data
Synthetic portfolios are cleaner and more regular than real ones. Evaluation scores on them are an **upper bound** and should not be read as real-world performance. Gold labels come from the generator, not from human annotators. The LLM-judge calibration in Part B uses 30 human-labelled items to mitigate this.

---

## 4. Ethics & privacy
- No scraping, no browser automation, no live Upwork user data. Live-mode data is never committed.
- Real Kaggle records contain no personal contact data after preprocessing. Logs pass through `agent/safety.py::mask_pii`.
- The hidden test set never enters the repository.
