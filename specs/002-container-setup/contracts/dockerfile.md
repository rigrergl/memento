# Contract: `Dockerfile`

**Location**: repo root (`/Dockerfile`)
**Driven by**: FR-001, FR-002, FR-003; research §R1, §R2, §R3, §R14
**Consumers**: GitHub Actions `publish.yml`, local power-user compose (indirectly via the published image), Cloud Run (deferred).

## Required behaviour

### Stages

The Dockerfile MUST have at least two stages: a builder stage and a runtime stage. The runtime stage MUST NOT include `uv` or build-only OS packages.

### Build steps (builder stage)

1. Base image MUST be `python:3.12-slim` (or compatible CalVer slim variant tied to `requires-python` in `pyproject.toml`).
2. `WORKDIR /app`.
3. Install `uv` in the builder stage (via `pip` or `COPY --from=ghcr.io/astral-sh/uv:latest`).
4. Copy `pyproject.toml` and `uv.lock` to `/app/`.
5. Run `uv sync --frozen --no-install-project --no-dev` to populate `/app/.venv`.
6. Copy `src/` into `/app/src/`.
7. Run a Python invocation that downloads `sentence-transformers/all-MiniLM-L6-v2` to `/app/.cache/models` using the same `SentenceTransformer` loader the runtime uses.

### Build steps (runtime stage)

1. Base image MUST be `python:3.12-slim` (same as builder).
2. `WORKDIR /app`.
3. Install `curl` and `ca-certificates` via `apt-get` (needed for the compose healthcheck).
4. Create a non-root `app` user; `chown` `/app` to it.
5. `COPY --from=builder /app/.venv /app/.venv`.
6. `COPY --from=builder /app/src /app/src`.
7. `COPY --from=builder /app/.cache/models /app/.cache/models`.
8. `COPY --from=builder /app/pyproject.toml /app/pyproject.toml` (so `fastmcp` can find project metadata if needed).
9. `ENV PATH=/app/.venv/bin:$PATH`.
10. `USER app`.
11. `ENTRYPOINT ["fastmcp", "run", "src/mcp/server.py"]`.
12. `CMD []`.

### Image properties

- Final image MUST run as a non-root user.
- Final image MUST contain `/app/.cache/models/<huggingface-cache-layout>/sentence-transformers--all-MiniLM-L6-v2/...` such that `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", cache_folder="/app/.cache/models")` finds the model offline.
- Final image MUST publish a working healthcheck-compatible HTTP listener on whichever `--port` is passed at run time.
- Final image SHOULD be ≤ 500 MB compressed (target; not enforced).

## Test plan

- **Build**: `docker build -t memento:test .` succeeds end-to-end on a fresh machine with no cached layers.
- **Multi-arch build**: `docker buildx build --platform linux/amd64,linux/arm64 -t memento:test .` succeeds.
- **Offline embedding**: `docker run --rm --network none memento:test --transport http --host 0.0.0.0 --port 8000` boots and `ensure_vector_index` runs against a stub Neo4j (in tests, exercised via lifespan unit tests rather than container run).
- **Healthcheck binary present**: `docker run --rm --entrypoint curl memento:test --version` prints curl's version.
- **Non-root**: `docker run --rm --entrypoint id memento:test` reports a non-zero UID.
