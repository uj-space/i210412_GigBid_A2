"""Download Kaggle datasets for GigBid.

Prerequisites:
1. pip install kaggle
2. Set up kaggle.json at ~/.kaggle/kaggle.json
3. Run: python data/ingest/download_kaggle.py
"""
from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Kaggle datasets to download
KAGGLE_DATASETS = {
    "upwork-job-postings-2024": {
        "kaggle_slug": "asaniczka/upwork-job-postings-dataset-2024-50k-records",
        "description": "Upwork job postings 2024 - 50k records",
        "expected_files": ["*.csv", "*.json"],
    },
    "all-jobs-on-upwork-200k": {
        "kaggle_slug": "asaniczka/all-jobs-on-upwork-200k-plus",
        "description": "All jobs on Upwork - 200k+ records",
        "expected_files": ["*.csv", "*.json"],
    },
    "upwork-freelance-jobs-60k": {
        "kaggle_slug": "ahmedmyalo/upwork-freelance-jobs-60k",
        "description": "Upwork freelance jobs - 60k records",
        "expected_files": ["*.csv", "*.json"],
    },
    "freelance-contracts-1.3m": {
        "kaggle_slug": "asaniczka/freelance-contracts-dataset-1-3-million-entries",
        "description": "Freelance contracts - 1.3 million entries",
        "expected_files": ["*.csv", "*.json"],
    },
    "freelancer-success-prediction": {
        "kaggle_slug": "sarveshchhetri/freelancer-success-earnings-and-churn-prediction",
        "description": "Freelancer success, earnings, and churn prediction",
        "expected_files": ["*.csv"],
    },
    "trial-1": {
        "kaggle_slug": "adityammantri/trial-1",
        "description": "Trial dataset",
        "expected_files": ["*.csv", "*.json"],
    },
}


def check_kaggle_cli() -> bool:
    """Check if Kaggle CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["kaggle", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print("[ERROR] Kaggle CLI not found. Install: pip install kaggle")
            return False
        print(f"[OK] Kaggle CLI: {result.stdout.strip()}")
    except FileNotFoundError:
        print("[ERROR] Kaggle CLI not found. Install: pip install kaggle")
        return False

    # Check for kaggle.json
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if not kaggle_json.exists():
        print(f"[ERROR] Kaggle API token not found at {kaggle_json}")
        print("   Download from: https://www.kaggle.com/account")
        return False
    print(f"[OK] Kaggle API token: {kaggle_json}")
    return True


def download_dataset(slug: str, dest_dir: Path) -> bool:
    """Download a single Kaggle dataset."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["kaggle", "datasets", "download", "-d", slug, "-p", str(dest_dir), "--unzip"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"[ERROR] Failed to download {slug}: {result.stderr}")
            return False
        print(f"[OK] Downloaded: {slug}")
        return True
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Timeout downloading {slug}")
        return False


def main():
    print("=" * 60)
    print("GIGBID - Kaggle Dataset Downloader")
    print("=" * 60)

    if not check_kaggle_cli():
        print("\n[SETUP] Setup instructions:")
        print("   1. pip install kaggle")
        print("   2. Get API token from https://www.kaggle.com/account")
        print("   3. Place kaggle.json at ~/.kaggle/kaggle.json")
        print("   4. Run: python data/ingest/download_kaggle.py")
        return

    print(f"\n[DIR] Data directory: {DATA_DIR}")
    print(f"[DIR] Raw data: {RAW_DIR}")
    print(f"[DIR] Processed data: {PROCESSED_DIR}")

    downloaded = []
    for name, info in KAGGLE_DATASETS.items():
        print(f"\n[DOWNLOAD] Downloading: {info['description']}")
        print(f"   Slug: {info['kaggle_slug']}")
        dest = RAW_DIR / name
        if download_dataset(info["kaggle_slug"], dest):
            downloaded.append(name)

    print(f"\n{'=' * 60}")
    print(f"[OK] Downloaded {len(downloaded)}/{len(KAGGLE_DATASETS)} datasets")
    for name in downloaded:
        print(f"   ✓ {name}")
    print(f"\n[DIR] Raw data location: {RAW_DIR}")
    print(f"[DIR] Next step: Run data/ingest/process_kaggle.py to normalize")


if __name__ == "__main__":
    main()