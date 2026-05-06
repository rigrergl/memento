# Contract: `docker-compose.yml`

**Location**: repo root (`/docker-compose.yml`)
**Driven by**: FR-004, FR-005, FR-011; research §R4
**Consumers**: Local power users via `docker compose up -d`. Not used by Cloud Run.

## Required services

### Service: `memento`

| Directive | Required value | Source |
|---|---|---|
| `image` | `ghcr.io/rigrergl/memento:vX.Y.Z` (initial: `v0.0.2`) — pinned semver, no `:latest`, no `build:` directive. | FR-011 |
| `depends_on.neo4j.condition` | `service_healthy` | FR-004 |
| `command` | `["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]` | FR-004 |
| `ports` | `["127.0.0.1:8000:8000"]` | FR-005 |
| `environment.MEMENTO_NEO4J_URI` | `bolt://neo4j:7687` | ADR-007 |
| `environment.MEMENTO_NEO4J_USER` | `neo4j` | ADR-007 |
| `environment.MEMENTO_NEO4J_PASSWORD` | `${MEMENTO_NEO4J_PASSWORD:?...}` — required, no fallback default. Compose MUST fail at config-time when the variable is unset. | ADR-007 |
| `environment.MEMENTO_EMBEDDING_PROVIDER` | `local` | ADR-007 |
| `environment.MEMENTO_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | ADR-007 |
| `environment.MEMENTO_EMBEDDING_CACHE_DIR` | **MUST NOT be set** — relies on the `Config` default that resolves to the baked path. | FR-003 / R3 |
| `healthcheck.test` | `["CMD-SHELL", "curl -f http://localhost:8000/mcp/ || exit 1"]` | FR-004 |
| `healthcheck.interval` | `10s` | R4 |
| `healthcheck.timeout` | `5s` | R4 |
| `healthcheck.retries` | `6` | R4 |
| `healthcheck.start_period` | `30s` | R4, SC-002 |

### Service: `neo4j`

| Directive | Required value | Source |
|---|---|---|
| `image` | `neo4j:2026.03.1` (CalVer pinned; **not** `neo4j:5`) | ADR-007 |
| `ports` | `["127.0.0.1:7687:7687", "127.0.0.1:7474:7474"]` | FR-005 |
| `environment.NEO4J_AUTH` | `neo4j/${MEMENTO_NEO4J_PASSWORD:?...}` — required, no fallback default; same enforcement as the memento service. | ADR-007 |
| `volumes` | `["neo4j_data:/data"]` | ADR-007 |
| `healthcheck.test` | `["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]` | ADR-007 |
| `healthcheck.interval` | `5s` | ADR-007 |
| `healthcheck.timeout` | `5s` | ADR-007 |
| `healthcheck.retries` | `10` | ADR-007 |

### Volumes

| Volume | Purpose |
|---|---|
| `neo4j_data` | Named volume for Neo4j on-disk graph state. |

## Forbidden

- No `build:` directive on `memento` — power users MUST NOT need a local build (FR-011, FR-004).
- No `:latest` tags anywhere (FR-011).
- No bind to `0.0.0.0` for any host port (FR-005).
- No `MEMENTO_TRANSPORT`, `MEMENTO_MCP_HOST`, `MEMENTO_MCP_PORT` env vars (FR-007).

## Test plan

- `docker compose config` emits a syntactically valid resolved config with no warnings.
- `docker compose up -d` (against the published image after R12 bootstrap) reaches `docker compose ps` "healthy" status for both services within ~60 s.
- `curl -fsS http://127.0.0.1:8000/mcp/` returns a 2xx (or at minimum a non-connection-refused MCP envelope) once both services are healthy.
- `curl -fsS http://10.x.x.x:8000/mcp/` (LAN IP) **fails to connect** — verifies loopback binding.
- `docker compose down` followed by `docker compose up -d` preserves stored memories (volume persistence).
