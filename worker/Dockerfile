FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

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
CMD ["python", "-m", "arq", "app.main.WorkerSettings"]
