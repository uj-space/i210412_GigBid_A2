# AI Usage Disclosure

In accordance with academic integrity requirements for AI-4016 (Agentic AI):

- **Human Design & Verification:** All architectural decisions (MCP separation, LangGraph `Send` fan-out, HITL `interrupt()` gates, RAG hybrid/rerank pipeline, and evaluation methodology), dataset curation (`data/ingest/`), and verification assertions were authored, reviewed, and validated by the student.
- **AI Coding Assistance:** An AI coding assistant was used for boilerplate scaffolding, test-case drafting, and documentation formatting. Every generated module was executed and verified locally via `pytest`, `tsc && vite build`, and the evaluation runners in `evals/runners/`.
- **Runtime Models:** GigBid's agent nodes support OpenAI-compatible/Ollama LLMs via `agent/llm.py` (`OPENAI_API_KEY` / `OLLAMA_BASE_URL`) with a deterministic rule-based fallback for reproducible offline evaluation.
