"""Process all 6 Kaggle datasets into normalized GigBid processed assets.

Clearly distinguishes real-world Kaggle records (``is_real_data: True``)
from synthetic records (``is_real_data: False``).

Datasets processed from ``data/raw/``:
1. asaniczka/upwork-job-postings-dataset-2024-50k-records (upwork-jobs.csv)
2. asaniczka/all-jobs-on-upwork-200k-plus (all_upwork_jobs_2024-*.csv)
3. ahmedmyalo/upwork-freelance-jobs-60k (Final_Upwork_Dataset.csv)
4. asaniczka/freelance-contracts-dataset-1-3-million-entries (contracts.csv)
5. sarveshchhetri/freelancer-success-earnings-and-churn-prediction (freelancer_gig_success_dataset.csv)
6. adityammantri/trial-1 (processed_labeled_dataset_without_encoding.xlsx)
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

MAX_JOBS_PER_FILE = 1000
MAX_CONTRACT_ROWS = 25000
MAX_FRAUD_ROWS = 600

SKILL_KEYWORDS = [
    "python", "fastapi", "django", "flask", "react", "typescript", "javascript",
    "next.js", "node.js", "postgresql", "sql", "pandas", "scikit-learn", "pytorch",
    "tensorflow", "langgraph", "langchain", "rag", "llm", "docker", "aws",
    "tableau", "power bi", "dbt", "airflow", "spark", "excel", "d3.js", "tailwind",
]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _hash_id(prefix: str, text: str) -> str:
    return f"{prefix}-{hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()[:10]}"


def _to_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    s = re.sub(r"[^\d.]", "", str(val))
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _extract_skills(text: str, explicit: str = "") -> list[str]:
    found: list[str] = []
    if explicit:
        for part in re.split(r"[,;|/]", explicit):
            p = part.strip()
            if p and p not in found:
                found.append(p)
    lower = text.lower()
    for kw in SKILL_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", lower) and kw not in [f.lower() for f in found]:
            found.append(kw)
    return found[:10]


def _detect_warnings(text: str) -> list[str]:
    lower = text.lower()
    warnings: list[str] = []
    if any(w in lower for w in ["unpaid", "free trial", "free test", "no pay", "volunteer"]):
        warnings.append("unpaid_work")
    if any(w in lower for w in ["telegram", "whatsapp", "off-platform", "pay outside", "skype me"]):
        warnings.append("off_platform_contact")
    if any(w in lower for w in ["100% guarantee", "guaranteed roi", "ignore previous"]):
        warnings.append("suspicious_claim")
    return warnings


def _process_upwork_jobs_csv(path: Path, source_name: str, limit: int = MAX_JOBS_PER_FILE) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    if not path.exists():
        return jobs
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            title = _clean_text(row.get("title") or row.get("Job Title"))
            desc = _clean_text(row.get("description") or row.get("Description") or title)
            if not title and not desc:
                continue
            b_fixed = _to_float(row.get("budget"))
            h_low = _to_float(row.get("hourly_low"))
            h_high = _to_float(row.get("hourly_high"))
            is_hourly = str(row.get("is_hourly", "")).lower() in {"true", "1", "yes"}
            if is_hourly and (h_low or h_high):
                b_min = (h_low or h_high or 25.0) * 20
                b_max = (h_high or h_low or 50.0) * 20
            else:
                b_min = b_fixed
                b_max = b_fixed
            skills = _extract_skills(f"{title} {desc}", _clean_text(row.get("Search_Keyword")))
            job_id = _hash_id("kgl", f"{source_name}:{idx}:{title}")
            jobs.append({
                "job_id": job_id,
                "title": title or "Untitled Upwork Job",
                "description": desc[:2000],
                "required_skills": skills,
                "budget": {"min": b_min, "max": b_max, "currency": "USD"},
                "budget_min": b_min,
                "budget_max": b_max,
                "currency": "USD",
                "is_hourly": is_hourly,
                "country": _clean_text(row.get("country") or row.get("Posted_from") or "Unknown"),
                "category": _clean_text(row.get("Category_1") or row.get("Search_Keyword") or "General"),
                "connects_cost": 6 if (b_max or 0) < 500 else (8 if (b_max or 0) < 2000 else 12),
                "client_id": _hash_id("cli", f"{source_name}:{row.get('country', 'na')}:{idx % 200}"),
                "warning_signals": _detect_warnings(f"{title} {desc}"),
                "posted_at": _clean_text(row.get("published_date") or "2024-05-01"),
                "source": source_name,
                "is_real_data": True,
                "provenance": "kaggle_real",
            })
    return jobs


def _process_contracts(path: Path, limit: int = MAX_CONTRACT_ROWS) -> dict[str, Any]:
    rates: list[float] = []
    totals: list[float] = []
    by_bucket: dict[str, list[float]] = {"ai_ml": [], "web_dev": [], "data_analytics": [], "other": []}
    if not path.exists():
        return {"count": 0, "hourly_rate": {}, "total_paid": {}, "by_category": {}}
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            rate = _to_float(row.get("hourly_rate"))
            paid = _to_float(row.get("total_paid"))
            title = _clean_text(row.get("job_title")).lower()
            if rate and 3.0 <= rate <= 300.0:
                rates.append(rate)
                if any(k in title for k in ["machine learning", "ai", "nlp", "data scien", "llm", "python"]):
                    by_bucket["ai_ml"].append(rate)
                elif any(k in title for k in ["react", "web", "full stack", "frontend", "backend", "wordpress"]):
                    by_bucket["web_dev"].append(rate)
                elif any(k in title for k in ["data analy", "tableau", "power bi", "sql", "excel"]):
                    by_bucket["data_analytics"].append(rate)
                else:
                    by_bucket["other"].append(rate)
            if paid and 10.0 <= paid <= 100000.0:
                totals.append(paid)

    def _pcts(vals: list[float]) -> dict[str, float]:
        if not vals:
            return {"count": 0, "p25": 25.0, "median": 45.0, "p75": 75.0}
        s = sorted(vals)
        n = len(s)
        return {
            "count": n,
            "p25": round(s[int(0.25 * (n - 1))], 2),
            "median": round(statistics.median(s), 2),
            "p75": round(s[int(0.75 * (n - 1))], 2),
        }

    return {
        "source": "asaniczka/freelance-contracts-dataset-1-3-million-entries",
        "is_real_data": True,
        "rows_sampled": len(rates),
        "hourly_rate": _pcts(rates),
        "total_paid": _pcts(totals),
        "by_category": {k: _pcts(v) for k, v in by_bucket.items()},
    }


def _process_freelancer_success(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"count": 0, "by_primary_skill": {}}
    rates_by_skill: dict[str, list[float]] = {}
    all_rates: list[float] = []
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            skill = _clean_text(row.get("primary_skill") or "General")
            rate = _to_float(row.get("hourly_rate_usd"))
            if rate and 5.0 <= rate <= 250.0:
                all_rates.append(rate)
                rates_by_skill.setdefault(skill, []).append(rate)
    return {
        "source": "sarveshchhetri/freelancer-success-earnings-and-churn-prediction",
        "is_real_data": True,
        "count": len(all_rates),
        "median_hourly_usd": round(statistics.median(all_rates), 2) if all_rates else 40.0,
        "by_primary_skill": {
            k: {"count": len(v), "median_rate": round(statistics.median(v), 2)}
            for k, v in sorted(rates_by_skill.items())
        },
    }


def _process_fraud_dataset(path: Path, limit: int = MAX_FRAUD_ROWS) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(h) if h is not None else "" for h in next(rows_iter, ())]
        fraud_pos = 0
        non_fraud = 0
        for idx, values in enumerate(rows_iter):
            row = dict(zip(headers, values))
            is_fraud = str(row.get("fraudulent", "0")).strip() in {"1", "True", "true", "t"}
            if is_fraud and fraud_pos >= limit // 2:
                continue
            if not is_fraud and non_fraud >= limit // 2:
                continue
            title = _clean_text(row.get("job_title"))
            desc = _clean_text(row.get("job_desc") or row.get("text"))[:1200]
            if not title and not desc:
                continue
            records.append({
                "job_id": _hash_id("frd", f"{idx}:{title}"),
                "title": title or "Job Posting",
                "description": desc,
                "fraudulent": is_fraud,
                "industry": _clean_text(row.get("industry")),
                "source": "adityammantri/trial-1",
                "is_real_data": True,
            })
            if is_fraud:
                fraud_pos += 1
            else:
                non_fraud += 1
            if len(records) >= limit:
                break
        wb.close()
    except Exception as e:
        print(f"[WARN] Could not parse {path.name}: {e}")
    return records


def process_all_kaggle() -> dict[str, Any]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    all_jobs: list[dict[str, Any]] = []
    by_source: dict[str, int] = {}

    job_sources = [
        ("upwork-jobs.csv", "asaniczka/upwork-job-postings-dataset-2024-50k-records", 1500),
        ("all_upwork_jobs_2024-02-07-2024-03-24.csv", "asaniczka/all-jobs-on-upwork-200k-plus", 700),
        ("all_upwork_jobs_2024-03-24-2024-05-21.csv", "asaniczka/all-jobs-on-upwork-200k-plus", 700),
        ("all_upwork_jobs_2024-05-21-2024-07-25.csv", "asaniczka/all-jobs-on-upwork-200k-plus", 700),
        ("Final_Upwork_Dataset.csv", "ahmedmyalo/upwork-freelance-jobs-60k", 1000),
    ]
    for fname, src, lim in job_sources:
        extracted = _process_upwork_jobs_csv(RAW_DIR / fname, src, limit=lim)
        all_jobs.extend(extracted)
        by_source[src] = by_source.get(src, 0) + len(extracted)

    pricing_stats = _process_contracts(RAW_DIR / "contracts.csv")
    freelancer_stats = _process_freelancer_success(RAW_DIR / "freelancer_gig_success_dataset.csv")
    fraud_records = _process_fraud_dataset(RAW_DIR / "processed_labeled_dataset_without_encoding.xlsx")

    (PROCESSED_DIR / "all_jobs.json").write_text(
        json.dumps(all_jobs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (PROCESSED_DIR / "market_pricing_stats.json").write_text(
        json.dumps(pricing_stats, indent=2), encoding="utf-8"
    )
    (PROCESSED_DIR / "freelancer_benchmarks.json").write_text(
        json.dumps(freelancer_stats, indent=2), encoding="utf-8"
    )
    (PROCESSED_DIR / "fraud_benchmark.json").write_text(
        json.dumps(fraud_records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Small derived aggregates are committed (data/market/) so CI and the deployed app can price
    # without the multi-GB raw files; bulky row-level outputs stay in git-ignored data/processed/.
    market_dir = ROOT / "data" / "market"
    market_dir.mkdir(parents=True, exist_ok=True)
    (market_dir / "market_pricing_stats.json").write_text(json.dumps(pricing_stats, indent=2), encoding="utf-8")
    (market_dir / "freelancer_benchmarks.json").write_text(json.dumps(freelancer_stats, indent=2), encoding="utf-8")

    stats = {
        "total_jobs": len(all_jobs),
        "real_jobs": len(all_jobs),
        "synthetic_jobs": 0,
        "by_source": by_source,
        "contracts_sampled": pricing_stats.get("rows_sampled", 0),
        "freelancer_records": freelancer_stats.get("count", 0),
        "fraud_benchmark_records": len(fraud_records),
    }
    (PROCESSED_DIR / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


if __name__ == "__main__":
    out = process_all_kaggle()
    print(json.dumps(out, indent=2))
