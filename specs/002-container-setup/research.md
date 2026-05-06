# Phase 0 Research: 002-container-setup

**Feature**: Container Setup for Local Power Users + Dev Loop
**Date**: 2026-04-27
**Spec**: [spec.md](./spec.md) · **ADR**: [ADR-007](../../Documentation/ADR/ADR-007-container-setup.md)

## Scope

This phase resolves every "how do we actually do X" question implied by the spec so Phase 1 can produce concrete contracts and Phase 2 can produce ordered tasks. The ADR has already settled the architectural shape (HTTP daemon, single `fastmcp run` entrypoint, baked model, multi-stage Dockerfile, GHCR publish, multi-arch, auto-tag). What remains is selecting concrete commands, versions, and file structures that satisfy each FR/SC.

Each unknown is captured as a **Decision / Rationale / Alternatives** triplet. Where the spec has already pinned a value, the entry is recorded for traceability.

---

## R1. Multi-stage Dockerfile with `uv`

**Decision**: Use the official `ghcr.io/astral-sh/uv` distroless-style approach: a builder stage based on `python:3.12-slim` that runs `uv sync --frozen --no-install-project --no-dev` into `/app/.venv`, then a runtime stage based on the same `python:3.12-slim` that copies `/app/.venv` and the source tree. `WORKDIR /app`. Final image runs as a non-root `app` user. The `uv` CLI itself is **not** copied into the runtime stage — the venv is self-contained.

**Rationale**:
- `uv sync --frozen` (against the committed `uv.lock`) gives reproducible builds without network resolution at build time.
- `--no-install-project --no-dev` separates dependency layers from source code, so source-only edits do not invalidate the dependency-install cache layer.
- `python:3.12-slim` is the smallest official Python tag with libssl/glibc current enough for Neo4j driver's `bolt+s://` and for `sentence-transformers` to import without manual binary patching.
- Runtime stage drops `uv` because `fastmcp` is the entrypoint, not `uv run`. Inside the container, the venv is already activated by setting `PATH=/app/.venv/bin:$PATH`. (Outside the container — i.e. dev — `uv run` is still the entrypoint.)
- Non-root user is best practice and is enforced by Cloud Run regardless.

**Alternatives considered**:
- **Single-stage build**: smaller Dockerfile but ships build tools and `uv` in the runtime image, ~50 MB heavier and a larger attack surface. Rejected.
- **`python:3.12-alpine`**: smaller base, but `sentence-transformers` (via `torch`) ships glibc-linked wheels; alpine forces fallback to building from source, multi-minute builds and a hard dependency on `gcc`/`g++` in the builder. Rejected.
- **Pre-built `astral.sh/uv` base image**: tighter integration but pins us to whatever Python `uv` ships, which lags behind. Rejected — we want explicit Python version control.

**Concrete layer order** (cache-friendly):
1. Set `WORKDIR /app`, install OS deps (`curl`, `ca-certificates`).
2. Install `uv` (builder only) via `pip install --no-cache-dir uv` or `COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv`.
3. Copy `pyproject.toml` and `uv.lock` only.
4. `RUN uv sync --frozen --no-install-project --no-dev`.
5. Copy source (`src/`).
6. Bake the embedding model (R3).
7. Runtime stage: copy `/app/.venv` and `/app/src` and the baked model directory.

---

## R2. Entrypoint and CMD

**Decision**: `ENTRYPOINT ["fastmcp", "run", "src/mcp/server.py"]` and `CMD []`.

**Rationale** (already pinned by ADR-007 §"Single entrypoint" and FR-002):
- Empty `CMD` means each environment supplies the per-environment flags via compose `command:` or Cloud Run `args` without redeclaring the entrypoint binary path.
- `fastmcp run` is the same launcher dev uses with `--reload`, eliminating two divergent entrypoints.

**Alternatives considered**: `CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]` baked in. Rejected because it would force Cloud Run to use `--entrypoint` overrides, which is ergonomically worse and easier to misconfigure.

---

## R3. Baking the embedding model into the image

**Decision**: Add a `RUN` step in the **builder** stage that downloads `sentence-transformers/all-MiniLM-L6-v2` into `/app/.cache/models`, then `COPY --from=builder /app/.cache/models /app/.cache/models` into the runtime stage. The bake step uses the actual loader from the runtime so the on-disk format is byte-identical to what the running server expects.

