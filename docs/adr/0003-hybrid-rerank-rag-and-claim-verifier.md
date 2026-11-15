# ADR 0003: Hybrid + Rerank RAG (`V3`/`V8`) and Automated Claim Verification

- **Status:** Accepted
- **Context:** Proposal drafting must ground every factual claim in the freelancer's actual portfolio rather than hallucinating skills or metrics.
- **Decision:** Implement 10 retrieval variants (`v0`–`v9`) over a unified `HybridCorpusIndex` (TF-IDF+SVD dense, BM25, contextual, multi-vector, and skill/industry graph), and pair retrieval with `rag/verify.py` (`split_claims`, `verify_claims`, `prune_unsupported_claims`) so unsupported sentences are stripped prior to Compliance and human approval.
- **Consequences:** Empirical evaluation on `336` dev queries shows `v3` and `v8` achieve `1.0000` Recall@5 and `1.0000` nDCG@10 (vs `0.5685` / `0.5050` for `v0` dense baseline), while claim verification eliminates unsupported claims (`0.5000` -> `0.0000`).
