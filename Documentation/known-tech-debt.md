# Known Technical Debt

Items deferred from feature implementation intentionally. Each entry includes the risk level, the trigger condition for remediation, and the affected locations.

**Priority field** (added by 003-container-polish-devloop): `high` = address before the next feature PR or publish cycle; `low` = address when a concrete pain point arises.

---

## TD-007 — Multi-arch (`linux/arm64`) Docker build under QEMU is untested

**Feature**: 003-container-polish-devloop
**Severity**: Medium — first publish failure would leave arm64 users with a broken image
**Status**: Deferred — no publish has run yet; flagged as known-unknown

### Priority

high

### Context

`publish.yml` builds for `linux/arm64` via QEMU emulation. The Dockerfile bakes `sentence-transformers/all-MiniLM-L6-v2` during the build stage, which means the model download + Python import happens under QEMU. This can take 5–10× longer than native and has been known to exceed GHA `ubuntu-latest` job timeout windows. No data exists yet because the workflow has never run with this Dockerfile shape.

### Risk

- **If QEMU build times out**: The arm64 image leg fails; only `amd64` ships; Apple Silicon and similar users get the wrong image or a pull error.

### Affected locations

- `.github/workflows/publish.yml` — `build-push-action` matrix

### Remediation (before next publish cycle)

Run `docker buildx build --platform linux/arm64 .` locally (using QEMU via `docker buildx`) to confirm the build completes within a reasonable window. If it times out: split the matrix to use native arm64 GHA runners, or move the model-bake step to a `--platform=$BUILDPLATFORM` stage so it executes on the native host.

---

## TD-008 — `auto-tag.yml` has a TOCTOU race on concurrent merges to `main`

**Feature**: 003-container-polish-devloop
**Severity**: Medium — loud and recoverable; not silent data loss
**Status**: Deferred — advisory; low-cadence release schedule makes collision unlikely

### Priority

high

### Context

`auto-tag.yml` checks whether a tag already exists (`git rev-parse`) and then pushes. With `cancel-in-progress: false`, two PRs merging to `main` in quick succession can both pass the check before either pushes; the second `git push origin v$VERSION` fails loudly (non-fast-forward or tag-already-exists). Failure mode is recoverable by re-running the failed workflow run.

### Risk

- **Current**: Low probability (single-digit releases per month).
- **If release cadence increases**: Race becomes more likely; re-runs become a routine nuisance.

### Affected locations

- `.github/workflows/auto-tag.yml`

### Remediation: N/A — advisory-only

Add a comment to the workflow noting the low-cadence assumption and how to recover (re-run the failed publish workflow). Structural fix (atomic tag-then-push or a lock mechanism) is appropriate only if release cadence rises.

---

## TD-001 — Unstructured exception logging in MCP tool error handlers

**Feature**: 001-baseline-rag
**Severity**: Low (current deployment); Medium (before public/multi-tenant release)
**Status**: Deferred — single-tenant, trusted-user deployment

### Priority

low

### Context

Both MCP tool handlers (`remember`, `recall`) use a bare `except Exception` catch-all that returns a fixed generic string to the client:

```python
except Exception:
    return "Failed to store/search memories: unexpected error. Please try again."
```

The raw exception is intentionally **not** forwarded to the MCP client (preventing leakage of connection URIs, credentials, or file-system paths). However, the exception is also not currently forwarded to any structured log sink — it is silently swallowed.

### Risk

- **Leakage risk (current)**: None — the client receives no internal detail.
- **Observability risk (current)**: Errors from the Neo4j driver (e.g. `ServiceUnavailable`) or the embedding provider (e.g. model load failure) produce no log output, making silent failures hard to diagnose.
- **Leakage risk (if naively adding logging)**: If `str(e)` is logged to an external sink without scrubbing, it can expose Neo4j connection URIs with embedded credentials or internal host names.

### Affected locations

- `src/mcp/server.py` — `remember` tool catch-all handler
- `src/mcp/server.py` — `recall` tool catch-all handler
- `specs/001-baseline-rag/contracts/remember-tool.md`
- `specs/001-baseline-rag/contracts/recall-tool.md`

### Remediation (before productionisation)

1. Add structured logging (e.g. `structlog` or stdlib `logging`) to the service and/or MCP layers.
2. Catch specific known exception types first (`neo4j.exceptions.ServiceUnavailable`, `neo4j.exceptions.AuthError`, `RuntimeError` for embedding failures) and log them at `ERROR` level with a scrubbed message — **never** log the raw Neo4j URI.
3. Let the final `except Exception` log at `ERROR` with `exc_info=True` (stack trace only, no URI) and return the same fixed string to the client.
4. Add a credential-scrubbing utility if connection strings are configured via URI rather than discrete host/user/password fields.

