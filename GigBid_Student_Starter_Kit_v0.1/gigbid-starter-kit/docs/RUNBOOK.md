# Runbook

## Startup

### Local Development
```bash
# Backend
cd gigbid-starter-kit
python -m uvicorn apps.api.main:app --reload --port 8000

# Frontend
cd apps/web
npm install && npm run dev
```

### Docker Compose
```bash
cd gigbid-starter-kit/infra
docker compose up
```

## Rate Limits
- GigSim: 20 RPM (configurable via GIGSIM_RPM)
- Live Upwork: conservative interval, never poll aggressively

## Degraded Mode
If the marketplace MCP server is down:
- UI shows "marketplace unavailable" banner
- Work is queued and recovers when service returns
- Kill test: kill MCP server, verify UI degrades gracefully

## Recovery
- Postgres checkpointer: restart API, approve from UI, proposal submitted exactly once
- Worker restart: idempotent processing, no double-analysis or double-submission
