# Extending GigBid

## 1. Adding a New Freelancer Persona
1. Add a persona JSON file under `data/personas/<persona_id>.json` following the schema (`persona`, `items[]` with `evidence_id`, `type`, `title`, `summary`, `skills`, `client_industry`, `outcome`).
2. Add the persona option to the `<select>` in `apps/web/src/App.tsx` (`SignIn` component).
3. `rag/ingest/ingest.py` (`load_portfolio_items`) automatically discovers `data/personas/*.json`.

## 2. Adding a New RAG Variant (`v10+`)
1. Create `rag/variants/v10_custom.py` exposing `retrieve(query: str, k: int = 5, persona: str = "default") -> list[dict]`.
2. Register `"v10": "rag.variants.v10_custom"` in `rag/retriever.py` (`_VARIANTS`) and `evals/runners/rag_eval.py`.

## 3. Adding a New MCP Server
1. Create `mcp_servers/<name>/server.py` using `mcp.server.Server`, defining Pydantic input schemas and `outputSchema` on all `types.Tool` definitions.
2. Return `(list[types.TextContent], structured_dict)` from `call_tool`.
3. Register the server's allowed tools per agent role in `agent/mcp_client.py` (`AGENT_TOOL_ALLOWLISTS`) and document them in `docs/TOOLS.md`.
