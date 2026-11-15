FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./worker/pyproject.toml ./
RUN pip install --no-cache-dir -e worker
COPY . .
CMD ["python", "-m", "worker.run"]