```dockerfile
RUN .venv/bin/python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='/app/.cache/models')"
```

`Config.embedding_cache_dir` gets a default value of `.cache/models` (relative path). At runtime with `WORKDIR=/app`, that resolves to `/app/.cache/models` — the same directory the bake wrote to. Dev keeps `MEMENTO_EMBEDDING_CACHE_DIR=.cache/models` in `.env.example` so its working tree matches.

**Rationale** (FR-003, SC-003, TD-004 interim):
- Using the actual loader avoids subtle format mismatches (token-cache files, model card metadata, etc.) that arise when fetching with raw `huggingface_hub` calls.
- Defaulting `embedding_cache_dir` lets compose omit the env var entirely. Dev's `.env` retains it for explicitness and because dev's CWD is the repo root, not `/app`.
- Image size cost: ~90 MB (acceptable per ADR-007 §Consequences).

**Alternatives considered**:
- **Named volume cache**: smaller image, but first-run download in compose, plus Cloud Run cold starts pay it on every new instance. Rejected for now (TD-004).
- **Hosted embedding API**: removes the local-model problem but adds API key plumbing and breaks "zero-secrets power user". Out of scope (TD-004).
- **Override-only via env var**: requiring power-user compose to set `MEMENTO_EMBEDDING_CACHE_DIR` to find the baked model. Rejected — couples the compose file to internal layout.

---

## R4. `docker-compose.yml` shape

**Decision**: Single `docker-compose.yml` at repo root with two services: `memento` and `neo4j`. Memento references `ghcr.io/rigrergl/memento:v0.0.2` (initial pinned tag); pin gets bumped per release per FR-011 version-sync policy. Neo4j pinned to `neo4j:2026.03.1` (matches ADR-007 illustrative example and existing README prerequisite).

Key directives, all driven by spec FRs:

```yaml
services:
  memento:
    image: ghcr.io/rigrergl/memento:v0.0.2
    depends_on:
      neo4j:
        condition: service_healthy
    environment:
      MEMENTO_NEO4J_URI: bolt://neo4j:7687
      MEMENTO_NEO4J_USER: neo4j
      MEMENTO_NEO4J_PASSWORD: ${MEMENTO_NEO4J_PASSWORD:?MEMENTO_NEO4J_PASSWORD must be set (copy .env.example to .env and fill it in)}
      MEMENTO_EMBEDDING_PROVIDER: local
      MEMENTO_EMBEDDING_MODEL: sentence-transformers/all-MiniLM-L6-v2
    command: ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
    ports:
      - "127.0.0.1:8000:8000"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/mcp/ || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 30s

  neo4j:
    image: neo4j:2026.03.1
    ports:
      - "127.0.0.1:7687:7687"
      - "127.0.0.1:7474:7474"
    environment:
      NEO4J_AUTH: neo4j/${MEMENTO_NEO4J_PASSWORD:?MEMENTO_NEO4J_PASSWORD must be set (copy .env.example to .env and fill it in)}
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

**Rationale**:
- Bound to `127.0.0.1` per FR-005.
- `condition: service_healthy` waits for Neo4j healthcheck (FR-004).
- Memento healthcheck uses `curl` against the streamable-HTTP path `/mcp/` — FastMCP responds even on `GET` with a JSON error envelope, so a 2xx-or-4xx-but-not-connection-refused signals readiness. `curl -f` treats any 4xx/5xx as failure; 2xx as success. The MCP endpoint returns 200 on `GET` for healthy servers (per FastMCP HTTP transport's default routing), so `-f` is correct.
- `start_period: 30s` covers the lifespan-hook latency (model load + Neo4j vector-index bootstrap), satisfying SC-002's "exempt during start_period" framing.
- `MEMENTO_EMBEDDING_CACHE_DIR` is **not** set in compose — the new default in `Config` resolves to `/app/.cache/models` inside the container, where the model is baked.
- `:latest` is intentionally avoided in compose (FR-011).

**Alternatives considered**:
- Single combined image (Neo4j + Memento): rejected per ADR-007 / R-section research notes (research/mcp-distribution-patterns.md).
- `tini` as `init: true`: deferred — `fastmcp` already handles signal forwarding cleanly and there is no zombie-process risk in this single-process container.

---

## R5. `server.py` refactor: lifespan hook

**Decision**: Use FastMCP's `lifespan` parameter, an async context manager attached to the `FastMCP` instance. Module-level `Config`, embedder, repository, and service become `None` placeholders that the lifespan populates on `__aenter__`. `repository.ensure_vector_index()` is awaited inside the same lifespan, wrapped in `asyncio.to_thread` since the underlying Neo4j driver call is sync.

Sketch:

```python
import asyncio
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from src.utils.config import Config
from src.utils.factory import Factory
from src.graph.neo4j import Neo4jRepository
from src.memory.service import MemoryService

