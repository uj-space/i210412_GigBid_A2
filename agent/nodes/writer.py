"""Proposal Writer node: draft a personalised proposal citing evidence only."""
from __future__ import annotations

from agent.state import GigBidState
from agent.handoffs import ProposalDraft
from rag.verify import verify_claims


def writer_node(state: GigBidState) -> GigBidState:
    job = state.get("job", {}) or {}
    job_spec = state.get("job_spec", {}) or {}
    fit = state.get("fit_report", {}) or {}
    price = state.get("price_quote", {}) or {}
    evidence = state.get("evidence", []) or []
    style_memory = state.get("style_memory", []) or []

    cover = _draft_cover_letter(job, job_spec, fit, price, evidence, style_memory)
    answers = _draft_screening_answers(job, evidence)

    draft = ProposalDraft(
        job_id=job.get("job_id", ""),
        cover_letter=cover,
        screening_answers=answers,
        evidence_ids=[e.get("evidence_id") or e.get("id") for e in evidence],
        status="pending_review",
        claim_citations=[{"claim": c, "evidence_id": e.get("evidence_id") or e.get("id")}
                         for c, e in zip(_split_claims(cover), evidence)],
    )
    state["proposal_draft"] = draft.model_dump()

    verification = verify_claims(cover, evidence)
    state["claim_verification"] = verification
    state["unsupported_claims"] = [v for v in verification if v.get("verdict") == "unsupported"]
    return state


def _draft_cover_letter(job, job_spec, fit, price, evidence, style_memory) -> str:
    title = job.get("title", "this project")
    skills = ", ".join(job_spec.get("required_skills", []) or [])
    matched = ", ".join(fit.get("matched_skills", []) or [])
    bids = price.get("suggested_bid", "N/A")
    cites = "; ".join(f"[{e.get('evidence_id') or e.get('id')}]" for e in evidence[:3]) or "[portfolio]"
    style = ""
    if style_memory:
        style = " " + " ".join(s.get("text", "") for s in style_memory[:3])
    return (
        f"Dear Client,\n\nI am writing to apply for \"{title}\". "
        f"My background in {skills} aligns with your requirements, and I have "
        f"demonstrated relevant work in {matched} {cites}. "
        f"I propose to deliver this project for {bids} and can start immediately. "
        f"I have successfully completed similar engagements and would welcome "
        f"the chance to discuss your goals in detail.{style}\n\nThank you."
    )


def _draft_screening_answers(job, evidence) -> list[str]:
    qs = list(job.get("screening_questions", []) or [])
    answers = []
    for q in qs:
        answers.append(
            f"I would approach this by clarifying your success criteria, then "
            f"delivering incremental work you can review at each stage."
        )
    return answers or ["I am available to discuss your project requirements."]


def _split_claims(text: str) -> list[str]:
    return [s.strip() for s in text.split(".") if s.strip()][:5]
