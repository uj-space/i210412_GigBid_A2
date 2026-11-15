# Architecture

## Overview
GigBid is a multi-agent freelancer copilot built with LangGraph, MCP servers,
and a React frontend. The system connects to GigSim for development and
Upwork's official MCP server for live use.

## Components

### Bid Graph (one thread per job)
Scout → [Analyst || Risk Assessor || Fit Matcher] → Decision → Pricing → Writer → Critic → Compliance → Approval Gate

### Conversation Graph (one thread per client)
Client Liaison → Approval Gate

### MCP Servers
- Portfolio: read-only evidence search, case studies, skills
- Marketplace: read/write tools with idempotency and dry_run
- Workspace: calendar slots, interview holds, email drafts

### Data Stores
- Postgres: checkpointer, memory store, user data
- Redis: caching, rate limiting, task queue
- ChromaDB: vector store for RAG

## Key Design Decisions
- All marketplace access through one port (R1)
- Policies in config.yaml, not hard-coded
- Human approval before any external action (R4)
- Claims verified against portfolio evidence (R5)
