# syntax=docker/dockerfile:1

FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build \
    && rm -rf dist \
    && mkdir -p dist \
    && cp -r ../backend/app/static/app/. dist/

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/frontend/dist/ backend/app/static/app

ENV FLASK_APP=backend.app.serverless:app

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
