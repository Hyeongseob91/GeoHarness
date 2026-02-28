# Stage 1: Build frontend
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim

LABEL maintainer="GeoHarness Team"
LABEL service="geoharness-api"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH=/app/src
ENV PORT=8080
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
COPY --from=frontend /frontend/out /app/frontend/out
EXPOSE 8080
# python src/main.py: PYTHONPATH=/app/src makes src/ internals top-level,
# which conflicts with uvicorn's package-style module resolution (no src/__init__.py).
CMD ["python", "src/main.py"]
