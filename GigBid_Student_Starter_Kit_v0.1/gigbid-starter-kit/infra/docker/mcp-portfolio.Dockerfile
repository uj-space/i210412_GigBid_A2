FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./mcp_servers/portfolio/pyproject.toml ./
RUN pip install --no-cache-dir -e mcp_servers/portfolio
COPY . .
CMD ["python", "-m", "mcp_servers.portfolio.server"]
