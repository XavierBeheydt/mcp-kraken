# syntax=docker/dockerfile:1.7

# -----------------------------------------------------------------------------
# Stage 0: uv binary (decoupled from Python version)
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:latest AS uv-bin

# -----------------------------------------------------------------------------
# Stage 1: build a self-contained virtualenv
# -----------------------------------------------------------------------------
FROM python:3.14-slim-bookworm AS builder

COPY --from=uv-bin /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first, in their own layer for cache reuse.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Now bring in the project itself.
COPY pyproject.toml uv.lock README.md /app/
COPY src /app/src
COPY .git /app/.git

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 2: distroless-style minimal runtime
# -----------------------------------------------------------------------------
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    MCP_KRAKEN_TOKEN_DB="/data/tokens.db"

RUN groupadd --system --gid 10001 mcp \
 && useradd  --system --uid 10001 --gid mcp --home /app --shell /sbin/nologin mcp \
 && mkdir -p /app /data \
 && chown -R mcp:mcp /app /data

WORKDIR /app
COPY --from=builder --chown=mcp:mcp /app /app

USER mcp
EXPOSE 8765
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "\
import urllib.request, os, sys; \
port = os.environ.get('MCP_KRAKEN_PORT', '8765'); \
urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3); \
sys.exit(0)" || exit 1

ENTRYPOINT ["mcp-kraken"]
CMD ["serve"]
