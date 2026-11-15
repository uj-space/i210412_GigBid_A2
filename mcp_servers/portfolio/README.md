# GigBid Portfolio MCP Server

Read-only Model Context Protocol (MCP) server exposing verified freelancer portfolio case studies, skills, and proposal drafting prompts.

## Tools, Resources & Prompts
- **Tools:** `search_evidence`, `get_case_study`, `list_skills`
- **Resources:** `portfolio://case/{id}`, `portfolio://proposal/{id}`
- **Prompts:** `answer_screening_question`, `draft_evidence_paragraph`

## Install & Run via `uvx` (No Clone Required)
```bash
# Run stdio server directly from GitHub
uvx --from git+https://github.com/uj-space/i210412_GigBid_A2 gigbid-portfolio-mcp

# Or install locally in editable mode and run
pip install -e .
gigbid-portfolio-mcp
```

## Run Locally (stdio or Streamable HTTP)
```bash
# stdio (for Claude Desktop / MCP clients)
python -m mcp_servers.portfolio.server --transport stdio

# Streamable HTTP (/mcp and /health)
python -m mcp_servers.portfolio.server --transport http --port 8001
```

## Run via Docker
```bash
docker build -f infra/docker/mcp-portfolio.Dockerfile -t gigbid-portfolio-mcp .
docker run -p 8001:8001 gigbid-portfolio-mcp
```