---

## TD-002 — Vector index similarity metric is fixed at creation time

**Feature**: 001-baseline-rag
**Severity**: Low (current deployment); Medium (if embedding model or retrieval strategy changes)
**Status**: Deferred — cosine similarity is correct for text embeddings; no use case for changing it yet

### Priority

low

### Context

Neo4j bakes the similarity function (`cosine`, `euclidean`) into the vector index at creation time via the `vector.similarity_function` index config option. There is no ALTER INDEX support for changing this value — the only path is dropping the index and recreating it, which requires re-embedding all stored Memory nodes.

The current implementation hardcodes cosine similarity in `Neo4jRepository.ensure_vector_index`. This is intentional and correct for the `all-MiniLM-L6-v2` model, but it means any future change to the similarity metric is a migration, not a config change.

### Risk

- **Functional risk (current)**: None — cosine is the correct metric for sentence embedding similarity.
- **Migration risk (future)**: If a new embedding model is adopted that benefits from a different metric (e.g., dot-product for normalized vectors), the vector index must be dropped and rebuilt. All stored memories must be re-embedded if the model also changes.
- **Operational risk**: A developer changing a config value expecting it to take effect will see no change — there is no config value to change, and no runtime error will surface.

### Affected locations

- `src/graph/neo4j.py` — `ensure_vector_index` method
- `specs/001-baseline-rag/data-model.md` — vector index definition

### Remediation (when similarity metric needs to change)

1. Add a migration script that reads all Memory nodes, drops the existing vector index, recreates it with the new similarity function, and re-indexes embeddings.
2. If the embedding model also changes, re-embed all content fields using the new provider before re-indexing.
3. Consider making the index name configurable so multiple indexes (one per metric/model combination) can coexist during a migration window.

---

## TD-003 — MCP server host defaults to `0.0.0.0`

**Feature**: ADR-007 container setup
**Severity**: Medium (any local deployment on a shared network)
**Status**: Resolved by ADR-007 / spec 002-container-setup — `Config.mcp_host` and `Config.mcp_port` deleted; transport/host/port now CLI flags; local power-user compose binds `127.0.0.1:8000`.

### Priority

low

### Context

`Config.mcp_host` defaults to `0.0.0.0`, which binds the HTTP server to all interfaces. On shared networks (café Wi-Fi, office LAN), this exposes the Memento server to other machines on the same network. The safe default for local deployments is `127.0.0.1` (loopback-only). Cloud Run legitimately requires `0.0.0.0` since its traffic router connects to the container over the network.

### Risk (historical — resolved by ADR-007)

- **Local/power-user risk**: If a user accidentally ran the server over HTTP locally, it was reachable from the LAN. No longer applicable: the power-user compose binds the published port to `127.0.0.1:8000`, so the LAN cannot reach it even though Memento listens on `0.0.0.0` inside the container.
- **Cloud Run**: No risk — `0.0.0.0` is required and intentional there, now passed explicitly via `--host 0.0.0.0`.
- **Dev (stdio)**: No risk — the dev loop uses stdio transport via `uv run fastmcp run --reload`; host binding is irrelevant.

### Affected locations

- `src/utils/config.py` — `mcp_host` field default value (to be deleted per ADR-007)

### Remediation

Implement ADR-007: remove `mcp_host` and `mcp_port` fields from `src/utils/config.py` and delete any remaining references in the application code. Transport, host, and port are now handled as CLI flags by the `fastmcp` launcher.

---

## TD-004 — Embedding model distribution and caching strategy is unresolved

**Feature**: ADR-007 container setup
**Severity**: Low (dev); Medium (power-user container UX)
**Status**: Deferred — decision intentionally postponed until embedding strategy is finalised

### Priority

low

### Context

Memento currently uses `sentence-transformers/all-MiniLM-L6-v2`, downloaded on first use to `MEMENTO_EMBEDDING_CACHE_DIR` (~90 MB). In the power-user container setup described in ADR-007, each MCP client invocation creates a fresh container via `docker compose run --rm memento`. Without a persistence strategy, the model is re-downloaded on every spawn, producing multi-second cold starts and, eventually, a broken setup if the model is ever pulled from Hugging Face.

Three broad options exist, none of which this project is ready to commit to:

