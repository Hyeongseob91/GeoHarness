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
# Install deps directly to system Python (no venv) so CMD python can find them
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt && \
    uv pip install --system -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt
COPY . .
COPY --from=frontend /frontend/out /app/frontend/out
EXPOSE 8080
CMD ["python", "src/main.py"]
