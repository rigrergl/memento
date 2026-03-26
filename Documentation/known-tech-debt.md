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
