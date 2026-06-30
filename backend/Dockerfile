FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

FROM base AS deps
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen --no-install-project

FROM base AS runtime
WORKDIR /app
RUN groupadd --system appgroup && useradd --system --gid appgroup appuser
COPY --from=deps --chown=appuser:appgroup /app/.venv /app/.venv
COPY --chown=appuser:appgroup . .
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