1. **Bake the model into the Docker image** at build time — simple, offline-capable, but inflates the image by ~100 MB and couples image rebuilds to model changes.
2. **Mount a named volume** at the cache dir — keeps the image small, but adds a first-run download and a second volume to manage.
3. **Switch to a hosted embedding API** (Voyage, OpenAI, Cohere, etc.) — removes the local-model problem entirely, but introduces a new external dependency, cost, and latency profile, and breaks the "zero API keys for power users" story.

### Risk

- **Current dev risk**: None — dev runs on the VM with a persistent filesystem, model is cached once.
- **Power-user risk (if ADR-007 ships as-is)**: Every MCP client spawn re-downloads ~90 MB. First-time UX is slow; offline use is broken; a model taken down upstream silently breaks existing installs.
- **Cloud Run risk**: Cold starts pay the full model download on every new instance unless the model is baked into the image.

### Affected locations

- `src/embeddings/local_embedding_provider.py`
- Dockerfile (not yet written — ADR-007)
- `docker-compose.yml` (not yet written — ADR-007)
- `Documentation/ADR/ADR-007-container-setup.md` — Dockerfile Strategy section

### Status update (2026-04-27)

002-container-setup chose option 1 (bake into image) as the interim resolution: the published Docker image bakes `sentence-transformers/all-MiniLM-L6-v2` to `/app/.cache/models` at build time, giving offline capability and eliminating cold-start downloads for power users. The longer-term decision between continued image-baking, volume-mounting, or switching to a hosted embedding API remains open and is not blocked by this feature.

### Remediation (before productionising power-user distribution)

1. Decide whether Memento continues to bundle a local embedding model at all, or moves to a hosted API for personal-scale deployments.
2. If local: re-evaluate image-baking vs. volume-mounting as model size grows or if model changes become frequent.
3. If hosted: design the provider abstraction for API-key management, add a new `IEmbeddingProvider` implementation, and update the cloud and power-user credential flows to include the API key as a secret.
4. Ensure Cloud Run cold-start behaviour is acceptable under whichever option is chosen.

---

## TD-005 — `Neo4jRepository.close` is not idempotent

**Feature**: 003-container-polish-devloop
**Severity**: Low — current Neo4j Python driver tolerates double-close; contract gap only
**Status**: Deferred — not a runtime bug today; deferred per spec clarification C1–C3

### Priority

low

### Context

`Neo4jRepository.close()` calls `self._driver.close()` unconditionally with no guard against a second call. The current driver tolerates this, but the contract is unmet and a future driver upgrade or a test that double-enters/exits the lifespan will surface the issue.

### Risk

- **Current**: None — driver silently accepts a second close.
- **Future**: A driver upgrade that raises on double-close will cause test failures or silent lifespan errors.

### Affected locations

- `src/graph/neo4j.py` — `close` method

### Remediation (when double-close occurs in tests or after driver upgrade)

Add a `_closed: bool = False` flag; short-circuit `close()` if already closed.

---

## TD-006 — `_get_tool_fn` helper spins up a new event loop per call

**Feature**: 003-container-polish-devloop
**Severity**: Low — functional; negligible overhead in current test count
**Status**: Deferred — no concrete pain point yet

### Priority

low

### Context

`tests/test_mcp/test_server.py` defines `_get_tool_fn` which calls `asyncio.run(mcp.get_tool(tool_name))`. Each call pays the cost of a fresh event loop. Additionally, `asyncio.run` raises if called inside an already-running loop, which will surface if tests are ever migrated to async.

### Risk

- **Current**: None — sync tests, small test count.
- **Future**: Refactoring to `pytest-asyncio` style will require replacing this helper.

### Affected locations

- `tests/test_mcp/test_server.py` — `_get_tool_fn` helper

### Remediation (when test suite is migrated to pytest-asyncio or helper causes slowness)

Replace `_get_tool_fn` with a module-level fixture that resolves both tool functions once and yields them, or use `await mcp.get_tool(...)` directly in async tests.

---

## TD-009 — `asyncio.to_thread` is patched at the global `asyncio` module level in tests

**Feature**: 003-container-polish-devloop
**Severity**: Low — stylistic; no behaviour difference
**Status**: Deferred

### Priority

low

### Context

`tests/test_mcp/test_lifespan.py` uses `patch("asyncio.to_thread", ...)` which patches the attribute on the shared `asyncio` package object. The idiomatic, narrower form is `patch("src.mcp.server.asyncio.to_thread", ...)` which scopes the patch to the module under test.

### Risk

- **Current**: None — the global form works because Python module identity is shared.
- **Future**: A test refactor that imports `asyncio.to_thread` separately could bypass the global patch unexpectedly.

### Affected locations

