# mcp-kraken — development command runner.
# Usage:   just <recipe>   (run `just` with no args for the list)

set shell := ["bash", "-cu"]
set dotenv-load := true

# Default: show the recipe list.
default:
    @just --list --unsorted

# ----------------------------------------------------------------- environment

# Resolve dependencies and create / update .venv.
sync:
    uv sync --all-extras --dev

# Forcefully rebuild .venv from uv.lock.
sync-fresh:
    rm -rf .venv
    uv sync --all-extras --dev

# ----------------------------------------------------------------- run

# Run the HTTP MCP server (uses values from .env).
serve *args:
    uv run mcp-kraken serve {{args}}

# Run the HTTPS server using ./certs/{key,cert}.pem (generate with `just cert-local`).
serve-https *args:
    uv run mcp-kraken serve \
        --ssl-keyfile certs/key.pem \
        --ssl-certfile certs/cert.pem {{args}}

# Run on stdio for local Claude Desktop / `uvx` setups.
serve-stdio:
    uv run mcp-kraken serve --stdio

# Generate a locally-trusted TLS cert for HTTPS testing.
# Requires mkcert (https://github.com/FiloSottile/mkcert).
# `mkcert -install` adds a local CA to the OS / browser / app trust stores so
# that Claude Desktop will accept the resulting cert without warnings.
cert-local DEST="certs":
    @command -v mkcert >/dev/null || { \
        echo "mkcert not found. Install: https://github.com/FiloSottile/mkcert"; \
        exit 1; }
    mkdir -p {{DEST}}
    mkcert -install
    mkcert -key-file {{DEST}}/key.pem -cert-file {{DEST}}/cert.pem \
        localhost 127.0.0.1 ::1 host.docker.internal
    @echo
    @echo "Generated {{DEST}}/cert.pem + {{DEST}}/key.pem"
    @echo "Start the HTTPS server with:  just serve-https"

# Generate a raw self-signed cert with openssl (NOT trusted by Claude Desktop
# unless you import it into the OS trust store manually).
cert-openssl DEST="certs":
    mkdir -p {{DEST}}
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout {{DEST}}/key.pem -out {{DEST}}/cert.pem \
        -days 365 -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1"
    @echo
    @echo "Generated {{DEST}}/cert.pem + {{DEST}}/key.pem (self-signed)"

# Issue a new bearer token.
token-create NAME *args:
    uv run mcp-kraken token create {{NAME}} {{args}}

# List bearer tokens.
token-list:
    uv run mcp-kraken token list

# Revoke a token by id.
token-revoke ID:
    uv run mcp-kraken token revoke {{ID}}

# ----------------------------------------------------------------- quality

# Lint with ruff.
lint:
    uv run ruff check .

# Auto-fix lint findings + format.
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Format check (does not modify files).
fmt-check:
    uv run ruff format --check .

# Static type check with mypy.
typecheck:
    uv run mypy

# Run the test suite.
test *args:
    uv run pytest {{args}}

# Coverage report (terminal).
cov:
    uv run pytest --cov --cov-report=term-missing

# CI bundle: everything that CI runs locally.
check: lint fmt-check typecheck test

# ----------------------------------------------------------------- build

# Build sdist + wheel into ./dist.
build:
    uv build

# Wipe build artefacts.
clean:
    rm -rf dist build .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml
    find . -type d -name __pycache__ -exec rm -rf {} +

# ----------------------------------------------------------------- docker

# Build the Docker image locally as ghcr.io/xavierbeheydt/mcp-kraken:dev.
docker-build TAG="dev":
    docker build -f docker/Dockerfile -t ghcr.io/xavierbeheydt/mcp-kraken:{{TAG}} .

# Run the locally-built image (binds 8765, mounts ./data).
docker-run TAG="dev":
    mkdir -p data
    docker run --rm -it \
        -p 8765:8765 \
        --env-file .env \
        -v $(pwd)/data:/data \
        ghcr.io/xavierbeheydt/mcp-kraken:{{TAG}}

# Bring up the compose stack.
up:
    docker compose up -d

# Tear it down.
down:
    docker compose down

# Tail compose logs.
logs:
    docker compose logs -f --tail=200
