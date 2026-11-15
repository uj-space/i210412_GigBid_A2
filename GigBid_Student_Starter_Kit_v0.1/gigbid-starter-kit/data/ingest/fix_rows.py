"""Add row limit to process_kaggle.py to prevent timeout on large files."""
from pathlib import Path

filepath = Path(__file__).parent / "process_kaggle.py"

with open(filepath, "r") as f:
    content = f.read()

# Add MAX_ROWS_PER_FILE constant before process_upwork_jobs_2024
old = "def process_upwork_jobs_2024(raw_dir: Path) -> list[dict]:"
new = "MAX_ROWS_PER_FILE = 1000\n\n\ndef process_upwork_jobs_2024(raw_dir: Path) -> list[dict]:"

content = content.replace(old, new, 1)

# Add row limit in CSV processing loop
old2 = '''            if csv_file.suffix == ".csv":
                with open(csv_file, encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        job = _normalize_job(row, source="kaggle_upwork_2024")
                        if job:
                            jobs.append(job)'''

new2 = '''            if csv_file.suffix == ".csv":
                with open(csv_file, encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i >= MAX_ROWS_PER_FILE:
                            break
                        job = _normalize_job(row, source="kaggle_upwork_2024")
                        if job:
                            jobs.append(job)'''

content = content.replace(old2, new2, 1)

with open(filepath, "w") as f:
    f.write(content)

print("SUCCESS: Row limit added")