config: Config | None = None
embedder = None
repository: Neo4jRepository | None = None
service: MemoryService | None = None


@asynccontextmanager
async def lifespan(_mcp: FastMCP):
    global config, embedder, repository, service
    config = Config()
    embedder = Factory.create_embedder(config)
    repository = Neo4jRepository(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )
    await asyncio.to_thread(repository.ensure_vector_index)
    service = MemoryService(config=config, embedder=embedder, repository=repository)
    try:
        yield
    finally:
        # Neo4jRepository owns the driver; close it on shutdown.
        await asyncio.to_thread(repository.close)


mcp = FastMCP("Memento", lifespan=lifespan)
```

The `remember` and `recall` tool bodies dereference `service` at call time (it is guaranteed populated by the time FastMCP starts accepting tool calls), preserving the existing test pattern of `patch.object(server_module, "service", mock_service)`.

**Rationale** (FR-006, FR-006c, SC-005):
- A bare `import src.mcp.server` no longer instantiates `Config`, the embedder, or the Neo4j driver. Test fixtures that previously needed to patch `SentenceTransformer` and `GraphDatabase` *just to import the module* (see `tests/test_mcp/conftest.py`) will continue working but become unnecessary for tests that only exercise tool wiring; the conftest is left in place to avoid churn.
- `ensure_vector_index` runs unconditionally on every `mcp.run()` invocation — including dev `--reload`, fixing the ADR-007-noted latent bug.
- `await asyncio.to_thread(...)` keeps the Neo4j sync API ergonomic without requiring a Neo4j async driver migration.
- Module-level globals (rather than passing service through `mcp.dependencies`) preserve the `patch.object(server_module, "service", ...)` test contract used by 11 existing tests in `tests/test_mcp/test_server.py`.

**Alternatives considered**:
- **`Neo4jRepository.ensure_vector_index_async`**: cleaner than `to_thread` but requires migrating the Neo4j driver call to async, which is out of scope. Rejected.
- **Dependency injection via `Context`**: each tool would receive its `service` via a FastMCP context object. More idiomatic, but every existing test would need rewriting. Rejected on YAGNI/test-churn grounds.
- **Lifespan returning a context dict**: returning `{"service": ...}` from the async generator is the FastMCP-recommended way for lifespan-managed resources. Rejected only because it would break the existing `patch.object(server_module, "service", ...)` test surface. We can revisit in a later spec without changing public behaviour.

---

## R6. Removing `MEMENTO_TRANSPORT`, `MEMENTO_MCP_HOST`, `MEMENTO_MCP_PORT`

**Decision**: Delete `mcp_host` and `mcp_port` fields from `Config` (TD-003 resolution per FR-007). Remove `MEMENTO_TRANSPORT` references entirely (none currently exist in code; this is a forward-looking guard against re-adding it). Update `.env.example` to drop these vars. Update `tests/test_mcp/conftest.py` to drop the corresponding `os.environ.setdefault` lines (none currently set those, so this is mostly the verification step).

**Rationale**: Single source of truth for transport/host/port is the per-environment CLI flag. Spec FR-007.

**Alternatives considered**: keep them as optional with `None` defaults — rejected, dead code violates KISS.

---

## R7. `.mcp.json` for dev loop

**Decision**: Commit `.mcp.json` at repo root with two MCP servers wired:

```json
{
  "mcpServers": {
    "memento": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "src/mcp/server.py", "--reload"]
    },
    "neo4j-cypher": {
      "command": "uvx",
      "args": ["mcp-neo4j-cypher"],
      "env": {
        "NEO4J_URI": "${MEMENTO_NEO4J_URI}",
        "NEO4J_USERNAME": "${MEMENTO_NEO4J_USER}",
        "NEO4J_PASSWORD": "${MEMENTO_NEO4J_PASSWORD}"
      }
    }
  }
}
```

**Rationale** (FR-009, ADR-007 §"MCP configuration as repo files"):
- `${VAR}` substitution is performed by Claude Code and Gemini CLI (the two clients in scope for dev) from the launching shell environment.
- Dev exports the `MEMENTO_NEO4J_*` vars (e.g. via `set -a; source .env; set +a` or `direnv`) before launching the client. The `.mcp.json` file does not include literal credentials.
- `mcp-neo4j-cypher` is the upstream Neo4j Labs MCP — the dev queries the live Neo4j via this server to self-validate Memento mutations.

**Alternatives considered**:
- Putting `${MEMENTO_NEO4J_PASSWORD}` literally in the file with no env-substitution layer: only works if the user manually edits values, which defeats the goal. Rejected.
- Splitting into `mcp.json.example` + a generation step: extra friction. Rejected — `.mcp.json` is already a published interoperability format.

---

## R8. `.env.example` shape (post-cleanup)

**Decision**: Trim TD-003 vars, leave `MEMENTO_NEO4J_PASSWORD` blank (placeholder only — no committed credential), and add comments explaining the cache-dir default. Final shape:

```bash
# Neo4j connection (Local default)
MEMENTO_NEO4J_URI=bolt://localhost:7687
MEMENTO_NEO4J_USER=neo4j
# Set a password of your choice (Neo4j requires a minimum of 8 characters).
MEMENTO_NEO4J_PASSWORD=

