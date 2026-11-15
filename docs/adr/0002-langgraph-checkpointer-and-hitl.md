# ADR 0002: LangGraph StateGraph Checkpointing and Human-in-the-Loop `interrupt()`

- **Status:** Accepted
- **Context:** Proposals spend Connects and send external messages on the user's behalf. A crash mid-workflow or an unapproved submission is unacceptable.
- **Decision:** Orchestrate `bid_graph` and `conversation_graph` using LangGraph `StateGraph` with parallel `Send` fan-out (`analyst`, `risk_assessor`, `fit_matcher`), a bounded Critic loop (`max 2` revisions), a step/token budget guard (`needs_attention`), durable checkpointing (`PostgresSaver` when `DATABASE_URL` is set, else `MemorySaver`), and mandatory `interrupt()` gates before any `submit_proposal` or `send_message` call.
- **Consequences:** Human edits at the approval gate are re-checked by `compliance_node`; threads can pause indefinitely and resume via `Command(resume=...)` or `replay_from_node()`.
