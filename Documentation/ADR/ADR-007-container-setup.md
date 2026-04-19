# ADR-007: Container Setup for Local and Cloud Deployment

## Status
Accepted

## Date
2026-04-08

## Context

Memento needs a container strategy for two deployment targets:

1. **Local (power users)**: Technical users who want to run Memento locally without installing Python, `uv`, or Neo4j. Setup should be a single command.
2. **Cloud**: Memento deployed to Cloud Run for always-on access.

Development is done directly in a VM — not inside a container.

## Decisions

### Development environment: VM replaces devcontainer

The existing `.devcontainer/` setup is removed. Development moves to a VM to run Claude Code in **YOLO mode** (`--dangerously-skip-permissions`), which lets Claude execute all tool calls autonomously. A VM provides the right isolation boundary for this.

> **Note**: this decision is about where **Claude Code** runs, not about whether Memento runs in a container.

The VM is configured with two MCP servers available to Claude:

1. **Memento MCP** — the server under development, running via `uv run`. Claude can call its tools to test behaviour end-to-end.
2. **Neo4j MCP** — connected to the local Neo4j instance. After calling a Memento tool, Claude can query the database directly to verify graph mutations.

This gives Claude a self-validation loop: call a Memento tool → inspect the DB via Neo4j MCP → confirm correctness.

### Development workflow for Memento

Dev runs Memento directly in the VM:

```bash
docker compose up neo4j               # starts Neo4j only, port-mapped to localhost
fastmcp run src/mcp/server.py --reload  # auto-restarts worker on file change
```

The key reason to avoid the power-user container approach here is **setup simplicity**. Running Memento as an ephemeral container requires either a full rebuild on every code change, or a volume-mount + `compose watch` setup to avoid the rebuild — extra Docker plumbing for no real gain. Running directly in the VM, `fastmcp --reload` (introduced in fastmcp v3) watches Python files via `watchfiles` and restarts the worker on change. The stdio connection to the MCP client drops on restart, but the server is stateless, so the MCP client (Claude Code, Gemini CLI) respawns the subprocess and re-handshakes on its next tool call — the agent sees one failed call, retries, and iteration continues with no user intervention. `fastmcp>=3.0.0` is pinned in `pyproject.toml`.

### MCP configuration as repo files

The MCP server config for dev is committed to the repo as `.mcp.json` at the project root. This file is purely for **developing Memento** — it wires in the Memento server under development plus a Neo4j MCP for self-validation. It is **not** the config a power user would use to install Memento as an MCP server in their own client (that setup is described in §"Local Setup (power users)" below). Claude Code treats `.mcp.json` as the project-level MCP configuration, shared with anyone who clones the repo — no manual `~/.claude` setup required:

```json
{
  "mcpServers": {
    "memento": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "src/mcp/server.py", "--reload"]
    },
    "neo4j-cypher": {
      "command": "uvx",
      "args": ["mcp-neo4j-cypher"],
      "env": {
        "NEO4J_URI": "${MEMENTO_NEO4J_URI}",
        "NEO4J_USERNAME": "${MEMENTO_NEO4J_USER}",
        "NEO4J_PASSWORD": "${MEMENTO_NEO4J_PASSWORD}"
      }
    }
  }
}
```

Claude Code (and Gemini CLI) perform `${VAR}` substitution in `.mcp.json` from their own process environment, so the dev must have the `MEMENTO_NEO4J_*` vars exported before launching the client (e.g. via `direnv`, or `set -a; source .env; set +a`). This gives a single source of truth for credentials — the same `.env` file the Memento app reads via pydantic-settings. Not every MCP client performs this substitution; this flow relies on client behavior, confirmed for Claude Code and Gemini CLI.

### Single entrypoint: `fastmcp run`

Every environment starts the server the same way: by invoking the `fastmcp` CLI, which is a thin wrapper that imports `src/mcp/server.py`, locates the `mcp` object, and calls `mcp.run(...)` on it with flags parsed from the command line. Only the flags differ per environment.

| Environment | Command |
|---|---|
| Dev (VM) | `fastmcp run src/mcp/server.py --reload` |
| Power user (container) | `fastmcp run src/mcp/server.py` (stdio is the CLI default) |
| Cloud Run | `fastmcp run src/mcp/server.py --transport http --host 0.0.0.0 --port 8080` |

