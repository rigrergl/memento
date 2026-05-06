# Known Technical Debt

Items deferred from feature implementation intentionally. Each entry includes the risk level, the trigger condition for remediation, and the affected locations.

---

## TD-001 — Unstructured exception logging in MCP tool error handlers

**Feature**: 001-baseline-rag
**Severity**: Low (current deployment); Medium (before public/multi-tenant release)
**Status**: Deferred — single-tenant, trusted-user deployment

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
