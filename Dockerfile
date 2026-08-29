# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.24 AS uv

FROM python:3.13.7-slim-bookworm AS builder
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock README.md ./
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.13.7-slim-bookworm AS runner
WORKDIR /app
RUN useradd --system --uid 10001 --create-home appuser
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
EXPOSE 8000
USER appuser

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
    CMD python -m app.smoke --path /health/live --attempts 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips ${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
