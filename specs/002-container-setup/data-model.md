# Phase 1 Data Model: 002-container-setup

**Feature**: Container Setup for Local Power Users + Dev Loop
**Date**: 2026-04-27

This feature is primarily infrastructure and packaging; it does not introduce new domain entities (Memory, User, etc. remain unchanged from `001-baseline-rag`). Two configuration-level "entities" do exist — both already named in spec.md §"Key Entities" — and are described here as a conceptual data model so contracts can reference them by name.

---

## Entity 1: Container Image

The immutable artifact published to GHCR per release. One image serves all environments; per-environment behaviour comes from CLI flags and env vars at run time.

### Fields

| Field | Type | Source | Notes |
|---|---|---|---|
| `repository` | string | `ghcr.io/rigrergl/memento` | Hardcoded in `docker-compose.yml`; matches GHCR namespace from repo owner. |
| `tag` | string (semver, e.g. `v0.0.2`) | `pyproject.toml` `[project] version` (with leading `v`) | Pinned in compose; bumped per release. `latest` is forbidden (FR-011). |
| `architectures` | `[linux/amd64, linux/arm64]` | `docker/build-push-action` `platforms` | Multi-arch manifest (FR-011 §Multi-arch). |
| `entrypoint` | `["fastmcp", "run", "src/mcp/server.py"]` | Dockerfile | Per FR-002. |
| `cmd` | `[]` | Dockerfile | Empty by design — flags supplied per environment (FR-002). |
| `workdir` | `/app` | Dockerfile | All relative paths in the running container resolve here. |
| `baked_model_path` | `/app/.cache/models` | Builder-stage `RUN` (R3) | Holds `sentence-transformers/all-MiniLM-L6-v2`. Resolves from `Config.embedding_cache_dir` default. |
| `runtime_user` | non-root `app` user | Dockerfile | Cloud Run + best-practice. |
| `python_version` | `3.12` (slim variant) | Dockerfile base image | Matches `pyproject.toml` `requires-python`. |

### Lifecycle / state transitions

```
[source change] → PR opened
[PR merged] → push to main
[push to main] → auto-tag.yml
   (if pyproject.toml version is new and matching git tag absent)
   → push annotated tag vX.Y.Z
[tag push] → publish.yml
   → docker buildx build --platform linux/amd64,linux/arm64 --push
   → image published at ghcr.io/rigrergl/memento:vX.Y.Z and :X.Y.Z
[manual one-time] → maintainer sets package visibility = Public
[user upgrade] → git pull && docker compose pull && docker compose up -d
```

The image is **immutable** — once published, a tag is never re-pushed. Yanking a release is done by bumping `pyproject.toml` again with a fixed version, not by overwriting.

### Validation rules

- `tag` MUST equal `v` + the value of `[project] version` in the same commit's `pyproject.toml` (manual review per R13).
- `tag` referenced in committed `docker-compose.yml` MUST equal the latest published `tag`, except during the bootstrap window described in FR-011 §Bootstrap.
- Image MUST contain the baked embedding model at `/app/.cache/models` (verified by R3 build step).
- Image MUST run as non-root.
- Image MUST be pullable without authentication once GHCR visibility is Public (FR-011).

---

## Entity 2: Deployment Configuration

A composite of environment variables + CLI flags + ports that differentiates the three target environments (Dev, Local power user, Cloud Run). This entity is conceptual — there is no single config file that captures all of it; it is split across `.env`, `docker-compose.yml`, `.mcp.json`, and (in a future spec) Terraform.

### Fields per environment

| Field | Dev (VM) | Local power user (compose) | Cloud Run (deferred) |
|---|---|---|---|
| `MEMENTO_NEO4J_URI` | `bolt://localhost:7687` (`.env`) | `bolt://neo4j:7687` (compose env block) | Aura URI (Cloud Run env var) |
| `MEMENTO_NEO4J_USER` | `neo4j` (`.env`) | `neo4j` (compose env block) | env var |
| `MEMENTO_NEO4J_PASSWORD` | user-supplied (`.env`; `.env.example` ships blank) | `${MEMENTO_NEO4J_PASSWORD}` interpolated by compose, no fallback default | Secret Manager → env var |
| `MEMENTO_EMBEDDING_PROVIDER` | `local` (`.env`) | `local` (compose env block) | TBD per Cloud spec |
| `MEMENTO_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` (`.env`) | same (compose env block) | same |
| `MEMENTO_EMBEDDING_CACHE_DIR` | `.cache/models` (`.env`) | unset (uses `Config` default `.cache/models` → `/app/.cache/models`) | unset |
| `MEMENTO_MAX_MEMORY_LENGTH` | `4000` (`.env` default) | unset (uses `Config` default) | unset |
| Transport CLI flag | `--reload` (no transport flag = stdio default) | `--transport http` | `--transport http` |
| Host CLI flag | n/a (stdio) | `--host 0.0.0.0` | `--host 0.0.0.0` |
| Port CLI flag | n/a (stdio) | `--port 8000` | `--port 8080` |
| Host port binding | n/a | `127.0.0.1:8000:8000` | n/a (Cloud Run handles ingress) |
| `Config.mcp_host` | **removed** (FR-007) | **removed** | **removed** |
| `Config.mcp_port` | **removed** (FR-007) | **removed** | **removed** |
| `MEMENTO_TRANSPORT` env var | **removed** (FR-007) | **removed** | **removed** |

