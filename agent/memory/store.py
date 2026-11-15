"""Long-term memory store (R7): style memory and outcome memory with promotion rules."""
from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from agent.memory.promotion_rules import should_promote_style_edit, should_record_outcome

ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "data" / "processed" / "memory_store.json"


class GigBidMemoryStore:
    """Persistent JSON-backed store for promoted style and outcome memory per user."""

    def __init__(self, path: Path = STORE_PATH) -> None:
        self.path = path
        self._data: dict[str, Any] = {"style": {}, "outcome": {}, "edit_counts": {}}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get_style_memory(self, user_id: str) -> list[dict[str, Any]]:
        return list((self._data.get("style") or {}).get(user_id, []))

    def get_outcome_memory(self, user_id: str) -> list[dict[str, Any]]:
        return list((self._data.get("outcome") or {}).get(user_id, []))

    def delete_memory(self, user_id: str, kind: str | None = None) -> None:
        if kind in (None, "style"):
            (self._data.get("style") or {}).pop(user_id, None)
        if kind in (None, "outcome"):
            (self._data.get("outcome") or {}).pop(user_id, None)
        self._save()

    def record_user_edit(self, user_id: str, original: str, edited: str) -> dict[str, Any]:
        """Diff user edit and promote to style memory only when promotion rule passes."""
        diff = list(difflib.unified_diff(original.splitlines(), edited.splitlines(), lineterm=""))
        rule_text = None
        if len(edited) < len(original) * 0.85:
            rule_text = "Prefer concise proposals; trim filler sentences."
        elif "passionate" in original.lower() and "passionate" not in edited.lower():
            rule_text = "Never say 'passionate'."
        elif diff:
            rule_text = f"User edit preference: {diff[-1][:120]}"

        promoted = False
        if rule_text:
            counts = self._data.setdefault("edit_counts", {}).setdefault(user_id, {})
            counts[rule_text] = int(counts.get(rule_text, 0)) + 1
            if should_promote_style_edit(counts[rule_text], consistent_pattern=True):
                entries = self._data.setdefault("style", {}).setdefault(user_id, [])
                if not any(e.get("text") == rule_text for e in entries):
                    entries.append({"text": rule_text, "count": counts[rule_text]})
                promoted = True
            self._save()
        return {"rule": rule_text, "promoted": promoted}

    def record_outcome(self, user_id: str, category: str, outcome: str, evidence_count: int = 1) -> bool:
        if not should_record_outcome(outcome, min_evidence=evidence_count):
            return False
        entries = self._data.setdefault("outcome", {}).setdefault(user_id, [])
        entries.append({"category": category, "outcome": outcome, "evidence_count": evidence_count})
        self._save()
        return True


_STORE = GigBidMemoryStore()


def get_memory_store() -> GigBidMemoryStore:
    return _STORE
