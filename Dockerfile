# Build stage
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/

RUN uv sync --frozen --no-dev


# Runtime stage
FROM python:3.11-slim AS runtime

ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd --gid ${APP_GID} appgroup \
    && useradd --uid ${APP_UID} --gid appgroup --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup sql/ ./sql/
COPY --chown=appuser:appgroup configs/ ./configs/
COPY --chown=appuser:appgroup data/ ./data/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1

USER appuser