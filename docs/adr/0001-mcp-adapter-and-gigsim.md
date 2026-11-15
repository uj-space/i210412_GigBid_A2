# ADR 0001: Modular MCP Servers, Marketplace Port Abstraction, and GigSim

- **Status:** Accepted
- **Context:** GigBid interacts with portfolio evidence, job search/bidding, and calendar/email tools. Exposing a single unconstrained tool server creates high blast-radius risk and prevents offline reproducibility.
- **Decision:** Split tools into three MCP servers (`portfolio` read-only, `marketplace` read/write behind Bearer auth + rate limiting + audit log, `workspace` calendar/email) and abstract marketplace access behind `agent/marketplace_port.py` with `GigSimAdapter` (default local simulator) and `UpworkLiveAdapter` (draft-only live mode).
- **Consequences:** All write tools require `idempotency_key` and `dry_run` support; per-agent allowlists (`AGENT_TOOL_ALLOWLISTS`) restrict write exposure; the full test and evaluation suite runs deterministically offline without live Upwork credentials.
