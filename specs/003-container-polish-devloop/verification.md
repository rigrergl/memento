# Verification — 003-container-polish-devloop

**Feature**: 003-container-polish-devloop  
**Branch**: `feature/003-container-polish`  
**Date**: TBD

---

## Power-User Verification (FR-007)

_Verify that the v0.0.3 image, built from this branch, produces both services healthy on a fresh clone._

**Steps**:
1. `git clone https://github.com/rigrergl/memento.git && cd memento`
2. `cp .env.example .env` — set a password (`openssl rand -base64 12` recommended)
3. `docker compose up -d`
4. `docker compose ps` — both `memento` and `neo4j` report `healthy`
5. Configure an MCP client (see README §MCP client configuration) and exercise `remember`/`recall`

**Results**:

> TBD — to be populated during T021 (local build) and T022 (published image).

---

## Claude Code Dev Loop (FR-008)

_Verify that Claude Code can connect to the memento MCP server via the project-level `.mcp.json`, observe tool description changes after `--reload` triggers a worker respawn, and confirm database state via `cypher-shell`._

**Prerequisites**:
- `docker compose up neo4j -d`
- Launch Claude Code at the repo root (`.mcp.json` honoured automatically)

**Canonical prompt**:

> TBD — to be populated during T015.

**Canonical `cypher-shell` query**:

```bash
cypher-shell -u neo4j -p $MEMENTO_NEO4J_PASSWORD --database neo4j \
  'MATCH (m:Memory) RETURN m.content LIMIT 5'
```

**Transcript**:

> TBD — to be populated during T015.

**Client-specific caveats**:

> TBD

---

## Gemini CLI Dev Loop (FR-008)

_Repeat the dev loop validation with Gemini CLI using the same flow._

**Prerequisites**:
- `docker compose up neo4j -d`
- Launch Gemini CLI at the repo root (`.mcp.json` honoured automatically)

**Canonical prompt**:

> TBD — to be populated during T016.

**Transcript**:

> TBD — to be populated during T016.

**Client-specific caveats**:

> TBD — document subprocess respawn behaviour, session-level tool-description caching, or other Gemini CLI differences.