This replaces the previous `python -m src.mcp.server` entrypoint and its `if __name__ == "__main__":` block. Rationale: we already need `fastmcp run` for `--reload` in dev, and the FastMCP CLI is already a runtime dependency inside the container. Having a second hand-rolled `__main__` block that does a slightly different version of the same job (different transport default, separate place where startup logic lives) is pure duplication and was the root cause of the `ensure_vector_index()` drift noted below.

#### Implementation changes required

1. **Delete the `if __name__ == "__main__":` block** in `src/mcp/server.py`. The file becomes a pure module that defines `mcp` and its tools — no script behaviour. `os`/transport/`config.mcp_host`/`config.mcp_port` imports that only existed to serve the `__main__` block can go with it.
2. **Move startup initialization into a FastMCP lifespan hook** attached to the `mcp` object. This covers two things the current layout conflates:
   - **Expensive resource construction** (`Config()`, the embedder, `Neo4jRepository`, `MemoryService`) moves out of module scope. These become module-level `None` placeholders that the lifespan `__aenter__` populates. Today they run on any bare import — tests, doc generation, IDE introspection — which means an import alone can attempt a Neo4j connection and load the sentence-transformers model. Tests that need these objects must rebind them on the module (`import src.mcp.server as srv; srv.service = mock`) — a `from src.mcp.server import service` binds to the `None` placeholder at import time and won't see the lifespan's later assignment.
   - **Vector index bootstrap** (`repository.ensure_vector_index()`) also moves into the lifespan. The current code path runs it from `__main__` only, which means the dev `fastmcp run` workflow silently skips index creation today — a latent bug. Lifespans are `async` context managers, so `ensure_vector_index` becomes `async` (or is wrapped with `asyncio.to_thread`) and is `await`ed inside `__aenter__`. FastMCP does not start accepting tool calls until `__aenter__` returns, so there is no window where `recall` could run before the index exists; `CREATE VECTOR INDEX … IF NOT EXISTS` is idempotent on subsequent starts.

   A lifespan hook fires whenever `mcp.run()` is called (by any caller), so it covers dev, power-user, and Cloud Run uniformly, and is skipped on bare imports.
3. **Drop the `MEMENTO_TRANSPORT` env var entirely.** Transport is now a CLI flag set per environment, not a runtime-read env var. `MEMENTO_MCP_HOST` and `MEMENTO_MCP_PORT` also go away — Cloud Run passes `--host`/`--port` as CLI flags, and stdio environments don't have a host or port. `Config.mcp_host` and `Config.mcp_port` are deleted from `src/utils/config.py`.
4. **Dockerfile uses `ENTRYPOINT` + `CMD`** so Cloud Run can override the flags without repeating the entrypoint:
   ```dockerfile
   ENTRYPOINT ["fastmcp", "run", "src/mcp/server.py"]
   CMD []
   ```
   Power-user `docker compose run --rm -T memento` picks up the empty `CMD` and gets stdio. The Terraform config sets Cloud Run's container `args = ["--transport", "http", "--host", "0.0.0.0", "--port", "8080"]`, which get appended to the ENTRYPOINT at container start. Port 8080 matches Cloud Run's `$PORT` default; the exact wiring (e.g. as a Terraform variable in a single place) is an implementation detail.
5. **Tests that currently import `server.py`** need to be checked — any that relied on the `__main__` block's side effects (none expected, but worth confirming) need to start the server via the lifespan path instead.

### Credentials and environment variables

**Single source of truth for credentials**

All three consumers of Neo4j credentials — the Neo4j image, the Memento app, and the Neo4j MCP server — read from the same `MEMENTO_NEO4J_*` variables. Changing the password in one place propagates everywhere.

The compose file interpolates from `MEMENTO_NEO4J_PASSWORD`:

```yaml
NEO4J_AUTH: neo4j/${MEMENTO_NEO4J_PASSWORD:-memento}
```

The `.mcp.json` Neo4j MCP server entry maps to the same vars:

```json
"env": {
  "NEO4J_URI": "${MEMENTO_NEO4J_URI}",
  "NEO4J_USERNAME": "${MEMENTO_NEO4J_USER}",
  "NEO4J_PASSWORD": "${MEMENTO_NEO4J_PASSWORD}"
}
```

**Power users (docker-compose)**

