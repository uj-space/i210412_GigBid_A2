"""Long-term memory promotion rules (R7). Raw tool output never enters memory."""
from __future__ import annotations


def should_promote_style_edit(edit_count: int, consistent_pattern: bool) -> bool:
    return bool(consistent_pattern and edit_count >= 3)


def should_record_outcome(outcome: str, min_evidence: int = 1) -> bool:
    return bool(outcome in {"won", "replied", "ignored", "lost", "hired"} and min_evidence >= 1)
