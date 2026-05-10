# Contract: Memento Container Healthcheck

**Location**: `docker-compose.yml` (memento service), `src/mcp/server.py` (health route)  
**Driven by**: FR-001, SC-001; research §R1  
**Consumers**: Docker Compose health gate (`depends_on: service_healthy`), `docker compose ps`, external orchestrators.

## Healthcheck shape

The Memento container healthcheck MUST use:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 6
  start_period: 30s
```

`interval`, `timeout`, `retries`, and `start_period` are unchanged from the 002 baseline (timing constraints deliberately excluded from this spec).

## Health endpoint

The MCP server MUST expose a GET `/health` endpoint that returns HTTP 200 with a JSON body. This endpoint is registered via FastMCP's `custom_route` decorator:

```python
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})
```

**Response contract**:
- Status: `200 OK`
- Content-Type: `application/json`
- Body: `{"status": "ok"}`

The endpoint is available as soon as the HTTP transport is listening. It does not probe Neo4j connectivity or embedding model readiness — it is a liveness check, not a readiness check.

## What this contract replaces

The 002 healthcheck (`curl -f http://localhost:8000/mcp/`) sent a bare GET to the FastMCP streamable-HTTP endpoint, which returns a non-2xx response for GET requests (the MCP protocol requires POST with specific headers). This caused the service to remain `unhealthy` indefinitely.

## Verification

`docker compose ps memento` MUST report `healthy` (not `starting` or `unhealthy`) after normal startup. Verified as part of FR-007's power-user end-to-end test.