- `tests/test_mcp/test_lifespan.py`

### Remediation (when touching test_lifespan.py for other reasons)

Replace `patch("asyncio.to_thread", ...)` with `patch("src.mcp.server.asyncio.to_thread", ...)`.

---

## TD-010 — Dockerfile copies `pyproject.toml` into the runtime stage unnecessarily

**Feature**: 003-container-polish-devloop
**Severity**: Low — bytes only; no correctness risk
**Status**: Deferred — unverified whether `fastmcp run` actually reads it at runtime

### Priority

low

### Context

The Dockerfile runtime stage copies `pyproject.toml` from the builder. If `fastmcp run` does not read project metadata at runtime, this file is dead weight in the image layer.

### Risk

- **Current**: Minimal — ~5 KB overhead per image layer.

### Affected locations

- `Dockerfile` — runtime `COPY --from=builder /app/pyproject.toml` line

### Remediation (next Dockerfile touch)

Verify whether `fastmcp run src/mcp/server.py` reads `pyproject.toml` at startup (e.g., run the container, rename the file, confirm tool calls still work). Drop the `COPY` if it is unused.

---

## TD-011 — `.env.example` lists environment variables that `docker-compose.yml` ignores

**Feature**: 003-container-polish-devloop
**Severity**: Low — confusing for power users who edit these vars and see no effect
**Status**: Deferred

### Priority

low

### Context

`.env.example` contains `MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, and the `MEMENTO_EMBEDDING_*` block. The compose file hardcodes all of these; only `MEMENTO_NEO4J_PASSWORD` is read from `.env` via substitution. Power users who copy `.env.example` and edit these fields see no effect on the running container.

### Risk

- **Current**: Confusion; no functional impact.

### Affected locations

- `.env.example`

### Remediation (when touching .env.example for other reasons)

Add section headers distinguishing dev-only vars from compose-read vars, e.g., `# Dev-only — ignored by docker-compose`. Alternatively, ship a second `.env.power-user.example` with only `MEMENTO_NEO4J_PASSWORD`.

---

## TD-012 — Cache-dir contract between `Dockerfile` and `Config.embedding_cache_dir` is implicit

**Feature**: 003-container-polish-devloop
**Severity**: Low — silent breakage if one side changes without the other
**Status**: Deferred

### Priority

low

### Context

The Dockerfile bakes the embedding model to `/app/.cache/models`; `Config.embedding_cache_dir` defaults to `.cache/models` (relative to `WORKDIR /app`). They agree only because of the `WORKDIR` alignment. Changing either without updating the other silently breaks offline model loading.

### Risk

- **Current**: None — values are in sync.
- **Future**: Refactoring either side without updating the other causes a model re-download or a startup failure.

### Affected locations

- `Dockerfile` — `SentenceTransformer(..., cache_folder='/app/.cache/models')` line in builder stage
- `src/utils/config.py` — `embedding_cache_dir` default

### Remediation (when touching either location)

Add a one-line comment in the Dockerfile pointing to `Config.embedding_cache_dir`'s default (or vice versa) so the dependency is explicit.

---

## TD-013 — ADR-007 illustrative example uses `v0.2.0`; real `docker-compose.yml` uses `v0.0.2`

**Feature**: 003-container-polish-devloop
**Severity**: Low — doc drift; no functional impact
**Status**: Deferred

### Priority

low

### Context

The docker-compose excerpt in `Documentation/ADR/ADR-007-container-setup.md` shows `image: ghcr.io/rigrergl/memento:v0.2.0`. The real `docker-compose.yml` uses `v0.0.x`. The ADR prose notes it is "illustrative", but the version mismatch confuses readers who diff the two.

### Affected locations

- `Documentation/ADR/ADR-007-container-setup.md` — docker-compose excerpt

### Remediation (next ADR touch)

Update the example version to `v0.0.2` (or use a generic `vX.Y.Z` placeholder that doesn't drift).

---

## TD-014 — Two import styles for `src.mcp.server` within `test_server.py`

**Feature**: 003-container-polish-devloop
**Severity**: Low — stylistic inconsistency
**Status**: Deferred

### Priority

low

### Context

`tests/test_mcp/test_server.py` uses both `import src.mcp.server as server_module` (for `patch.object`) and `from src.mcp.server import mcp` (inside `_get_tool_fn`). The inconsistency makes the test file slightly harder to read.

### Affected locations

- `tests/test_mcp/test_server.py`

### Remediation (when touching test_server.py for other reasons)

Standardize to the module-level `server_module` reference and access `mcp` as `server_module.mcp` where needed.
