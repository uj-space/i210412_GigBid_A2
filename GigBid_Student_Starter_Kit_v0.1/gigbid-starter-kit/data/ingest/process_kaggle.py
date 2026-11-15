"""Process Kaggle datasets into GigBid format.

Reads raw Kaggle downloads and normalizes them into GigBid's internal
job and client data structures. Synthetic data is clearly distinguished
from real Kaggle data.
"""
from __future__ import annotations

import json
import csv
import hashlib
from pathlib import Path
from typing import Any
import re

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

SYNTHETIC_PREFIX = "SYNTHETIC_"


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _clean_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip()


def _clean_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip()


def _parse_budget(text: Any) -> dict:
    result = {"min": None, "max": None, "currency": "USD"}
    if text is None:
        return result
    text = str(text)
    numbers = re.findall(r"[\d,]+\.?\d*", text.replace(",", ""))
    nums = [float(n) for n in numbers if n]
    if len(nums) >= 2:
        result["min"] = min(nums)
        result["max"] = max(nums)
    elif len(nums) == 1:
        result["min"] = nums[0]
        result["max"] = nums[0]
    return result


MAX_ROWS_PER_FILE = 1000


def process_upwork_jobs_2024(raw_dir: Path) -> list[dict]:
    jobs = []
    csv_files = list(raw_dir.glob("*.csv")) + list(raw_dir.glob("*.json"))
    for csv_file in csv_files:
        try:
            if csv_file.suffix == ".csv":
                with open(csv_file, encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i >= MAX_ROWS_PER_FILE:
                            break
                        job = _normalize_job(row, source="kaggle_upwork_2024")
                        if job:
                            jobs.append(job)
            elif csv_file.suffix == ".json":
                with open(csv_file, encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for row in data:
                            job = _normalize_job(row, source="kaggle_upwork_2024")
                            if job:
                                jobs.append(job)
                    elif isinstance(data, dict):
                        job = _normalize_job(data, source="kaggle_upwork_2024")
                        if job:
                            jobs.append(job)
        except Exception as e:
            print(f"[WARN]  Error processing {csv_file}: {e}")
    return jobs


def _normalize_job(row: dict, source: str = "unknown") -> dict | None:
    job_id = (
        row.get("job_id")
        or row.get("Job ID")
        or row.get("id")
        or row.get("Job ID")
        or _file_hash(str(row))[:12]
    )
    title = _clean_text(row.get("title") or row.get("Title") or row.get("job_title"))
    description = _clean_text(
        row.get("description")
        or row.get("Description")
        or row.get("job_description")
        or row.get("details")
    )
    skills_raw = _clean_text(
        row.get("required_skills")
        or row.get("Required Skills")
        or row.get("skills")
        or row.get("Skills")
    )
    skills = [s.strip() for s in skills_raw.split(",") if s.strip()] if skills_raw else []
    budget_raw = _clean_text(
        row.get("budget") or row.get("Budget") or row.get("price") or row.get("Price")
    )
    budget = _parse_budget(budget_raw)
    connects_raw = _clean_text(
        row.get("connects_cost") or row.get("Connects") or row.get("connects")
    )
    try:
        connects_cost = int(float(connects_raw)) if connects_raw else 5
    except ValueError:
        connects_cost = 5
    client_id = _clean_text(
        row.get("client_id") or row.get("Client ID") or row.get("client")
    ) or "unknown-client"
    warning_raw = _clean_text(
        row.get("warning_signals") or row.get("Warning") or row.get("flags")
    )
    warning_signals = [s.strip() for s in warning_raw.split(",") if s.strip()] if warning_raw else []
    
    desc_lower = description.lower()
    if not warning_signals:
        if any(w in desc_lower for w in ["unpaid", "free trial", "test project"]):
            warning_signals.append("unpaid_work")
        if any(w in desc_lower for w in ["telegram", "whatsapp", "off-platform", "contact directly"]):
            warning_signals.append("off_platform_contact")
    
    return {
        "job_id": f"{SYNTHETIC_PREFIX}{job_id}" if source.startswith("kaggle") else str(job_id),
        "title": title or "Untitled Job",
        "description": description or "",
        "required_skills": skills,
        "budget": budget,
        "connects_cost": connects_cost,
        "client_id": client_id or "unknown",
        "warning_signals": warning_signals,
        "posted_at": _clean_text(row.get("posted_at") or row.get("Posted") or row.get("date")),
        "source": source,
        "is_real_data": source.startswith("kaggle"),
        "raw": row,
    }


def process_all_kaggle() -> dict:
    all_jobs = []
    stats = {"total": 0, "real": 0, "synthetic": 0, "by_source": {}}

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Process Kaggle subdirectories (datasets downloaded as folders)
    kaggle_dirs = [d for d in RAW_DIR.iterdir() if d.is_dir()]
    for kaggle_dir in kaggle_dirs:
        dir_name = kaggle_dir.name
        print("[PROCESS] " + dir_name)
        jobs = process_upwork_jobs_2024(kaggle_dir)
        stats["by_source"][dir_name] = len(jobs)
        stats["real"] += len(jobs)
        stats["total"] += len(jobs)
        all_jobs.extend(jobs)
        print("   [OK] " + str(len(jobs)) + " jobs extracted from " + dir_name)

    # Process root-level Kaggle CSV/JSON files directly
    root_csv_files = list(RAW_DIR.glob("*.csv")) + list(RAW_DIR.glob("*.json"))
    if root_csv_files:
        print("[PROCESS] root-level Kaggle files")
        jobs = process_upwork_jobs_2024(RAW_DIR)
        stats["by_source"]["root_level_files"] = len(jobs)
        stats["real"] += len(jobs)
        stats["total"] += len(jobs)
        all_jobs.extend(jobs)
        print("   [OK] " + str(len(jobs)) + " jobs extracted from root-level files")

    if not kaggle_dirs and not root_csv_files:
        print("[WARN] No Kaggle datasets found in " + str(RAW_DIR))
        print("   [INFO] Generating synthetic jobs only")

    
    synthetic_jobs = _generate_synthetic_jobs()
    stats["synthetic"] = len(synthetic_jobs)
    stats["total"] += len(synthetic_jobs)
    all_jobs.extend(synthetic_jobs)
    print("   [OK] " + str(len(synthetic_jobs)) + " synthetic jobs generated")
    
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / "all_jobs.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)
    
    stats_file = PROCESSED_DIR / "stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    
    print("\n" + "=" * 60)
    print("[OK] Processed " + str(stats['total']) + " total jobs")
    print("   [REAL] " + str(stats['real']) + " (Kaggle)")
    print("   [SYNTHETIC] " + str(stats['synthetic']))
    print("   [OUT] " + str(output_file))
    print("   [STATS] " + str(stats_file))
    
    return {"jobs": all_jobs, "stats": stats}


def _generate_synthetic_jobs() -> list[dict]:
    synthetic = [
        {
            "job_id": f"{SYNTHETIC_PREFIX}synth-001",
            "title": "Build ML churn prediction model",
            "description": "Need ML engineer for customer churn prediction using Python/pandas/scikit-learn",
            "required_skills": ["Python", "pandas", "scikit-learn"],
            "budget": {"min": 500, "max": 2000, "currency": "USD"},
            "connects_cost": 6,
            "client_id": "synth-client-1",
            "warning_signals": [],
            "posted_at": "2024-01-15",
            "source": "synthetic",
            "is_real_data": False,
            "raw": {},
        },
        {
            "job_id": f"{SYNTHETIC_PREFIX}synth-002",
            "title": "React dashboard for analytics",
            "description": "Build a modern dashboard with React, TypeScript, and D3.js charts",
            "required_skills": ["React", "TypeScript", "D3.js"],
            "budget": {"min": 800, "max": 3000, "currency": "USD"},
            "connects_cost": 8,
            "client_id": "synth-client-2",
            "warning_signals": [],
            "posted_at": "2024-01-16",
            "source": "synthetic",
            "is_real_data": False,
            "raw": {},
        },
        {
            "job_id": f"{SYNTHETIC_PREFIX}synth-003",
            "title": "API development with FastAPI",
            "description": "Create REST APIs for a SaaS platform",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "budget": {"min": 1000, "max": 4000, "currency": "USD"},
            "connects_cost": 10,
            "client_id": "synth-client-3",
            "warning_signals": [],
            "posted_at": "2024-01-17",
            "source": "synthetic",
            "is_real_data": False,
            "raw": {},
        },
        {
            "job_id": f"{SYNTHETIC_PREFIX}synth-004",
            "title": "SCAM - Unpaid work needed",
            "description": "Unpaid test project first. Need work done for free trial.",
            "required_skills": ["Python", "React"],
            "budget": {"min": 0, "max": 0, "currency": "USD"},
            "connects_cost": 4,
            "client_id": "synth-scam-1",
            "warning_signals": ["unpaid_work"],
            "posted_at": "2024-01-18",
            "source": "synthetic",
            "is_real_data": False,
            "raw": {},
        },
    ]
    return synthetic


if __name__ == "__main__":
    result = process_all_kaggle()
    print("\n[OK] Data processing complete!")
    print("   Total jobs: " + str(result['stats']['total']))
    print("   Real (Kaggle): " + str(result['stats']['real']))
    print("   Synthetic: " + str(result['stats']['synthetic']))