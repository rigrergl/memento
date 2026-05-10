# Research — 003-container-polish-devloop

**Date**: 2026-05-09  
**Branch**: `003-container-polish`  
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## R1. Healthcheck shape for FR-001 (C1)

**Decision**: Option (a) — add `@mcp.custom_route("/health", methods=["GET"])` returning HTTP 200, and update the Docker Compose `test:` to `curl -f http://localhost:8000/health`.

**Rationale**: FastMCP 3.2.4 (installed) exposes `custom_route` as a first-class decorator. Option (a) is simpler than (b) (POST+MCP-handshake) and requires no change to the healthcheck curl flags. The spec explicitly calls (a) out as simpler and acceptable.

**FastMCP API confirmed**:
```python
from starlette.requests import Request
from starlette.responses import JSONResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})
```
`curl -f http://localhost:8000/health` returns HTTP 200.

**Alternatives considered**:
- (b) POST `initialize` handshake: works but more brittle (depends on MCP protocol version string, SSE response format).
- (c) FastMCP built-in liveness: confirmed absent in 3.x.
- (d) TCP socket probe: verifies listener, not MCP readiness.

**Healthcheck values**: `start_period`, `interval`, `timeout`, and `retries` stay at current values per spec clarifications ("out of scope").

**Contract impact**: A new `healthcheck.md` contract is added in `specs/003-container-polish-devloop/contracts/` (not modifying 002's contracts since the 002 compose spec was for the broken shape; the 003 contracts document the corrected shape).

---

## R2. Lifespan driver-leak fix for FR-002 (C2)

**Decision**: Open the `try` block immediately after `Neo4jRepository(...)`. Embedder construction stays before driver construction (no change to ordering).

**Rationale**: Spec clarifications §"Lifespan + driver lifecycle" and feedback §C2 specify this exact fix. The current shape leaves the driver constructed but not protected if `ensure_vector_index` raises.

**Correct shape**:
```python
embedder = Factory.create_embedder(config)
repository = Neo4jRepository(...)
try:
    await asyncio.to_thread(repository.ensure_vector_index)
    service = MemoryService(...)
    yield
finally:
    await asyncio.to_thread(repository.close)
```

**Test required**: A unit test that monkeypatches `repository.ensure_vector_index` to raise and asserts `repository.close` was called exactly once.

**Alternatives considered**: Wrapping the entire lifespan (including embedder creation) in try/finally — rejected per spec (simpler to document the construction order invariant instead).

---

## R3. Module globals refactor for FR-012

**Decision**: `config`, `embedder`, `repository` become local variables inside `lifespan`. Only `service` remains at module scope with annotation `MemoryService | None = None`.

**Rationale**: The existing test pattern `patch.object(server_module, "service", mock_service)` requires `service` to be a module-level name. No test patches `config`, `embedder`, or `repository` directly — confirmed by grepping tests.

**Impact on server-lifespan.md contract**: The 002 contract currently lists all four names as module-level exports. This contract must be updated to reflect that only `service` remains at module scope. The `specs/002-container-setup/contracts/server-lifespan.md` file also gains the embedder-reentrant invariant note per spec.

---

## R4. Parameter descriptions for FR-013

**Decision**: Use `Annotated[T, Field(description="...")]` from pydantic for each parameter on `remember` and `recall`.

**Rationale**: FastMCP 3.x propagates pydantic `Field` metadata to the MCP tool schema, making descriptions visible to MCP clients (e.g., Claude Code's tool listing). This is the idiomatic FastMCP pattern.

**Confirmed API** (FastMCP 3.2.4):
```python
from typing import Annotated
from pydantic import Field

@mcp.tool()
def remember(
    content: Annotated[str, Field(description="The text to store as a memory. Must be non-empty and at most 4000 characters.")],
    confidence: Annotated[float, Field(description="How confident you are in this memory, from 0.0 (uncertain) to 1.0 (certain). Values outside [0, 1] are rejected.")],
) -> str:
```

**Stylistic reference**: `Documentation/legacy/mcp-tool-specification.md` — concise, behavioural, parameter-focused. The `source` field and `supersede_memory` are NOT re-introduced.

**Alternatives considered**: Updating the function docstring with an Args section — less reliable; FastMCP does not guarantee parsing of arbitrary docstring formats for parameter-level descriptions.

---

## R5. Dockerfile permissions fix for FR-006 (H3)

**Decision**: Add `--user-group` to `useradd`, move `RUN chown -R app:app /app` to after all `COPY` instructions.

**Rationale**: `chown app /app` (current) only changes the directory inode; subsequent `COPY --from=builder` retains root ownership. A trailing `chown -R` fixes all content in one layer. `--user-group` ensures `app:app` resolves cleanly (creates the `app` group alongside the `app` user).

**Correct Dockerfile shape** (runtime stage):
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --create-home --uid 1001 --user-group app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/.cache/models /app/.cache/models
COPY --from=builder /app/pyproject.toml /app/pyproject.toml

RUN chown -R app:app /app

ENV PATH=/app/.venv/bin:$PATH

USER app
```

---

## R6. .env.example change for FR-004 (H1)

**Decision**: Remove the `# For local development with the provided docker-compose, use: memento-password` line. Add an `openssl rand -base64 12` generation hint.

**Rationale**: ADR-007 explicitly rejected a default password. The comment is the same failure mode in different clothing. A generation hint is helpful without normalizing any specific value.

**Target shape**:
```
# Neo4j requires a minimum of 8 characters.
# Generate one: openssl rand -base64 12
MEMENTO_NEO4J_PASSWORD=
```

---

## R7. AGENTS.md path discovery for FR-011

**Decision**: Replace the hardcoded `specs/002-container-setup/plan.md` reference with a discovery instruction using `.specify/feature.json`'s `feature_directory` key.

**`.specify/feature.json` format**:
```json
{"feature_directory": "specs/003-container-polish-devloop"}
```

**Updated AGENTS.md `<!-- SPECKIT START -->` block**:
```markdown
<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan.
The current feature directory is defined in `.specify/feature.json` under
the `feature_directory` key. Read `<feature_directory>/plan.md`.
<!-- SPECKIT END -->
```

---

## R8. .mcp.json cleanup for FR-008

**Decision**: Remove the `neo4j-cypher` server entry from `.mcp.json`. DB-state probes during dev-loop validation use `cypher-shell` directly.

**Rationale**: Spec clarifications §"Dev-loop validation" explicitly requires this removal.

---

## R9. Time-sensitive dependency verification

Verified against current installed state and pyproject.toml:

| Dependency | Constraint | Installed | Status |
|---|---|---|---|
| fastmcp | >=3.0.0 | 3.2.4 | Current — `custom_route` API confirmed |
| neo4j | >=5.28.0 | verified via uv | Stable API |
| sentence-transformers | >=5.1.0 | verified via uv | Stable |
| pydantic | >=2.11.0 | verified via uv | `Field` API confirmed |
| pydantic-settings | >=2.11.0 | verified via uv | Stable |

No version downgrades or breaking changes found.

---

## R10. Feedback ledger triage (FR-009 / FR-010)

Terminal state per spec clarifications §"Feedback ledger triage":

| Item | State | Disposition |
|---|---|---|
| C1 | Resolved | Fixed by FR-001 (healthcheck) |
| C2 | Resolved | Fixed by FR-002 (lifespan try/finally) |
| H1 | Resolved | Fixed by FR-004 (.env.example) |
| H2 | Not-Applicable | Bootstrap closed (v0.0.2 published) |
| H3 | Resolved | Fixed by FR-006 (Dockerfile chown -R) |
| H4 | Deferred | Idempotent `Neo4jRepository.close` — tech-debt entry |
| M1 | Resolved | Fixed by FR-012 (module globals) |
| M2 | Resolved | Fixed by FR-011 (AGENTS.md path discovery) |
| M3 | Deferred | Tech-debt entry |
| M4 | Resolved | `.env.example` generation hint added |
| M5 | Deferred | High-priority tech-debt entry |
| M6 | Deferred | High-priority advisory tech-debt entry |
| L1–L6 | Deferred | Low-priority tech-debt entries |
| L7 | Resolved | Neo4j-cypher server removed from .mcp.json |

New tech-debt entries (H4, M3, M5, M6, L1–L6) are appended to `Documentation/known-tech-debt.md` with the new `Priority` field. Existing TD-001–TD-004 entries gain the `Priority` field as well.