# Embedding (local sentence-transformers; no API costs)
MEMENTO_EMBEDDING_PROVIDER=local
MEMENTO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MEMENTO_EMBEDDING_CACHE_DIR=.cache/models

# Memory validation
MEMENTO_MAX_MEMORY_LENGTH=4000
```

**Rationale**: Same as today minus dead vars. `MEMENTO_EMBEDDING_CACHE_DIR` stays in dev because dev's CWD is repo root (not `/app`), and committing the dev value explicitly makes it less surprising than relying on the new `Config` default. FR-010. The password is intentionally left blank: shipping a hard-coded default normalises a credential identical across every deployment and trains users not to think about secrets — `cp .env.example .env` plus picking a password is a clear signal that this is a real database with a real credential.

---

## R9. GitHub Actions: `publish.yml` (Docker build + GHCR push)

**Decision**: Add `.github/workflows/publish.yml` triggered on `push` of tags matching `v*.*.*`. Steps:

1. `actions/checkout@v5`
2. `docker/setup-qemu-action@v3`
3. `docker/setup-buildx-action@v3`
4. `docker/login-action@v3` against `ghcr.io` using `${{ secrets.GITHUB_TOKEN }}` (no PAT required because the workflow runs in the same repo).
5. `docker/metadata-action@v5` to derive image tags from the git tag (`v0.0.2` → `0.0.2` and `v0.0.2`; no `latest`).
6. `docker/build-push-action@v6` with `platforms: linux/amd64,linux/arm64`, `push: true`, `cache-from: type=gha`, `cache-to: type=gha,mode=max`.

Workflow needs `permissions: contents: read, packages: write` at the job level.

**Rationale** (FR-011):
- Tag-only trigger means a push to `main` does not publish an image; `auto-tag.yml` (R10) is the gate that promotes a version bump to a release.
- Multi-arch via QEMU: ARM64 build is emulated, ~3× slower than AMD64 native, but builds in <8 min for our ~200 MB image — acceptable per release frequency (manual, low single-digit per month).
- `metadata-action` deduplicates the version-stripping logic.
- GHA cache (`type=gha`) is free and tied to repo storage limits.

**Alternatives considered**:
- **Self-hosted ARM runner**: avoids QEMU emulation but adds infra. Rejected — emulation is fast enough.
- **Separate amd64 / arm64 build jobs + manifest merge**: faster wall-clock but adds a third job and a merge step. Deferred until release frequency justifies it.
- **Push `latest` tag too**: explicitly forbidden by FR-011.

---

## R10. GitHub Actions: `auto-tag.yml`

**Decision**: Add `.github/workflows/auto-tag.yml` triggered on `push` to `main`. Steps:

1. `actions/checkout@v5` with `fetch-depth: 0` and `token: ${{ secrets.GITHUB_TOKEN }}`.
2. Read version from `pyproject.toml` (e.g. via `grep -E '^version = ' pyproject.toml | sed -E 's/.*"(.*)"/\1/'`).
3. If `git rev-parse "v$VERSION"` succeeds, exit 0 (already tagged).
4. Else, configure git as `github-actions[bot]`, create annotated tag `v$VERSION`, and `git push origin "v$VERSION"`.

Workflow needs `permissions: contents: write` at the job level so it can push a tag back.

**Rationale** (FR-011 §Auto-tagging):
- Tag push triggers `publish.yml` automatically — no manual step between merging a version bump and an image being published.
- Idempotent: re-running on the same commit (e.g. on a re-run) is a no-op.
- Annotated tag (`-a`) carries the commit SHA and message, useful for release notes.

**Alternatives considered**:
- **Trigger publish on `push` to `main` directly**: bypasses semver pinning. Rejected per spec — releases must be explicit.
- **Manual tag push by maintainer**: works but adds a manual step that's easy to forget after merging the PR. Rejected per spec.
- **release-please or semantic-release**: full-fledged release automation tools. Rejected on YAGNI — we only need "create tag from `pyproject.toml` version".

---

## R11. GHCR visibility (one-time bootstrap)

**Decision**: Document in README and the spec's bootstrap section that after the first successful `publish.yml` run, the maintainer must navigate to `https://github.com/users/rigrergl/packages/container/memento/settings` and set the package visibility to **Public**. This is a one-time step.

