from __future__ import annotations

from typing import Any
from pathlib import Path
import json
import hashlib


def load_portfolio_items(data_dir: str = "data") -> list[dict[str, Any]]:
    p = Path(data_dir) / "portfolio_items.json"
    if not p.exists():
        return []
    items = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for it in items:
        eid = it.get("evidence_id") or it.get("id") or hashlib.sha256(
            (it.get("title", "") + str(it.get("skills", []))).encode()).hexdigest()[:12]
        out.append({
            "evidence_id": eid,
            "type": it.get("type", "case_study"),
            "title": it.get("title", ""),
            "summary": it.get("summary", ""),
            "skills": it.get("skills", []),
            "outcome": it.get("outcome", ""),
            "source": it.get("source", ""),
            "text": (it.get("title", "") + " " + it.get("summary", "") +
                     " " + " ".join(it.get("skills", []))).strip(),
        })
    return out