### Validation rules

- All three Neo4j vars (`MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, `MEMENTO_NEO4J_PASSWORD`) MUST be present at server startup; `Config()` raises `ValidationError` otherwise (existing behaviour, preserved).
- All three embedding vars (`MEMENTO_EMBEDDING_PROVIDER`, `MEMENTO_EMBEDDING_MODEL`, `MEMENTO_EMBEDDING_CACHE_DIR`) MUST be present **OR** rely on `Config` defaults. Per R3, `embedding_cache_dir` gains a default of `.cache/models`. The provider and model fields remain required (no sensible default for "which model do you want").
- Transport, host, port MUST be passed as CLI flags. There MUST be no fallback to env vars or `Config` fields for these (FR-007).
- The local power-user compose MUST bind ports to `127.0.0.1` (FR-005).

---

## Affected source files (delta from current state)

| File | Change | Driven by |
|---|---|---|
| `src/mcp/server.py` | Refactor: delete `__main__`; introduce `lifespan` async context manager; module-level globals become `None` placeholders. | FR-006, R5 |
| `src/utils/config.py` | Delete `mcp_host`, `mcp_port` fields. Add default `.cache/models` for `embedding_cache_dir`. | FR-007, FR-003, R3, R6 |
| `.env.example` | (No new vars. Reaffirms current contents minus any future references to removed vars.) | FR-010, R8 |
| `Dockerfile` | **New.** Multi-stage build per R1, R3, R14. | FR-001, FR-002, FR-003 |
| `docker-compose.yml` | **New** (at repo root). Per R4. | FR-004, FR-005 |
| `.mcp.json` | **New** (at repo root). Per R7. | FR-009 |
| `.dockerignore` | **New.** Excludes `.git`, `.venv`, `tests/`, `specs/`, `Documentation/`, `.cache/` (so the host's downloaded model is not double-baked over the builder's). | R1 build context hygiene |
| `.github/workflows/publish.yml` | **New.** Tag-triggered multi-arch build + push to GHCR. | FR-011, R9 |
| `.github/workflows/auto-tag.yml` | **New.** `main`-triggered git tag creation from `pyproject.toml` version. | FR-011 §Auto-tagging, R10 |
| `Documentation/known-tech-debt.md` | Update TD-003 to "Resolved"; update TD-004 with interim-resolution note. | FR-008, R16 |
| `README.md` | Restructure into Power-User + Developer sections; remove `python -m src.mcp.server` reference; add MCP client config blocks. | FR-012, FR-013, R15 |
| `tests/test_mcp/conftest.py` | Verify still works after refactor; remove dead env-var setdefaults if any (none currently for `MEMENTO_TRANSPORT`/`MEMENTO_MCP_HOST`/`MEMENTO_MCP_PORT`). | FR-006, FR-007 |
| `.devcontainer/` | **Deleted** (per ADR-007 §"Development environment: VM replaces devcontainer"; out-of-scope for this spec but the README references to dev-container forwarding need to be removed alongside the README rewrite). | R15 cleanup |

`Memory`, `User`, embedding interfaces, `Neo4jRepository`, `MemoryService` are **unchanged** by this spec.

---

## Test surface delta

| Test file | Change |
|---|---|
| `tests/test_mcp/test_server.py` | Existing 16 tests continue using `patch.object(server_module, "service", ...)`. Add new tests: lifespan populates globals; bare import does not call `Neo4jRepository(...)`; bare import does not call `SentenceTransformer(...)`; lifespan calls `ensure_vector_index`. |
| `tests/test_mcp/conftest.py` | Patching of `SentenceTransformer` and `GraphDatabase` becomes belt-and-suspenders (no longer triggered by import after R5) but stays for safety; document why. |
| `tests/test_utils/test_config.py` | Delete tests for `mcp_host`/`mcp_port` fields (none exist today; the cleanup is a verification step). Add a test for the new `embedding_cache_dir` default (`Config(embedding_provider=..., embedding_model=..., neo4j_*=...)` succeeds without an explicit `embedding_cache_dir`). |
| New: `tests/test_mcp/test_lifespan.py` | New file or new section in `test_server.py` for lifespan-specific behaviour. |
