"""Write all Dockerfiles and docker-compose.yml"""
from pathlib import Path

ROOT = Path(__file__).parent.parent

def write(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"Wrote {p}")

# docker-compose.yml
write("infra/docker-compose.yml", """version: \\"3.8\\

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: gigbid
      POSTGRES_USER: gigbid
      POSTGRES_PASSWORD: gigbid
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: [\\"CMD-SHELL\\", \\"pg_isready -U gigbid -d gigbid\\"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports:
      - \\"5432:5432\\"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: [\\"CMD\\", \\"redis-cli\\", \\"ping\\"]
      interval: 10s
      timeout: 5s
      retries: 5
    ports:
      - \\"6379:6379\\"

  chromadb:
    image: chromadb/chroma:0.5
    environment:
      - CHROMA_SERVER_HOST=0.0.0.0
      - CHROMA_SERVER_PORT=8001
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - \\"8001:8001\\"
    healthcheck:
      test: [\\"CMD\\", \\"curl\\", \\"-f\\", \\"http://localhost:8001/api/v1/heartbeat\\"]
      interval: 15s
      timeout: 5s
      retries: 5

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - \\"11434:11434\\"
    healthcheck:
      test: [\\"CMD\\", \\"curl\\", \\"-f\\", \\"http://localhost:11434/api/tags\\"]
      interval: 15s
      timeout: 10s
      retries: 10
    command: [\\"serve\\"]

  gigsim:
    image: gigsim/simulator:latest
    environment:
      - GIGSIM_PORT=8081
      - GIGSIM_TOKEN=gigsim-dev-token
      - GIGSIM_RATE_LIMIT=20
    ports:
      - \\"8081:8081\\"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  mcp-portfolio:
    build:
      context: ..
      dockerfile: infra/docker/mcp-portfolio.Dockerfile
    environment:
      - PORTFOLIO_DATA_DIR=/app/data/sample
    ports:
      - \\"8090:8090\\"
    depends_on:
      - chromadb
    healthcheck:
      test: [\\"CMD\\", \\"curl\\", \\"-f\\", \\"http://localhost:8090/health\\"]
      interval: 10s
      timeout: 5s
      retries: 5

  mcp-marketplace:
    build:
      context: ..
      dockerfile: infra/docker/mcp-marketplace.Dockerfile
    environment:
      - MARKETPLACE_MODE=gigsim
      - GIGSIM_BASE_URL=http://gigsim:8081
      - GIGSIM_API_TOKEN=gigsim-dev-token
      - GIGSIM_RPM=20
    ports:
      - \\"8091:8091\\"
    depends_on:
      - gigsim
    healthcheck:
      test: [\\"CMD\\", \\"curl\\", \\"-f\\", \\"http://localhost:8091/health\\"]
      interval: 10s
      timeout: 5s
      retries: 5

  mcp-workspace:
    build:
      context: ..
      dockerfile: infra/docker/mcp-workspace.Dockerfile
    ports:
      - \\"8092:8092\\"
    healthcheck:
      test: [\\"CMD\\", \\"curl\\", \\"-f\\", \\"http://localhost:8092/health\\"]
      interval: 10s
      timeout: 5s
      retries: 5

  worker:
    build:
      context: ..
      dockerfile: infra/docker/worker.Dockerfile
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql+psycopg://gigbid:gigbid@postgres:5432/gigbid
      - REDIS_URL=redis://redis:6379/0
      - MARKETPLACE_MODE=gigsim
      - GIGSIM_BASE_URL=http://gigsim:8081
      - GIGSIM_API_TOKEN=gigsim-dev-token
      - MODEL_PROFILE=open
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      mcp-marketplace:
        condition: service_healthy
    command: [\\"python\\", \\"-m\\", \\"worker.run\\"]

  api:
    build:
      context: ..
      dockerfile: infra/docker/api.Dockerfile
    environment:
      - APP_ENV=production
      - APP_SECRET_KEY=\\${APP_SECRET_KEY:-dev-secret-change-me}
      - DATABASE_URL=postgresql+psycopg://gigbid:gigbid@postgres:5432/gigbid
      - REDIS_URL=redis://redis:6379/0
      - MARKETPLACE_MODE=gigsim
      - GIGSIM_BASE_URL=http://gigsim:8081
      - GIGSIM_API_TOKEN=gigsim-dev-token
      - GIGSIM_RPM=20
      - MODEL_PROFILE=open
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8001
    ports:
      - \\"8000:8000\\"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      mcp-marketplace:
        condition: service_healthy
      chromadb:
        condition: service_healthy
    command: [\\"python\\", \\"-m\\", \\"uvicorn\\", \\"apps.api.main:app\\", \\"--host\\", \\"0.0.0.0\\", \\"--port\\", \\"8000\\"]

  web:
    build:
      context: ..
      dockerfile: infra/docker/web.Dockerfile
    environment:
      - VITE_API_BASE=http://localhost:8000
    ports:
      - \\"5173:5173\\"
    depends_on:
      - api
    command: [\\"npm\\", \\"run\\", \\"dev\\", \\"--\\", \\"--host\\", \\"0.0.0.0\\"]

  langfuse:
    image: langfuse/langfuse:latest
    environment:
      - NEXT_PUBLIC_LANGFUSE_HOST=http://localhost:3001
      - LANGFUSE_SECRET_KEY=sk-lf-dev-secret
      - LANGFUSE_PUBLIC_KEY=pk-lf-dev-public
      - DATABASE_URL=postgresql+psycopg://gigbid:gigbid@postgres:5432/langfuse
      - REDIS_URL=redis://redis:6379/1
    ports:
      - \\"3001:3000\\"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: [\\"CMD\\", \\"curl\\", \\"-f\\", \\"http://localhost:3000/api/health\\"]
      interval: 15s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  ollama_data:
""")

print(\"docker-compose.yml written\")