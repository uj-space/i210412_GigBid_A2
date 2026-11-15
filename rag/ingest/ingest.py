"""Portfolio & repository ingestion with full metadata and incremental indexing (B1)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

_INCREMENTAL_ITEMS: list[dict[str, Any]] = []


def add_portfolio_item(item: dict[str, Any]) -> None:
    """Incrementally add a new portfolio item (e.g. from UI upload or GitHub MCP) and reset index."""
    _INCREMENTAL_ITEMS.append(item)
    try:
        from rag.index.hybrid_index import invalidate_index
        invalidate_index()
    except Exception:
        pass


def load_portfolio_items(persona: str = "default") -> list[dict[str, Any]]:
    """Load portfolio items with metadata (persona, type, project, skills, date, client_industry, outcome)."""
    items: list[dict[str, Any]] = []
    personas_dir = DATA_DIR / "personas"
    if personas_dir.exists():
        if persona and persona != "default":
            pfile = personas_dir / f"{persona}.json"
            if pfile.exists():
                data = json.loads(pfile.read_text(encoding="utf-8"))
                items.extend(data.get("items", []))
        else:
            for pfile in sorted(personas_dir.glob("*.json")):
                data = json.loads(pfile.read_text(encoding="utf-8"))
                items.extend(data.get("items", []))

    if not items:
        sample_file = DATA_DIR / "sample" / "portfolio_items.json"
        if sample_file.exists():
            items.extend(json.loads(sample_file.read_text(encoding="utf-8")))

    if _INCREMENTAL_ITEMS:
        for it in _INCREMENTAL_ITEMS:
            if persona in {"default", it.get("persona", "default")}:
                items.append(it)

    # Ensure every item has normalized fields
    out: list[dict[str, Any]] = []
    for it in items:
        eid = it.get("evidence_id") or it.get("id") or ""
        text = it.get("text") or f"{it.get('title', '')} {it.get('summary', '')} {' '.join(it.get('skills', []) or [])}"
        out.append({
            **it,
            "evidence_id": eid,
            "persona": it.get("persona", "default"),
            "type": it.get("type", "case_study"),
            "project": it.get("project", it.get("title", "")),
            "skills": list(it.get("skills", []) or []),
            "date": it.get("date", ""),
            "client_industry": it.get("client_industry", "General"),
            "outcome": it.get("outcome", "verified"),
            "text": text.strip(),
        })
    return out
