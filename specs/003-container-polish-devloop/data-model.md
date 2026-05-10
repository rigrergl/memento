# Data Model — 003-container-polish-devloop

**Feature**: 003-container-polish-devloop  
**Date**: 2026-05-09

## Overview

This feature introduces no new entities and no schema migrations. The `Memory` node in Neo4j is unchanged. All changes are to server-side code structure, container configuration, and documentation.

## Changed Entity: `server.py` module globals

**Before** (002): four module-level globals — `config`, `embedder`, `repository`, `service` — all initialized to `None` at import time, populated by the lifespan.

**After** (003): only `service` remains at module scope.

| Name | Scope | Type annotation | Purpose |
|---|---|---|---|
| `service` | Module | `MemoryService \| None` | Module-level for `patch.object(server_module, "service", ...)` test compatibility |
| `config` | Local in `lifespan` | `Config` | Constructed and used entirely within lifespan |
| `embedder` | Local in `lifespan` | `IEmbeddingProvider` | Constructed and used entirely within lifespan |
| `repository` | Local in `lifespan` | `Neo4jRepository` | Constructed and used entirely within lifespan |

**State transitions** for `service`:
- Import time: `None`
- After lifespan `__aenter__`: a live `MemoryService` instance
- After lifespan `__aexit__`: back to `None` (not reset explicitly; lifespan scope ends)

## Tool Parameter Schema (updated by FR-013)

The `remember` and `recall` MCP tools gain parameter descriptions. No parameter names, types, or defaults change.

### `remember`

| Parameter | Type | Description |
|---|---|---|
| `content` | `str` | The text to store as a memory. Must be non-empty and at most 4000 characters. |
| `confidence` | `float` | How confident you are in this memory, from 0.0 (uncertain) to 1.0 (certain). Values outside [0, 1] are rejected. |

### `recall`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | — | The search query used to find semantically similar memories. |
| `limit` | `int` | 10 | Maximum number of matching memories to return, ordered by relevance. |

## No Neo4j Schema Changes

The `Memory` node structure, vector index, and property set are unchanged. This feature does not require a database migration.