**Rationale** (FR-011 §GHCR visibility): GitHub defaults new container packages to private. Without this step, `docker compose pull` fails for unauthenticated power users with `denied: requested access to the resource is denied`.

**Alternatives considered**:
- **Automate via `gh api`**: GitHub does not currently expose package visibility via the REST or GraphQL API for personal-account containers. Rejected — not technically possible at this time.
- **Use Docker Hub instead**: adds a second registry to manage. Rejected.

---

## R12. Bootstrap sequence for the first image

**Decision**: Per spec FR-011 §Bootstrap, the implementation PR sets `image: ghcr.io/rigrergl/memento:v0.0.2` even though no such image exists yet. After merging:

1. The merge to `main` triggers `auto-tag.yml` (R10), which creates and pushes `v0.0.2`.
2. The tag push triggers `publish.yml` (R9), which builds and pushes `ghcr.io/rigrergl/memento:v0.0.2` and `:0.0.2`.
3. Maintainer sets the package to Public (R11).

`main` is transiently broken (`docker compose pull` fails) for ~10–15 minutes between (1) and (3). The PR description and the README should call this window out.

**Rationale**: Selected option in spec clarification §2026-04-27 Q2. The other options each require either (a) committing a placeholder broken tag, or (b) decoupling tag creation from the merge, both worse.

---

## R13. `pyproject.toml` version-sync policy enforcement

**Decision**: Document the policy in README's Release section: any PR that bumps `[project] version` in `pyproject.toml` must also bump the pinned `image:` tag in `docker-compose.yml` in the same commit. No CI enforcement in this spec — manual review is sufficient at our release cadence.

**Rationale** (FR-011 §Version sync policy): Mismatched versions would mean `docker compose pull` fetches an old image even after a release. Catching this in code review is cheap; CI enforcement is over-engineering for our cadence.

**Alternatives considered**:
- **Pre-commit hook that grep-compares the two files**: fragile (regex on YAML/TOML is brittle). Deferred until we get burned by it.
- **Auto-bumper that updates compose from `pyproject.toml`**: deferred — adds a second moving part.

---

## R14. Memento healthcheck command

**Decision**: `["CMD-SHELL", "curl -f http://localhost:8000/mcp/ || exit 1"]` (FR-004).

This requires `curl` to be present in the runtime image. `python:3.12-slim` does not include `curl` by default.

**Sub-decision**: Add `curl` (and `ca-certificates`) to the runtime stage's `apt-get install`:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

This adds ~5 MB to the runtime image. Acceptable.

**Rationale**: FR-004 explicitly mandates this healthcheck command. Using `python -c "urllib.request.urlopen('http://localhost:8000/mcp/')"` would avoid the dependency but is wordier and less debuggable when shelling into the container.

