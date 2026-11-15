import os
from pathlib import Path

ROOT = Path(__file__).parent.parent

def w(path, content):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    print('Wrote', path)

# API Dockerfile
w('infra/docker/api.Dockerfile', '''FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
''')

# Web Dockerfile
w('infra/docker/web.Dockerfile', '''FROM node:20-alpine
WORKDIR /app
COPY apps/web/package.json ./apps/web/
COPY apps/web/package-lock.json ./apps/web/
RUN cd apps/web && npm install
COPY apps/web ./apps/web
RUN cd apps/web && npm run build
FROM nginx:alpine
COPY --from=0 /app/apps/web/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off"]
''')

# Worker Dockerfile
w('infra/docker/worker.Dockerfile', '''FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./worker/pyproject.toml ./
RUN pip install --no-cache-dir -e worker
COPY . .
CMD ["python", "-m", "worker.run"]
''')

# MCP Portfolio Dockerfile
w('infra/docker/mcp-portfolio.Dockerfile', '''FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./mcp_servers/portfolio/pyproject.toml ./
RUN pip install --no-cache-dir -e mcp_servers/portfolio
COPY . .
CMD ["python", "-m", "mcp_servers.portfolio.server"]
''')

# MCP Marketplace Dockerfile
w('infra/docker/mcp-marketplace.Dockerfile', '''FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./mcp_servers/marketplace/pyproject.toml ./
RUN pip install --no-cache-dir -e mcp_servers/marketplace
COPY . .
CMD ["python", "-m", "mcp_servers.marketplace.server"]
''')

# MCP Workspace Dockerfile
w('infra/docker/mcp-workspace.Dockerfile', '''FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./mcp_servers/workspace/pyproject.toml ./
RUN pip install --no-cache-dir -e mcp_servers/workspace
COPY . .
CMD ["python", "-m", "mcp_servers.workspace.server"]
''')

print('All Dockerfiles written')
