"""Unit tests for the data layer: real/synthetic separation, persona corpora and dev set (Step 1)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PERSONAS = ["ai_ml_engineer", "fullstack_web_dev", "data_analyst"]


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


@pytest.mark.parametrize("pid", PERSONAS)
def test_persona_corpus_meets_spec(pid):
    corpus = _load(f"data/personas/{pid}.json")
    types = Counter(it["type"] for it in corpus["items"])
    assert types["cv"] == 1
    assert 15 <= types["case_study"] <= 25  # brief: 15 to 25 case studies
    assert types["repo_code"] >= 1 and types["client_review"] >= 1
    proposals = [it for it in corpus["items"] if it["type"] == "past_proposal"]
    assert len(proposals) == 150  # brief: about 150 past proposals
    assert {p["outcome"] for p in proposals} == {"won", "replied", "ignored"}


@pytest.mark.parametrize("pid", PERSONAS)
def test_every_chunk_has_required_metadata(pid):
    required = {"evidence_id", "persona", "type", "project", "skills", "date", "client_industry", "outcome"}
    for it in _load(f"data/personas/{pid}.json")["items"]:
        assert required <= it.keys(), it.get("evidence_id")


def test_synthetic_data_is_clearly_labelled():
    for pid in PERSONAS:
        assert all(it["is_real_data"] is False for it in _load(f"data/personas/{pid}.json")["items"])
    assert all(c["is_real_data"] is False for c in _load("data/synthetic/clients.json"))
    assert all(m["is_real_data"] is False for m in _load("data/synthetic/conversations.json"))
    assert all(j["provenance"].startswith("synthetic") for j in _load("evals/datasets/dev_set.json"))


def test_dev_set_has_gold_labels_and_balance():
    dev = _load("evals/datasets/dev_set.json")
    assert len(dev) == 600
    per_persona = Counter(j["persona"] for j in dev)
    assert all(per_persona[p] == 200 for p in PERSONAS)
    for j in dev:
        assert j["gold_decision"] in {"bid", "skip"}
        assert isinstance(j["gold_scam"], bool)
        assert len(j["fair_price_band"]) == 2
    assert sum(j["gold_scam"] for j in dev) >= 150  # scams + planted injections
    assert sum(j["gold_injection"] for j in dev) >= 75
    # gold evidence ids must exist in the persona corpus
    ids = {it["evidence_id"] for p in PERSONAS for it in _load(f"data/personas/{p}.json")["items"]}
    assert all(e in ids for j in dev for e in j["gold_evidence_ids"])


def test_client_hidden_preferences_present():
    clients = _load("data/synthetic/clients.json")
    assert len(clients) >= 40
    assert all({"must_have_skills", "budget_ceiling", "dislikes_generic_openings"} <= c["hidden_preferences"].keys() for c in clients)


@pytest.mark.skipif(not (ROOT / "data/processed/all_jobs.json").exists(), reason="raw Kaggle data not present (CI)")
def test_processed_kaggle_jobs_are_real_and_attributed():
    jobs = _load("data/processed/all_jobs.json")
    assert len(jobs) >= 1500  # brief: about 1,500 historical jobs for pricing statistics
    assert all(j["is_real_data"] is True for j in jobs)
    allowed = {
        "asaniczka/upwork-job-postings-dataset-2024-50k-records",
        "asaniczka/all-jobs-on-upwork-200k-plus",
        "ahmedmyalo/upwork-freelance-jobs-60k",
    }
    assert {j["source"] for j in jobs} <= allowed
    stats = _load("data/processed/market_pricing_stats.json")
    assert stats["hourly_rate"]["p25"] <= stats["hourly_rate"]["median"] <= stats["hourly_rate"]["p75"]