**Alternatives considered**:
- **`wget` instead**: not installed in slim either, similar size cost. Equivalent.
- **TCP-only check via `nc`**: cheaper but does not exercise the MCP route handler — a port-bound process that's deadlocked in lifespan would still pass. Rejected.

---

## R15. README updates and MCP client config blocks

**Decision**: README's existing "Quick Start" section is restructured into two top-level sections:

1. **Power-User Setup** (new, primary): `git clone` → `docker compose up -d` → MCP client config (native HTTP block first, two bridge fallback blocks).
2. **Developer Setup** (replaces existing Quick Start): `uv sync`, `cp .env.example .env`, `docker compose up neo4j`, then either `uv run fastmcp run src/mcp/server.py --reload` directly or via `.mcp.json` from a launched MCP client.

The `python -m src.mcp.server` reference in the existing README is removed (the entrypoint no longer exists per FR-006).

**Rationale** (FR-013, FR-012):
- Power-user is the new primary entry point — it must come first.
- Both MCP-client config flavours (native HTTP, `mcp-remote` bridge, `mcp-proxy` bridge) are documented per FR-012, with native HTTP as the recommended path.

**Alternatives considered**: separate `INSTALL.md` for power users — rejected, README is canonical.

---

## R16. `Documentation/known-tech-debt.md` updates

**Decision** (FR-008):

- **TD-003**: change Status to "Resolved by ADR-007 / spec 002-container-setup — `Config.mcp_host` and `Config.mcp_port` deleted; transport/host/port now CLI flags. Power-user compose binds `127.0.0.1:8000`, so the LAN exposure historical risk is closed." Keep the Context/Risk for archival traceability but mark them historical.
- **TD-004**: add a "Status update (2026-04-27)" subsection noting that spec 002-container-setup chose option 1 (bake into image) as an interim resolution, and the longer-term volume-vs-API decision remains open.

**Rationale**: Spec FR-008 mandates these updates; they keep the tech-debt ledger truthful.

---

## Open questions resolved by this research

| Question | Resolution |
|---|---|
| Do we need a `tini` init? | No — single-process container, FastMCP handles SIGTERM cleanly. |
| Healthcheck endpoint? | `GET /mcp/` (R14). |
| How to bake the model? | In the builder stage via `SentenceTransformer(...)`; copy directory to runtime stage (R3). |
| What `Config.embedding_cache_dir` default? | `.cache/models` — matches existing `.env.example` and resolves correctly inside the container (R3). |
| Does the power-user compose need to set `MEMENTO_EMBEDDING_CACHE_DIR`? | No — the new default + bake path align (R4). |
| Lifespan API shape? | `lifespan=async_context_manager` passed to `FastMCP(...)`, populating module-level globals (R5). |
| `ensure_vector_index` async? | Wrapped in `asyncio.to_thread` (R5). |
| Multi-arch build mechanism? | QEMU + buildx + `docker/build-push-action` (R9). |
| Tag trigger for publish? | Tag push of `v*.*.*` only; `auto-tag.yml` creates the tag from `pyproject.toml` on `main` (R9, R10). |

## Out-of-scope / deferred to later specs

- **Cloud Run deployment** (Terraform, Artifact Registry mirroring, GCP Secret Manager, Auth0). Tracked: Cloud Run spec (TBD).
- **Dev-loop autonomous iteration / Claude YOLO mode VM provisioning**. Tracked: separate dev-loop spec (TBD).
- **TD-001** structured exception logging.
- **TD-002** vector-index similarity-metric migration.
- **TD-004** longer-term embedding distribution decision.

## References

- Internal: [ADR-007](../../Documentation/ADR/ADR-007-container-setup.md), [research/mcp-distribution-patterns.md](./research/mcp-distribution-patterns.md), [Documentation/known-tech-debt.md](../../Documentation/known-tech-debt.md).
- External (verified online during this phase, see spec.md guidance on time-sensitive info):
  - FastMCP `lifespan` parameter — github.com/jlowin/fastmcp.
  - `docker/build-push-action` multi-arch — docs.docker.com/build/ci/github-actions/multi-platform.
  - GHCR package visibility — docs.github.com/en/packages.
  - `astral.sh/uv` Docker integration — docs.astral.sh/uv/guides/integration/docker.
