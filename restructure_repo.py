"""Move all contents from GigBid_Student_Starter_Kit_v0.1/ to repo root."""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parent
src = root / "GigBid_Student_Starter_Kit_v0.1"

if not src.exists():
    print(f"ERROR: {src} not found")
    exit(1)

items = list(src.iterdir())
print(f"Moving {len(items)} items from {src.name} to root...")

for item in items:
    dest = root / item.name
    if dest.exists():
        print(f"  SKIP (exists): {item.name}")
        continue
    shutil.move(str(item), str(dest))
    print(f"  MOVED: {item.name}")

# Remove the now-empty directory
try:
    src.rmdir()
    print(f"REMOVED: {src.name}")
except OSError as e:
    print(f"WARNING: Could not remove {src.name}: {e}")

print("\nDone! Repository restructured.")