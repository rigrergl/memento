# Builder stage: install deps and bake model
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/

RUN .venv/bin/python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='/app/.cache/models')"

# Runtime stage: lean image with non-root user
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --create-home --uid 1001 app && chown app /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/.cache/models /app/.cache/models
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

ENV PATH=/app/.venv/bin:$PATH

USER app

ENTRYPOINT ["fastmcp", "run", "src/mcp/server.py"]
CMD []
