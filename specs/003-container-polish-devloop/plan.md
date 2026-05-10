# Implementation Plan: 003-container-polish-devloop

**Branch**: `feature/003-container-polish` | **Date**: 2026-05-09 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/003-container-polish-devloop/spec.md`

## Summary

Polish the power-user container setup (healthcheck, lifespan safety, filesystem permissions, credential guidance) and validate the developer dev loop end-to-end on both Claude Code and Gemini CLI. Closes all open feedback from 002-container-setup and ships `v0.0.3` of the published image.

## Technical Context

**Language/Version**: Python 3.12 (runtime image: `python:3.12-slim`)  
**Primary Dependencies**: FastMCP 3.2.4, neo4j driver >=5.28.0, sentence-transformers >=5.1.0, pydantic >=2.11.0, pydantic-settings >=2.11.0  
**Storage**: Neo4j (Docker Compose service)  
**Testing**: pytest via `uv run pytest`  
**Target Platform**: Linux container (Docker/Docker Compose) + Linux VM (dev loop)  
**Project Type**: Single project (MCP server)  
**Performance Goals**: None — deliberately excluded from this spec  
**Constraints**: None timing-based — deliberately excluded from this spec  
**Scale/Scope**: Single-user, single-tenant deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. YAGNI | PASS | Every change has a concrete requirement (FR-001–FR-013). No speculative features. |
| II. KISS | PASS | Healthcheck uses the simplest option (GET `/health` route). Lifespan fix is a 3-line repositioning. Parameter descriptions are purely additive. |
| III. Established Patterns | PASS | No new patterns introduced. Factory and Repository patterns unchanged. |
| IV. Layered Architecture | PASS | All changes stay within their respective layers (MCP layer, container config). |
| V. Mandatory Testing | PASS | Tests required for FR-002 (lifespan leak), FR-012 (module globals). Existing test suite must continue passing. |
| VI. TDD | PASS | Tests for FR-002 and FR-012 written before implementation. FR-001 healthcheck verified manually (no unit test for HTTP routes per project convention). |

**No violations. All gates pass.**

## Project Structure

### Documentation (this feature)

```text
specs/003-container-polish-devloop/
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   └── healthcheck.md
├── verification.md      ← Generated during FR-007/FR-008 execution (not by /speckit-plan)
└── tasks.md             ← Phase 2 output (/speckit.tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
└── mcp/
    └── server.py           ← FR-001 (health route), FR-002 (lifespan), FR-012 (globals), FR-013 (param descriptions)

tests/
└── test_mcp/
    └── test_lifespan.py    ← New: FR-002 leak test + FR-012 globals refactor test

Dockerfile                  ← FR-006 (chown -R, --user-group)
docker-compose.yml          ← FR-001 (healthcheck test URL), image bump v0.0.3
.env.example                ← FR-004 (remove password suggestion)
.mcp.json                   ← FR-008 (remove neo4j-cypher server)
AGENTS.md                   ← FR-011 (path discovery)
README.md                   ← Developer Setup section, troubleshooting notes
Documentation/
└── known-tech-debt.md      ← FR-009/FR-010 deferred items + Priority field
specs/002-container-setup/contracts/
└── server-lifespan.md      ← Invariant note (embedder reentrant)
```

**Structure Decision**: Single project. Existing `src/` and `tests/` layout unchanged. No new top-level directories.

## Phase 0: Research

**Status**: Complete. See [research.md](research.md).

### Key decisions resolved

| ID | Question | Resolution |
|---|---|---|
| R1 | Healthcheck shape | Option (a): `@custom_route("/health")` GET → HTTP 200; curl `-f http://localhost:8000/health` |
| R2 | Lifespan fix | Open `try` immediately after `Neo4jRepository(...)` |
| R3 | Module globals | `config`, `embedder`, `repository` → local; `service: MemoryService \| None = None` stays |
| R4 | Parameter descriptions | `Annotated[T, Field(description="...")]` on `remember` and `recall` parameters |
| R5 | Dockerfile permissions | `--user-group` on `useradd` + trailing `RUN chown -R app:app /app` |
| R6 | `.env.example` | Remove password suggestion; add `openssl rand -base64 12` hint |
| R7 | AGENTS.md | Discover feature directory from `.specify/feature.json` |
| R8 | `.mcp.json` | Remove `neo4j-cypher` server entry |
| R9 | Dependency versions | No breaking changes; FastMCP 3.2.4 `custom_route` confirmed |
| R10 | Feedback ledger | All C/H/M/L items triaged; deferred items → known-tech-debt.md |

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md).

