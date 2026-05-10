# Contract: `src/mcp/server.py` Lifespan Hook

**Location**: `src/mcp/server.py`
**Driven by**: FR-006, FR-007, SC-005; research §R5, §R6
**Consumers**: `fastmcp run` (dev `--reload`, power-user container, Cloud Run); test suite via `import src.mcp.server`.

## Required public surface (post-refactor)

The module MUST export:

- `mcp: FastMCP` — the server instance with `lifespan=…` attached.
- `remember: Tool` — registered via `@mcp.tool()`; signature unchanged: `(content: str, confidence: float) -> str`.
- `recall: Tool` — registered via `@mcp.tool()`; signature unchanged: `(query: str, limit: int = 10) -> str`.
- Module-level name `service: MemoryService | None` — initialized to `None` at import time, populated by the lifespan `__aenter__`. This name exists so tests can `patch.object(server_module, "service", mock_service)`.

Note (updated by 003-container-polish-devloop / FR-012): `config`, `embedder`, and `repository` are **not** module-level exports — they are local variables inside `lifespan`. The embedder is reentrant and resource-free; the Neo4j driver (`repository`) owns the only leakable handle and is protected by the `try/finally` block.

The module MUST NOT export:

- `if __name__ == "__main__":` block (FR-006).
- Any reference to `config.mcp_host`, `config.mcp_port`, or env vars `MEMENTO_TRANSPORT`, `MEMENTO_MCP_HOST`, `MEMENTO_MCP_PORT` (FR-007).

## Required behaviour

### At import time (no `mcp.run()` yet)

- `Config()` MUST NOT be instantiated.
- `Factory.create_embedder(...)` MUST NOT be called.
- `Neo4jRepository(...)` MUST NOT be called (no driver instantiation, no socket open).
- `repository.ensure_vector_index()` MUST NOT be called.
- Importing the module MUST succeed even if Neo4j is unreachable and `sentence-transformers` is uninstalled (the latter holds because no symbol from `sentence_transformers` is touched until the lifespan fires).

### When `mcp.run(...)` is invoked (any transport)

The lifespan `__aenter__` MUST, in order:

1. Construct `Config()` (local variable).
2. Call `Factory.create_embedder(config)` (local variable; embedder is reentrant and resource-free).
3. Construct `Neo4jRepository(uri=..., user=..., password=...)` (local variable).
4. Open `try/finally` immediately after step 3 to ensure driver cleanup on any subsequent failure.
5. Call `await asyncio.to_thread(repository.ensure_vector_index)`.
6. Construct `MemoryService(config=config, embedder=embedder, repository=repository)` and bind to module-level `service`.
7. `yield`.

The lifespan `__aexit__` MUST close the Neo4j driver: `await asyncio.to_thread(repository.close)`. (`Neo4jRepository.close` is the existing teardown method; if it does not yet exist, this spec adds it.)

FastMCP MUST NOT begin accepting tool requests until `__aenter__` returns — guaranteed by the framework. This means `recall` cannot be called before `ensure_vector_index` completes.

### Tool implementations

`remember.fn` and `recall.fn` MUST continue to call the module-level `service` reference (not capture it at definition time). This preserves the existing `patch.object(server_module, "service", mock_service)` test pattern. The trivial implementation is the existing pattern: each tool body references `service.store_memory(...)` / `service.search_memory(...)` directly, looked up from the enclosing module scope at call time.

### Per-environment invocation (unchanged from ADR-007)

| Environment | Command |
|---|---|
| Dev | `uv run fastmcp run src/mcp/server.py --reload` |
| Power user (compose) | `fastmcp run src/mcp/server.py --transport http --host 0.0.0.0 --port 8000` |
| Cloud Run | `fastmcp run src/mcp/server.py --transport http --host 0.0.0.0 --port 8080` |

## Test plan

Tests added or modified in `tests/test_mcp/`:

1. **Import-side-effect-free** (`test_lifespan.py` new): `import src.mcp.server` with `Config()`, `SentenceTransformer(...)`, and `Neo4jRepository.__init__` patched as `MagicMock(side_effect=AssertionError("import touched it"))`. Import MUST succeed without raising — equivalent assertion: bare import does not call any of these constructors. (SC-005)
2. **Lifespan populates globals** (`test_lifespan.py`): construct a stub `lifespan` runner, run `async with mcp.lifespan(mcp):` (or however FastMCP exposes it), verify module-level `config`, `embedder`, `repository`, `service` are non-None and of the expected types.
3. **Lifespan calls `ensure_vector_index`**: same fixture, but with `Neo4jRepository.ensure_vector_index` mocked; assert called exactly once.
4. **Lifespan tears down**: `__aexit__` calls `repository.close`.
5. **Existing 16 tests in `test_server.py`** continue to pass with no changes — this verifies the `patch.object(server_module, "service", ...)` contract is preserved.

## Migration notes

- `tests/test_mcp/conftest.py`'s `patch_server_imports` autouse fixture currently patches `SentenceTransformer` and `GraphDatabase` *because the current `server.py` instantiates them at import time*. After this refactor, those patches become no-ops (nothing at import time touches them), but they remain harmless. Leave them in place for safety — they protect against regressions where someone reintroduces module-level instantiation.
