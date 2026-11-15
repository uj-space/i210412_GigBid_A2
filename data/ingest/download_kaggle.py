"""Download the six Kaggle datasets used by GigBid into data/raw/.

Credentials are NEVER stored in the repository. Provide them via either:
  * environment variable  KAGGLE_API_TOKEN=<token>   (new Kaggle access-token flow), or
  * ~/.kaggle/access_token  /  ~/.kaggle/kaggle.json  (standard Kaggle CLI locations)

Usage:
    python -m data.ingest.download_kaggle
"""
from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

KAGGLE_DATASETS: dict[str, str] = {
    "asaniczka/upwork-job-postings-dataset-2024-50k-records": "Upwork job postings 2024 (50k)",
    "asaniczka/all-jobs-on-upwork-200k-plus": "All jobs on Upwork (200k+)",
    "ahmedmyalo/upwork-freelance-jobs-60k": "Upwork freelance jobs (60k)",
    "asaniczka/freelance-contracts-dataset-1-3-million-entries": "Freelance contracts (1.3M)",
    "sarveshchhetri/freelancer-success-earnings-and-churn-prediction": "Freelancer success & churn",
    "adityammantri/trial-1": "Labelled fraudulent / legitimate job postings",
}


def _has_credentials() -> bool:
    home = Path.home() / ".kaggle"
    return bool(
        os.environ.get("KAGGLE_API_TOKEN")
        or (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"))
        or (home / "access_token").exists()
        or (home / "kaggle.json").exists()
    )


def download_all(force: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not _has_credentials():
        sys.exit("No Kaggle credentials found. Set KAGGLE_API_TOKEN or create ~/.kaggle/access_token.")

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    for slug, desc in KAGGLE_DATASETS.items():
        target = RAW_DIR / slug.split("/")[1]
        if target.exists() and not force:
            print(f"[SKIP] {slug} already downloaded")
            continue
        print(f"[DOWNLOAD] {slug} — {desc}")
        target.mkdir(parents=True, exist_ok=True)
        api.dataset_download_files(slug, path=str(target), unzip=False, quiet=False)
        for z in target.glob("*.zip"):
            with zipfile.ZipFile(z) as zf:
                zf.extractall(target)
            z.unlink()
        # Flatten files into data/raw so the processor finds them by name
        for f in target.rglob("*"):
            if f.is_file() and not (RAW_DIR / f.name).exists():
                shutil.copy2(f, RAW_DIR / f.name)
    print("[OK] All datasets available in", RAW_DIR)


if __name__ == "__main__":
    download_all(force="--force" in sys.argv)
