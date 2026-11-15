# AI Usage Disclosure

## Tools Used
- **Claude (Cline)**: Primary coding assistant for implementing agent nodes, graphs,
  MCP servers, RAG variants, FastAPI backend, React frontend, documentation, and
  deployment configuration.

## Files Assisted
- `agent/nodes/*.py` — All agent node implementations
- `agent/graphs/*.py` — Bid and conversation graphs
- `agent/state.py` — Typed LangGraph state
- `agent/handoffs.py` — Pydantic hand-off objects
- `agent/marketplace_port.py` — Marketplace port abstraction
- `mcp_servers/*/server.py` — All three MCP servers
- `rag/variants/v*.py` — RAG variants V0-V9
- `rag/verify.py` — Claim verification
- `apps/api/main.py` — FastAPI backend
- `apps/web/src/App.tsx` — React frontend
- `docs/*.md` — All documentation
- `infra/docker-compose.yml` — Production deployment

## Incorrect Suggestion Identified and Corrected
The AI initially suggested using `langgraph-supervisor` (prebuilt) as the primary
graph architecture. This was incorrect for this assignment because:

1. The assignment requires a **hand-written** LangGraph `StateGraph` (R3), not a
   prebuilt supervisor
2. The prebuilt supervisor doesn't support the interrupt-based human approval
   pattern (R4) in the required way
3. Custom state with separate state/trace/memory separation (C2) is harder with
   prebuilt supervisors

**Correction**: Implemented hand-written `StateGraph` with explicit nodes,
parallel branches via `Send`, `interrupt()` for human approval, and custom state
management as required by the assignment.

## Accountability
All code was reviewed, tested, and verified by the developer. The AI assistant
was used for code generation and suggestions, but every line was examined and
validated before inclusion.
