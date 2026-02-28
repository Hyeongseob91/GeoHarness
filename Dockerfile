# Use the latest Python 3.11 for broader pip package compatibility (pyproj, etc.)
FROM python:3.11-slim

# Install uv for fast dependency management and set env variables
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH=/app/src

# Setup Working Directory
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install packages using uv (bypassing venv creation script for docker)
RUN uv sync --frozen --no-dev

# Copy the rest of the generic application code
COPY . .

# Expose the Cloud Run default port
EXPOSE 8080

# Command to run the application
# Using `python src/main.py` instead of `uvicorn src.main:app`
# because PYTHONPATH=/app/src treats src/ internals as top-level modules,
# which conflicts with uvicorn's package-style module resolution.
CMD ["python", "src/main.py"]
