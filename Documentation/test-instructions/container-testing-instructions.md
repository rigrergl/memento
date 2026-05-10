# Container Testing Instructions

This document outlines the procedures for verifying Memento's containerized setup locally.

## Prerequisites

1. **Docker & Docker Compose**: Ensure you have Docker installed and the `docker` daemon is running.
2. **Permissions**: If you haven't added your user to the `docker` group, you will need to prefix `docker` commands with `sudo`.
3. **Environment Variables**: Copy `.env.example` to `.env` and ensure `MEMENTO_NEO4J_PASSWORD` is at least 8 characters long.
   ```bash
   cp .env.example .env
   # Ensure password length >= 8
   set -a; source .env; set +a
   ```

---

## Phase 0: Power User Setup (Published Image)
*Goal: Verify the published `ghcr.io` image works end-to-end — no local build required. This mirrors the setup a user following the README's Power-User Setup section would run.*

1. **Configure environment**:
   ```bash
   cp .env.example .env
   # Set MEMENTO_NEO4J_PASSWORD to a unique value (8+ characters).
   set -a; source .env; set +a
   ```

2. **Start the stack** (pulls the published image automatically):
   ```bash
   docker compose up -d
   ```
   *Note: First run downloads the image and the baked embedding model — may take several minutes.*

3. **Verify Neo4j is healthy**:
   ```bash
   docker compose ps
   ```
   Wait until both `memento` and `neo4j` services show `(healthy)` or `running`.

4. **Verify Memento is reachable**:
   ```bash
   curl http://localhost:8000/health
   ```
   Expected: HTTP 200 response.

5. **Smoke test tools**: Proceed to [Phase 3: Smoke Test](#phase-3-smoke-test-tool-invocation) to confirm `remember` and `recall` work against the running stack.

6. **Cleanup**:
   ```bash
   docker compose down
   ```

---

## Phase 1: Developer Setup (Hybrid)
*Goal: Run Neo4j in a container but run Memento natively for fast iteration.*

1. **Start Neo4j**:
   ```bash
   docker compose up neo4j -d
   ```
2. **Verify Neo4j Health**:
   Wait ~15s until `docker compose ps neo4j` shows `(healthy)`.
3. **Run Memento Natively**:
   ```bash
   uv run fastmcp run src/mcp/server.py --transport http --host 0.0.0.0 --port 8000
   ```
4. **Verify Connectivity**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Phase 2: Full Container Setup
*Goal: Verify the Dockerfile, model baking, and container-to-container networking.*

1. **Build the Memento Image**:
   ```bash
   docker build -t memento:dev .
   ```
   *Note: This downloads and bakes the embedding model into the image. It may take several minutes.*

2. **Temporary Configuration Change**:
   Modify `docker-compose.yml` to use the local image:
   ```yaml
   services:
     memento:
       image: memento:dev  # Change from ghcr.io/... to memento:dev
   ```

3. **Start the Stack**:
   ```bash
   docker compose up
   ```

4. **Verify**:
   ```bash
   curl http://localhost:8000/health
   ```

---

## Phase 3: Smoke Test (Tool Invocation)
*Goal: Confirm `remember` and `recall` work end-to-end against Neo4j. Run after Phase 1 or Phase 2.*

**Prerequisite**: Node.js / `npx` must be available.

1. **Store a memory**:
   ```bash
   npx @modelcontextprotocol/inspector --cli --method tools/call \
     --tool-name remember \
     --tool-arg content="smoke test memory" \
     --tool-arg confidence=0.9 \
     http://localhost:8000/mcp
   ```
   Expected: JSON response with a `memory_id` field.

2. **Recall the memory**:
   ```bash
   npx @modelcontextprotocol/inspector --cli --method tools/call \
     --tool-name recall \
     --tool-arg query="smoke test" \
     http://localhost:8000/mcp
   ```
   Expected: JSON response containing a `memories` array with at least one entry matching the stored content.

> **Tip**: Pipe either command through `| jq` for readable output.

> **Alternative (interactive)**: If you prefer testing through Claude Code, add a temporary entry to `.mcp.json`:
> ```json
> {
>   "mcpServers": {
>     "memento-container": { "type": "http", "url": "http://localhost:8000/mcp" }
>   }
> }
> ```
> Then ask Claude Code to call the `remember` and `recall` tools directly. Revert this change before committing.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'src'`
If the container fails with this error, ensure the `Dockerfile` includes `ENV PYTHONPATH=/app` or that you are running the module correctly.

### Neo4j Password Length
Neo4j requires a minimum of 8 characters for the password. If the container exits immediately, check `docker logs memento-neo4j-1`.

### Permissions
If you get "permission denied" when connecting to the Docker socket:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

## Cleanup
```bash
docker compose down
# Revert any changes to docker-compose.yml image tags before committing.
```
