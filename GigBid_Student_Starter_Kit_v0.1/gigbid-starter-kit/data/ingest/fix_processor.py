"""Fix the process_kaggle.py to also process root-level Kaggle files."""
from pathlib import Path

filepath = Path(__file__).parent / "process_kaggle.py"

with open(filepath, "r") as f:
    lines = f.readlines()

# Lines 148-168 (0-indexed 147-167) need replacement
new_function = '''def process_all_kaggle() -> dict:
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
'''

# Replace lines 148-168 (0-indexed: 147-167)
new_lines = lines[:147] + [new_function + "\n"] + lines[167:]

with open(filepath, "w") as f:
    f.writelines(new_lines)

print("SUCCESS: File updated")