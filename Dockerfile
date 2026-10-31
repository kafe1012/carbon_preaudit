FROM ghcr.io/astral-sh/uv:0.13.6-python3.15-trixie-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml uv.lock .python-version ./
# Workspace member; uv needs its manifest to resolve the lockfile, it is not installed.
COPY tools/pyproject.toml ./tools/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN useradd --system --no-create-home app
USER app

EXPOSE 8000

CMD ["uvicorn", "carbon_preaudit.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
