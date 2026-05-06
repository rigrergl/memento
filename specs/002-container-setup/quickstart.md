# Quickstart: 002-container-setup

**Audience**: contributors verifying this feature end-to-end. Two flows: power-user (US1) and developer (US2). Both must pass before the feature is considered shippable.

---

## Prerequisites (any flow)

- Docker Desktop (Mac/Windows) or Docker Engine 24+ (Linux) with `docker compose` plugin.
- Git.
- For dev flow only: `uv` installed on the host VM, plus an MCP client (Claude Code or Gemini CLI).

---

## Flow 1 — Power-User (US1)

This validates FR-001, FR-002, FR-003, FR-004, FR-005, FR-011, FR-012, FR-013, SC-001, SC-002, SC-003, SC-004.

> **Bootstrap caveat**: until the maintainer has cut `v0.0.2` and set GHCR visibility to Public per FR-011 §Bootstrap (research §R12), `docker compose pull` will fail. Run this flow only after the bootstrap window has closed.

### 1. Clone

```bash
git clone https://github.com/rigrergl/memento.git
cd memento
```

### 2. Start the stack

```bash
docker compose up -d
```

Expected: Docker pulls `ghcr.io/rigrergl/memento:vX.Y.Z` (the pinned tag) and `neo4j:2026.03.1`. Both containers start; `docker compose ps` reports `healthy` for both within ~60 s.

```bash
docker compose ps
```

### 3. Verify the HTTP endpoint

```bash
curl -fsS http://127.0.0.1:8000/mcp/
```

Expected: HTTP 200 (or an MCP JSON envelope). Anything other than connection refused.

```bash
# Negative check: not exposed on LAN
curl --connect-timeout 2 http://$(hostname -I | awk '{print $1}'):8000/mcp/ || echo "expected: connection refused or timeout"
```

### 4. Wire your MCP client

#### Claude Code (native HTTP)

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "memento": {
      "type": "http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

Restart Claude Code.

#### Claude Desktop (stdio bridge fallback)

Add to `claude_desktop_config.json` — pick whichever runtime you have:

```json
{
  "mcpServers": {
    "memento": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/mcp/"]
    }
  }
}
```

Or with `uvx`:

```json
{
  "mcpServers": {
    "memento": {
      "command": "uvx",
      "args": ["mcp-proxy", "http://localhost:8000/mcp/"]
    }
  }
}
```

### 5. Smoke-test `remember` and `recall`

In your MCP client, ask the agent to call:

- `remember(content="My favorite color is blue", confidence=0.9)` — should return a `Memory stored with id: <uuid>` string.
- `recall(query="favorite color", limit=5)` — should return at least the memory just stored.

### 6. Persistence check

```bash
docker compose down
docker compose up -d
# Wait for healthy.
```

Repeat the `recall` call from step 5. Expected: the memory survives restart (Neo4j named volume).

### 7. Upgrade flow

When a new release is published:

```bash
git pull
docker compose pull
docker compose up -d
```

Expected: the new pinned tag in `docker-compose.yml` is fetched and applied.

### Pass criteria for US1

- ✅ `docker compose up -d` to first successful tool call: under 5 minutes (excluding image pull). [SC-001]
- ✅ Memento `healthcheck` flips to `healthy` and the first MCP tool call returns within 5 s after that. [SC-002]
- ✅ Network isolation test (`docker run --network none ...`) shows the embedding model loads from the baked path without internet. [SC-003]
- ✅ Zero manual steps beyond `git clone`, `docker compose up -d`, and one MCP client config entry. [SC-004]
- ✅ Restart preserves stored memories.

---

## Flow 2 — Developer (US2)

This validates FR-006, FR-007, FR-009, FR-010, SC-005.

### 1. Clone and bootstrap env

```bash
git clone https://github.com/rigrergl/memento.git
cd memento
cp .env.example .env  # no edits needed — defaults match docker compose
```

### 2. Sync dependencies

```bash
uv sync
```

### 3. Start Neo4j only

```bash
docker compose up neo4j -d
```

Wait for Neo4j healthy (`docker compose ps neo4j`).

### 4. Export env so `.mcp.json` substitutions resolve

```bash
set -a; source .env; set +a
```

(Or use `direnv` if you have it.)

### 5. Launch your MCP client in the repo

Open Claude Code or Gemini CLI from the repo root. The client reads `.mcp.json` and:

- Spawns Memento via `uv run fastmcp run src/mcp/server.py --reload`.
- Spawns `mcp-neo4j-cypher` via `uvx`, with credentials interpolated from your shell's `MEMENTO_NEO4J_*` vars.

Expected: both `memento` and `neo4j-cypher` MCP servers connect.

### 6. Edit a tool, see reload

Edit `src/mcp/server.py` — for example, change the format string in `remember` to add a marker like `[edited]`.

In the MCP client, call `remember(...)`. Expected: at most one failed call, then the next call returns the new format. The dev sees the worker restart and the client respawn the subprocess. (US2 acceptance scenario 2.)

### 7. Self-validate via Neo4j MCP

After calling `remember`, ask the agent to call the `neo4j-cypher` MCP's tool to run `MATCH (m:Memory) RETURN m LIMIT 5`. Expected: the memory just stored is visible in the database. This is the dev-loop self-validation pattern from ADR-007.

### Pass criteria for US2

- ✅ Both MCP servers connect from `.mcp.json` with no manual config beyond `cp .env.example .env`. [FR-009, FR-010]
- ✅ `--reload` restarts the worker on edit; client respawns; new tool code is exercised on next call. [US2 AC2]
- ✅ Importing `src.mcp.server` in a test does not open a Neo4j connection or load the embedding model. [SC-005] — verified by the new lifespan unit test (`tests/test_mcp/test_lifespan.py`).

---

## Test-suite gate (every flow)

Per Constitution Principle V (Mandatory Testing) and Quality Gate 5:

```bash
uv run pytest
```

Expected: green. All existing tests plus the new lifespan tests pass.

```bash
uv run pytest --cov=src --cov-report=term-missing
```

Expected: coverage on `src/mcp/server.py` reflects the new lifespan paths.
