"""Hybrid RAG index: dense vectors, BM25 lexical index, multi-vector, and skill graph."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from rag.ingest.ingest import load_portfolio_items

_INDEX_CACHE: dict[str, "HybridCorpusIndex"] = {}


def invalidate_index() -> None:
    _INDEX_CACHE.clear()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_+#.-]+", (text or "").lower())


class HybridCorpusIndex:
    """In-memory hybrid index (Dense SVD + BM25 + Multi-Vector + Skill Graph) per persona."""

    def __init__(self, persona: str = "default") -> None:
        self.persona = persona
        self.items = load_portfolio_items(persona=persona)
        self.n = len(self.items)

        raw_texts = [it["text"] for it in self.items] or ["empty"]
        ctx_texts = [
            f"[{it.get('persona')} | {it.get('type')} | {it.get('client_industry')} | "
            f"{', '.join(it.get('skills', []))} | outcome:{it.get('outcome')}] {it['text']}"
            for it in self.items
        ] or ["empty"]

        # Dense index (TF-IDF -> SVD L2-normalized semantic space)
        self.vectorizer = TfidfVectorizer(max_features=4096, ngram_range=(1, 2), sublinear_tf=True)
        tfidf = self.vectorizer.fit_transform(raw_texts)
        n_comp = max(2, min(64, tfidf.shape[0] - 1, tfidf.shape[1] - 1)) if tfidf.shape[0] > 2 and tfidf.shape[1] > 2 else 0
        self.svd = TruncatedSVD(n_components=n_comp, random_state=42) if n_comp >= 2 else None
        if self.svd is not None:
            dense = self.svd.fit_transform(tfidf)
            norms = np.linalg.norm(dense, axis=1, keepdims=True) + 1e-9
            self.dense_vecs = dense / norms
        else:
            self.dense_vecs = tfidf.toarray()

        # Contextual dense index
        self.ctx_vectorizer = TfidfVectorizer(max_features=4096, ngram_range=(1, 2), sublinear_tf=True)
        self.ctx_tfidf = self.ctx_vectorizer.fit_transform(ctx_texts)

        # Multi-vector sub-texts (summary, readme, code)
        self.mv_vectorizer = TfidfVectorizer(max_features=4096, ngram_range=(1, 2))
        mv_docs = [
            f"{it.get('summary', '')} {it.get('readme', '')} {it.get('code_snippet', '')} {' '.join(it.get('skills', []))}"
            for it in self.items
        ] or ["empty"]
        self.mv_matrix = self.mv_vectorizer.fit_transform(mv_docs)

        # BM25 statistics
        self.doc_tokens = [_tokenize(t) for t in raw_texts]
        self.doc_tf = [Counter(toks) for toks in self.doc_tokens]
        self.avg_dl = sum(len(t) for t in self.doc_tokens) / max(len(self.doc_tokens), 1)
        df: Counter[str] = Counter()
        for toks in self.doc_tokens:
            for tok in set(toks):
                df[tok] += 1
        self.idf = {
            tok: math.log(1.0 + (self.n - freq + 0.5) / (freq + 0.5))
            for tok, freq in df.items()
        }

        # Skill & Industry Graph
        self.skill_graph: dict[str, list[int]] = {}
        self.industry_graph: dict[str, list[int]] = {}
        for idx, it in enumerate(self.items):
            for sk in it.get("skills", []):
                self.skill_graph.setdefault(sk.lower(), []).append(idx)
            ind = (it.get("client_industry") or "").lower()
            if ind:
                self.industry_graph.setdefault(ind, []).append(idx)

    def search_dense(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        if not self.items:
            return []
        q_tf = self.vectorizer.transform([query or ""])
        if self.svd is not None:
            q_vec = self.svd.transform(q_tf)
            q_vec = q_vec / (np.linalg.norm(q_vec, axis=1, keepdims=True) + 1e-9)
            scores = (self.dense_vecs @ q_vec.T).ravel()
        else:
            scores = (self.dense_vecs @ q_tf.toarray().T).ravel()
        order = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in order]

    def search_bm25(self, query: str, k: int = 10, k1: float = 1.5, b: float = 0.75) -> list[tuple[int, float]]:
        if not self.items:
            return []
        q_toks = _tokenize(query)
        scores: list[tuple[int, float]] = []
        for idx, tf in enumerate(self.doc_tf):
            dl = len(self.doc_tokens[idx]) or 1
            s = 0.0
            for qt in q_toks:
                if qt in tf:
                    idf = self.idf.get(qt, 0.0)
                    freq = tf[qt]
                    denom = freq + k1 * (1.0 - b + b * dl / max(self.avg_dl, 1.0))
                    s += idf * (freq * (k1 + 1.0)) / max(denom, 1e-9)
            scores.append((idx, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]

    def search_contextual(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        if not self.items:
            return []
        q_vec = self.ctx_vectorizer.transform([query or ""])
        scores = (self.ctx_tfidf @ q_vec.T).toarray().ravel()
        order = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in order]

    def search_multivector(self, query: str, k: int = 10) -> list[tuple[int, float]]:
        if not self.items:
            return []
        q_vec = self.mv_vectorizer.transform([query or ""])
        scores = (self.mv_matrix @ q_vec.T).toarray().ravel()
        order = np.argsort(-scores)[:k]
        return [(int(i), float(scores[i])) for i in order]


def get_index(persona: str = "default") -> HybridCorpusIndex:
    if persona not in _INDEX_CACHE:
        _INDEX_CACHE[persona] = HybridCorpusIndex(persona=persona)
    return _INDEX_CACHE[persona]
