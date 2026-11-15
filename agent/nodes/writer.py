"""Proposal Writer + Claim Verifier node: drafts evidence-cited proposals and prunes unsupported claims."""
from __future__ import annotations

from agent.handoffs import ProposalDraft
from agent.llm import get_node_llm, load_prompt
from agent.memory.store import get_memory_store
from agent.safety import delimit_untrusted
from agent.state import GigBidState
from rag.verify import prune_unsupported_claims, split_claims


def writer_node(state: GigBidState) -> GigBidState:
    prompt = load_prompt("writer")
    user_id = state.get("user_id", "default")
    job = state.get("job", {}) or {}
    job_spec = state.get("job_spec", {}) or {}
    fit = state.get("fit_report", {}) or {}
    price = state.get("price_quote", {}) or {}
    evidence = state.get("evidence", []) or []
    critique = state.get("critique", {}) or {}
    store_style = get_memory_store().get_style_memory(user_id)
    style_memory = (state.get("style_memory") or []) + store_style

    llm = get_node_llm("writer")
    cover = ""
    if llm is not None and evidence:
        ev_text = "\n".join(
            f"- [{e.get('evidence_id')}] {e.get('title')}: {e.get('summary','')}" for e in evidence[:5]
        )
        style_str = "\n".join(f"- {s.get('text')}" for s in style_memory[:5])
        fb = "; ".join(critique.get("suggestions", []) or [])
        msg = (
            f"{prompt}\n\n"
            f"{delimit_untrusted(job.get('title','') + ': ' + job.get('description',''), 'untrusted_job_post')}\n\n"
            f"Verified Evidence:\n{ev_text}\n\nStyle Rules:\n{style_str}\n\n"
            f"Suggested Bid: ${price.get('suggested_bid', 500)}\nCritic Feedback: {fb}"
        )
        try:
            resp = llm.invoke(msg)
            cover = getattr(resp, "content", str(resp)).strip()
        except Exception:
            cover = ""

    if not cover:
        cover = _draft_grounded_cover_letter(job, job_spec, fit, price, evidence, style_memory)

    # B3: Claim verification & pruning before Critic sees the draft
    cleaned_cover, verification, before_rate, after_rate = prune_unsupported_claims(cover, evidence)
    answers = _draft_screening_answers(job, evidence)

    citations = []
    for v in verification:
        if v.get("verdict") != "unsupported" and v.get("evidence_id"):
            citations.append({"claim": v["claim"], "evidence_id": v["evidence_id"], "verdict": v["verdict"]})

    draft = ProposalDraft(
        job_id=job.get("job_id", ""),
        cover_letter=cleaned_cover,
        screening_answers=answers,
        evidence_ids=[e.get("evidence_id") or e.get("id") for e in evidence[:5]],
        status="pending_review",
        claim_citations=citations,
    )

    return {
        "proposal_draft": draft.model_dump(),
        "claim_verification": verification,
        "unsupported_claims": [v for v in verification if v.get("verdict") == "unsupported"],
        "step_count": int(state.get("step_count", 0) or 0) + 1,
    }


def _draft_grounded_cover_letter(job, job_spec, fit, price, evidence, style_memory) -> str:
    title = job.get("title", "your project")
    matched = ", ".join(fit.get("matched_skills", []) or job_spec.get("required_skills", [])[:3] or ["Python"])
    top_ev = [e for e in evidence if e.get("type") in {"case_study", "repo_code", "cv"}] or evidence
    ev_lines = []
    for e in top_ev[:2]:
        eid = e.get("evidence_id") or e.get("id") or "ev"
        proj = e.get("project") or e.get("title") or "recent project"
        summary = (e.get("summary") or "").strip().rstrip(".")
        ev_lines.append(f"In {proj} [{eid}], {summary}.")

    evidence_block = " ".join(ev_lines) if ev_lines else "I can share relevant code samples upon request."
    bid = price.get("suggested_bid", 500)
    concise = any("concise" in (s.get("text", "").lower()) for s in style_memory)

    opening = f"For \"{title}\", my hands-on work in {matched} directly matches your deliverables."
    closing = (
        f"Proposed budget: ${bid:.0f} USD across clear milestones."
        if concise
        else f"I propose a milestone-based delivery at ${bid:.0f} USD and can start with a brief architecture walkthrough."
    )
    return f"{opening}\n\n{evidence_block}\n\n{closing}"


def _draft_screening_answers(job, evidence) -> list[str]:
    qs = list(job.get("screening_questions", []) or [])
    if not qs:
        return ["Happy to share milestone details and relevant portfolio repositories."]
    eid = (evidence[0].get("evidence_id") or evidence[0].get("id")) if evidence else "portfolio"
    return [f"Regarding '{q}': I follow a test-first milestone workflow as demonstrated in [{eid}]." for q in qs]