If no `MEMENTO_NEO4J_PASSWORD` env var is set, it falls back to `memento`. Security-conscious users can create a `.env` to override it without touching the compose file. Power users who don't care run `docker compose up` with zero configuration.

Neo4j's host ports are bound to `127.0.0.1` (e.g. `127.0.0.1:7687:7687`), making them reachable only from the host machine. Docker's default is `0.0.0.0`, which would expose the database to the local network — a real attack surface on shared networks (café, office, etc.). Container-to-container traffic between Memento and Neo4j uses the Docker internal network and is unaffected by this binding.

**Development (VM)**

A `.env` file is used and gitignored. `.env.example` is committed with values pre-filled (excerpt):

```
MEMENTO_NEO4J_URI=bolt://localhost:7687
MEMENTO_NEO4J_USER=neo4j
MEMENTO_NEO4J_PASSWORD=memento
MEMENTO_EMBEDDING_PROVIDER=local
MEMENTO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MEMENTO_EMBEDDING_CACHE_DIR=.cache/models
# ...
```

Dev copies `.env.example` to `.env` — no values need changing.

This follows the [12-factor app](https://12factor.net/config) convention and maps naturally to pydantic-settings: env vars are the source of truth, `.env` provides local defaults, and Cloud Run overrides them directly without any profile-switching logic. This is the Python idiomatic equivalent of Spring's `application-{profile}.yml` — simpler because there is no profile concept, just individual vars set per environment.

**Cloud Run**

Credentials reach the container through:
- `MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, `MEMENTO_EMBEDDING_*` — plain Cloud Run environment variables
- `MEMENTO_NEO4J_PASSWORD` — stored in GCP Secret Manager, exposed to the container as an environment variable via [Cloud Run's native secret integration](https://cloud.google.com/run/docs/configuring/services/secrets) (the env-var form, not the file-mount form, since pydantic-settings reads from the environment)

Transport, host, and port are **not** environment variables — they are CLI flags passed as the Cloud Run container `args` (see single-entrypoint section above).

### Local Setup (power users)

The standard for distributing containerized MCP servers is `docker run --rm -i`, which preserves stdio transport — the same transport used by all official Anthropic reference servers and Docker's MCP Toolkit. No HTTP transport is needed.

Memento needs a Neo4j sidecar. The solution is `docker compose run`, which handles network attachment automatically and waits for Neo4j's healthcheck to pass before Memento starts:

```yaml
# docker-compose.yml
services:
  memento:
    image: your-registry/memento
    depends_on:
      neo4j:
        condition: service_healthy
    environment:
      MEMENTO_NEO4J_URI: bolt://neo4j:7687
      MEMENTO_NEO4J_USER: neo4j
      MEMENTO_NEO4J_PASSWORD: ${MEMENTO_NEO4J_PASSWORD:-memento}

  neo4j:
    image: neo4j:2026.03.1 # Pin to specific CalVer; neo4j:5 is legacy stream
    ports:
      - "127.0.0.1:7687:7687"
      - "127.0.0.1:7474:7474"
    environment:
      NEO4J_AUTH: neo4j/${MEMENTO_NEO4J_PASSWORD:-memento}
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - neo4j_data:/data
```

The MCP client spawns Memento as a stdio subprocess via compose. The snippet below is the **power user's own MCP client config** (e.g. `~/.claude.json` or the equivalent for their client) — it is **not** the `.mcp.json` committed to this repo. The committed `.mcp.json` (shown earlier in §"MCP configuration as repo files") is for developers working *on* Memento; power users consuming Memento point their own client at the compose-run command:

```json
{
  "mcpServers": {
    "memento": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "-T", "memento"]
    }
  }
}
```

The `-T` flag disables pseudo-TTY allocation. This is **required** for MCP stdio transport: MCP clients communicate over line-delimited JSON-RPC on piped stdin/stdout, and TTY allocation can corrupt that framing. This mirrors the `docker run --rm -i` (no `-t`) convention used by the Anthropic reference MCP servers.

On first invocation, compose starts Neo4j and waits for its healthcheck to pass before launching Memento. Neo4j stays running between spawns, and its data persists via a named volume. No wrapper script or manual network management required.

> **First-spawn cold start**: Neo4j typically takes ~10–30s to become healthy from cold. The first MCP spawn of the day (or after a reboot) will block on that; subsequent spawns are fast because Neo4j stays up between them. MCP clients usually have generous handshake timeouts, but users should expect the first connection to be noticeably slower.

The `docker-compose.yml` is **not used for cloud deployment** — it exists solely for local power users.

### Cloud Deployment

**Platform: GCP** — Cloud Run for Memento, Neo4j Aura Free for storage.

- Cloud Run fits within the [GCP always-free quota](https://cloud.google.com/run/pricing) (2M requests/month).
- [Neo4j Aura Free](https://neo4j.com/cloud/platform/aura-graph-database/faq/) is sufficient for the target scale (personal, friends, and family).
- **Total cost: $0/month** at this scale. Clear upgrade path to self-hosted Neo4j on GCE if needed.

No docker-compose in cloud. The Memento image is pushed to Artifact Registry and deployed directly to Cloud Run. Neo4j Aura is an external managed service — no sidecar needed.

### Dockerfile Strategy

A single multi-stage `Dockerfile`:

- **Builder stage**: Installs `uv`, resolves and installs dependencies into a venv.
- **Runtime stage**: Copies only the venv and source into a slim Python image. No build tools in the final image.

The image's `ENTRYPOINT` is `fastmcp run src/mcp/server.py` with an empty `CMD`. The same image serves both environments — power users build locally via `docker compose up --build` and get stdio by default, Cloud Run pulls from Artifact Registry and passes `--transport http --host 0.0.0.0 --port 8080` as the container `args`. The only differences between environments are Neo4j connection config (env vars) and the CLI flags passed to the entrypoint.

> **Deferred**: whether the sentence-transformers model is baked into the image, mounted via a named volume, or replaced altogether (e.g. a hosted embedding API) is intentionally unresolved in this ADR. See `Documentation/known-tech-debt.md` TD-004.

### Infrastructure-as-Code

Cloud infrastructure is managed with Terraform (Google provider):

- `google_artifact_registry_repository`
- `google_cloud_run_v2_service`
- `google_secret_manager_secret`
- `google_service_account` + IAM bindings (least-privilege for Cloud Run)
- `google_secret_manager_secret_iam_member` — grants the Cloud Run service account `roles/secretmanager.secretAccessor` on `MEMENTO_NEO4J_PASSWORD`, without which the secret mount fails at deploy time

Neo4j Aura is provisioned manually — the Neo4j Labs Aura Terraform provider requires Aura API credentials that Free-tier accounts don't receive. Its connection string is stored in Secret Manager. Terraform state is stored in a GCS bucket.

## Consequences

- Power users get a one-command local setup with no Python or Neo4j prerequisites.
- **Power-user distribution and Cloud Run cold-start performance are gated on a follow-up embedding-model-distribution ADR** (tracked by TD-004). This ADR green-lights the *architecture* for power-user distribution and Cloud Run deployment, but neither can ship to real users until the embedding strategy is resolved: without it, every power-user MCP spawn re-downloads ~90 MB of model (first-run UX is multi-minute and offline-hostile), and every Cloud Run cold start pays the same cost. The design space (bake model into image, named-volume cache, hosted embedding API, or hybrid) intersects with a separate requirement to let users configure their own embedding provider, and is large enough to warrant its own ADR. The container plumbing in this ADR does not pre-commit to any of those options — they layer on additively.
- Dev copies `.env.example` to `.env` once — no values to edit. MCP servers are pre-configured via `.mcp.json`.
- Single entrypoint across all environments: `fastmcp run src/mcp/server.py` with per-environment CLI flags. The `if __name__ == "__main__":` block in `server.py` is deleted. Global resources (Config, Repository, Service) and `ensure_vector_index()` move into a FastMCP lifespan hook, so they are only initialized when the server starts serving and do not fire on bare imports. `MEMENTO_TRANSPORT`, `MEMENTO_MCP_HOST`, and `MEMENTO_MCP_PORT` env vars and their `Config` fields are removed — these are now CLI flags, not runtime env lookups. TD-003 (`mcp_host` default) is resolved by this deletion.
- Cloud deployment is zero-cost at personal scale.
- Claude self-validates by calling Memento tools then inspecting the DB via Neo4j MCP.
- Secrets are never plaintext in cloud; local defaults pose no meaningful security risk.
- One Dockerfile; no per-environment divergence.
- Cloud infrastructure is reproducible via Terraform.
