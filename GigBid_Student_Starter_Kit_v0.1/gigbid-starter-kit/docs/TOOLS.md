# MCP Tool Inventory

| Tool | Server | Read/Write | Annotations | Auth |
|------|--------|------------|-------------|------|
| search_evidence | Portfolio | Read | readOnlyHint | None |
| get_case_study | Portfolio | Read | readOnlyHint | None |
| list_skills | Portfolio | Read | readOnlyHint | None |
| search_jobs | Marketplace | Read | readOnlyHint | Bearer token |
| get_job | Marketplace | Read | readOnlyHint | Bearer token |
| get_client_history | Marketplace | Read | readOnlyHint | Bearer token |
| get_connects_balance | Marketplace | Read | readOnlyHint | Bearer token |
| create_proposal_draft | Marketplace | Write | destructiveHint: false, idempotentHint: true | Bearer token |
| submit_proposal | Marketplace | Write | destructiveHint: true, idempotentHint: true | Bearer token |
| send_message | Marketplace | Write | destructiveHint: true, idempotentHint: true | Bearer token |
| free_calendar_slots | Workspace | Read | readOnlyHint | None |
| create_interview_hold | Workspace | Write | destructiveHint: false, idempotentHint: true | None |
| create_email_draft | Workspace | Write | destructiveHint: false, idempotentHint: true | None |

## Third-Party Servers

| Server | Purpose | Trust Rationale |
|--------|---------|-----------------|
| Upwork Official MCP | Live marketplace access | Official Upwork integration, OAuth 2.1 |
| GitHub MCP | Repository ingestion for case studies | Public repositories, read-only access |