### Contracts

See [contracts/healthcheck.md](contracts/healthcheck.md).

**Cross-spec contract updates**:
- `specs/002-container-setup/contracts/server-lifespan.md` — gains one-line embedder-reentrant invariant note and updated module-level exports list (only `service` at module scope after FR-012).

### Agent Context

See AGENTS.md — `<!-- SPECKIT START -->` block updated to use `.specify/feature.json` discovery (FR-011).

## Implementation Phases

### Phase A: Tests (TDD — write first)

| Test | File | Purpose |
|---|---|---|
| `test_lifespan_closes_driver_on_startup_failure` | `tests/test_mcp/test_lifespan.py` | FR-002: inject failure in `ensure_vector_index`, assert `repository.close` called once |
| `test_module_globals_only_service` | `tests/test_mcp/test_lifespan.py` | FR-012: after lifespan exits, `service` is None at module scope; `config`/`embedder`/`repository` not in module globals |

Existing tests (`test_server.py`, `test_lifespan.py`) must continue passing.

### Phase B: Code Changes

| FR | File | Change |
|---|---|---|
| FR-001 | `src/mcp/server.py` | Add `@mcp.custom_route("/health", methods=["GET"])` returning `JSONResponse({"status": "ok"})` |
| FR-002 | `src/mcp/server.py` | Move `try/finally` to open immediately after `Neo4jRepository(...)` |
| FR-012 | `src/mcp/server.py` | `config`, `embedder`, `repository` → local vars in `lifespan`; annotate `service: MemoryService \| None = None` |
| FR-013 | `src/mcp/server.py` | `Annotated[T, Field(description="...")]` on all four parameters (`content`, `confidence`, `query`, `limit`) |

### Phase C: Container Config

| FR | File | Change |
|---|---|---|
| FR-001 | `docker-compose.yml` | `test:` → `curl -f http://localhost:8000/health` |
| FR-004 | `.env.example` | Remove password suggestion; add generation hint |
| FR-006 | `Dockerfile` | `--user-group` on `useradd`; trailing `RUN chown -R app:app /app` |
| Image bump | `docker-compose.yml` | `v0.0.2` → `v0.0.3` |
| FR-008 | `.mcp.json` | Remove `neo4j-cypher` server entry |

### Phase D: Documentation

| FR | File | Change |
|---|---|---|
| FR-011 | `AGENTS.md` | Update `<!-- SPECKIT START -->` block to feature-discovery phrasing |
| FR-009/FR-010 | `Documentation/known-tech-debt.md` | Add Priority field to TD-001–TD-004; add TD-005–TD-014 for deferred items |
| Spec | `specs/002-container-setup/contracts/server-lifespan.md` | Add embedder-reentrant invariant note; update module-level exports |
| README | `README.md` | Developer Setup: launching ritual, stale-volume troubleshooting, Python version note, Bolt port note |

### Phase E: Verification

| FR | Artifact | Action |
|---|---|---|
| FR-007 | `specs/003-container-polish-devloop/verification.md` | Power-user end-to-end: clean clone → `docker compose up -d` → both healthy → remember/recall |
| FR-008 | `specs/003-container-polish-devloop/verification.md` | Dev loop: Claude Code + Gemini CLI; canonical prompt; cypher-shell probe; per-client transcripts |
| FR-007 | `docker-compose.yml` / GHCR | Build and publish `v0.0.3` image |

## Constitution Check (post-design)

All gates confirmed passing. No new complexity introduced; all changes are targeted and minimal:
- The `/health` route adds ~5 lines to `server.py`.
- The lifespan fix is a 3-line restructure.
- The globals refactor removes 4 module-level declarations.
- The Dockerfile change is 2 lines altered.
- No new abstractions, no new modules, no new patterns.
