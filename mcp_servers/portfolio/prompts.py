"""Portfolio MCP prompt templates (A1)."""
from __future__ import annotations

import mcp.types as types


def get_prompt_definitions() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="answer_screening_question",
            description="Answer a client screening question strictly from verified portfolio evidence.",
            arguments=[
                types.PromptArgument(name="question", required=True),
                types.PromptArgument(name="evidence", required=False),
            ],
        ),
        types.Prompt(
            name="draft_evidence_paragraph",
            description="Draft one proposal paragraph citing a specific case study.",
            arguments=[
                types.PromptArgument(name="requirement", required=True),
                types.PromptArgument(name="evidence_id", required=True),
            ],
        ),
    ]


def render_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    args = arguments or {}
    if name == "draft_evidence_paragraph":
        req = args.get("requirement", "")
        eid = args.get("evidence_id", "")
        return types.GetPromptResult(
            description="Evidence-backed paragraph drafter",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=f"Address requirement '{req}' citing only portfolio item [{eid}]."),
                )
            ],
        )
    question = args.get("question", "")
    return types.GetPromptResult(
        description="Screening-question answerer",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(type="text", text=f"Answer using only portfolio evidence: {question}"),
            )
        ],
    )
