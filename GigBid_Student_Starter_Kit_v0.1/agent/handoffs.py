"""Typed Pydantic hand-off objects exchanged between agents (C3)."""
from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_id: str
    title: str
    deliverables: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: str = "USD"
    duration_days: Optional[int] = None
    screening_questions: List[str] = Field(default_factory=list)
    hidden_needs: List[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class RiskReport(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    flags: List[str] = Field(default_factory=list)
    explanation: str
    scam: bool = False
    unpaid_work: bool = False
    off_platform: bool = False
    injection: bool = False


class FitReport(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    requirement_matrix: List[dict[str, Any]] = Field(default_factory=list)
    reasons: str = ""


class BidDecision(BaseModel):
    decision: str  # skip | watch | bid
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    autonomy_override: bool = False


class PriceQuote(BaseModel):
    job_id: str
    suggested_bid: float
    currency: str = "USD"
    connects_cost: int
    worth_it: bool
    floor: Optional[float] = None
    rationale: str = ""


class ProposalDraft(BaseModel):
    job_id: str
    cover_letter: str
    screening_answers: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    status: str = "pending_review"
    claim_citations: List[dict[str, Any]] = Field(default_factory=list)


class Critique(BaseModel):
    grounded: bool
    unsupported_claims: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    length_ok: bool
    personalised: bool
    revision_count: int = 0


class ComplianceVerdict(BaseModel):
    passed: bool
    violations: List[str] = Field(default_factory=list)
    reason: str = ""
    redacted: bool = False
