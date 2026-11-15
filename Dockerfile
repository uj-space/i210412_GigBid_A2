# Multi-stage Dockerfile for single-URL cloud deployment (Hugging Face Spaces / Render / Railway)
FROM node:20-slim AS web-builder
WORKDIR /app/apps/web
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY . .
COPY --from=web-builder /app/apps/web/dist /app/apps/web/dist

EXPOSE 7860
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
