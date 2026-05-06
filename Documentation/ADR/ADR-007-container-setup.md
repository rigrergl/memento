# ADR-007: Container Setup for Local and Cloud Deployment

## Status
Accepted

## Date
2026-04-08 (amended 2026-04-20: power-user transport moved from stdio to HTTP; see Local Setup section)

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
| Power user (container) | `fastmcp run src/mcp/server.py --transport http --host 0.0.0.0 --port 8000` |
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
   Each environment supplies its own flags: the power-user `docker-compose.yml` sets `command: ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]`, so `docker compose up -d` runs Memento as an HTTP daemon on loopback. The Terraform config sets Cloud Run's container `args = ["--transport", "http", "--host", "0.0.0.0", "--port", "8080"]`. Both append to the same ENTRYPOINT. Port 8080 matches Cloud Run's `$PORT` default; the exact wiring (e.g. as a Terraform variable in a single place) is an implementation detail.
5. **Tests that currently import `server.py`** need to be checked — any that relied on the `__main__` block's side effects (none expected, but worth confirming) need to start the server via the lifespan path instead.

### Credentials and environment variables

**Single source of truth for credentials**

All three consumers of Neo4j credentials — the Neo4j image, the Memento app, and the Neo4j MCP server — read from the same `MEMENTO_NEO4J_*` variables. Changing the password in one place propagates everywhere.

The compose file interpolates from `MEMENTO_NEO4J_PASSWORD` with no inline default. Both services use the `${VAR:?error}` form, so `docker compose` errors at config-time (before any container starts) when the variable is unset, producing a clear actionable message rather than a confusing Neo4j-side auth failure later:

```yaml
NEO4J_AUTH: neo4j/${MEMENTO_NEO4J_PASSWORD:?MEMENTO_NEO4J_PASSWORD must be set (copy .env.example to .env and fill it in)}
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

The compose file ships with no fallback default for `MEMENTO_NEO4J_PASSWORD` — users must supply it via a `.env` file (or shell environment) before running `docker compose up`. Shipping with a hard-coded default password was rejected: it normalises a credential that ends up identical across every deployment, creates a false impression of "configured" security, and trains users not to think about secrets. The 2-second `cp .env.example .env` step plus picking a password is a clear signal that this is a real database with a real credential.

Neo4j's host ports are bound to `127.0.0.1` (e.g. `127.0.0.1:7687:7687`), making them reachable only from the host machine. Docker's default is `0.0.0.0`, which would expose the database to the local network — a real attack surface on shared networks (café, office, etc.). Container-to-container traffic between Memento and Neo4j uses the Docker internal network and is unaffected by this binding.

**Development (VM)**

A `.env` file is used and gitignored. `.env.example` is committed as a placeholder template — non-secret values are pre-filled, the password is left blank with a comment indicating Neo4j's 8-character minimum (excerpt):

```
MEMENTO_NEO4J_URI=bolt://localhost:7687
MEMENTO_NEO4J_USER=neo4j
# Set a password of your choice (Neo4j requires a minimum of 8 characters).
MEMENTO_NEO4J_PASSWORD=
MEMENTO_EMBEDDING_PROVIDER=local
MEMENTO_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MEMENTO_EMBEDDING_CACHE_DIR=.cache/models
# ...
```

Dev copies `.env.example` to `.env` and fills in `MEMENTO_NEO4J_PASSWORD` before starting the stack. Same flow for power users.

This follows the [12-factor app](https://12factor.net/config) convention and maps naturally to pydantic-settings: env vars are the source of truth, `.env` provides local defaults, and Cloud Run overrides them directly without any profile-switching logic. This is the Python idiomatic equivalent of Spring's `application-{profile}.yml` — simpler because there is no profile concept, just individual vars set per environment.

**Cloud Run**

Credentials reach the container through:
- `MEMENTO_NEO4J_URI`, `MEMENTO_NEO4J_USER`, `MEMENTO_EMBEDDING_*` — plain Cloud Run environment variables
- `MEMENTO_NEO4J_PASSWORD` — stored in GCP Secret Manager, exposed to the container as an environment variable via [Cloud Run's native secret integration](https://cloud.google.com/run/docs/configuring/services/secrets) (the env-var form, not the file-mount form, since pydantic-settings reads from the environment)

Transport, host, and port are **not** environment variables — they are CLI flags passed as the Cloud Run container `args` (see single-entrypoint section above).

### Local Setup (power users)

Power users clone the repo, start the stack once, and point their MCP client at Memento's HTTP endpoint via a stdio↔HTTP bridge. This mirrors the [Graphiti](https://github.com/getzep/graphiti) pattern for MCP servers with database sidecars and unifies transport with Cloud Run.

The Memento image is published to GitHub Container Registry (`ghcr.io/rigrergl/memento:<version>`) with pinned semver tags and referenced by the committed `docker-compose.yml`. Users clone the repo — no separate compose-file download, no local image build. The publish workflow builds a multi-architecture manifest (`linux/amd64` + `linux/arm64`) so Apple Silicon users get native performance without Rosetta. Releases are initiated by bumping `[project] version` in `pyproject.toml`: an `auto-tag.yml` GitHub Actions workflow runs on pushes to `main`, creates and pushes the matching git tag if it does not yet exist, and that tag triggers the Docker publish workflow.

**Install**:

```bash
git clone https://github.com/rigrergl/memento.git
cd memento
docker compose up -d
```

**`docker-compose.yml`** (illustrative excerpts; the authoritative file — including the Memento healthcheck and other implementation details — is specified in spec 002-container-setup):

```yaml
services:
  memento:
    image: ghcr.io/rigrergl/memento:v0.2.0  # pinned; bumped per release
    depends_on:
      neo4j:
        condition: service_healthy
    environment:
      MEMENTO_NEO4J_URI: bolt://neo4j:7687
      MEMENTO_NEO4J_USER: neo4j
      MEMENTO_NEO4J_PASSWORD: ${MEMENTO_NEO4J_PASSWORD:?must be set; copy .env.example to .env}
    command: ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
    ports:
      - "127.0.0.1:8000:8000"

  neo4j:
    image: neo4j:2026.03.1 # Pin to specific CalVer; neo4j:5 is legacy stream
    ports:
      - "127.0.0.1:7687:7687"
      - "127.0.0.1:7474:7474"
    environment:
      NEO4J_AUTH: neo4j/${MEMENTO_NEO4J_PASSWORD:?must be set; copy .env.example to .env}
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]
      interval: 5s
      timeout: 5s
      retries: 10
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

Memento's HTTP port and Neo4j's ports are bound to `127.0.0.1` to avoid exposing them on shared networks (café, office, etc.). Container-to-container traffic uses the Docker internal network and is unaffected.

**MCP client config** — the power user's own (e.g. `~/.claude.json`), **not** the committed `.mcp.json` shown earlier in §"MCP configuration as repo files".

**Preferred (native HTTP — Claude Code and other modern clients)**

Most current MCP clients support HTTP transport natively. No bridge process required:

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

**Fallback (stdio↔HTTP bridge — Claude Desktop and other stdio-only clients)**

Claude Desktop's `claude_desktop_config.json` only supports stdio-launched subprocess entries; it cannot connect to HTTP servers directly. Users of stdio-only clients need a bridge process. Two equivalent options are documented; the user picks whichever runtime they already have:

```jsonc
// Option 1: npx bridge (mcp-remote)
{
  "mcpServers": {
    "memento": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/mcp/"]
    }
  }
}

// Option 2: uvx bridge (mcp-proxy)
{
  "mcpServers": {
    "memento": {
      "command": "uvx",
      "args": ["mcp-proxy", "http://localhost:8000/mcp/"]
    }
  }
}
```

Neither bridge is maintained by this project; both are thin external dependencies on the user's side.

**Why HTTP, not stdio** (amended from the original draft):

- **Unified transport.** Same `fastmcp run --transport http` invocation locally and in Cloud Run; same lifespan path, same test surface. No stdio-over-docker-piping quirks (`-T` flag, TTY framing).
- **Lifecycle decoupled from MCP spawns.** Neo4j cold start (~10–30s) happens during `docker compose up -d`, not on the first MCP tool call. Subsequent client reconnects are immediate.
- **Debuggability.** Standard Docker tooling — `docker compose logs memento`, `docker compose ps`, `curl localhost:8000/mcp/` for a sanity check — instead of stdio introspection.

Tradeoff: the user manages the daemon (`docker compose up -d` once per reboot), where the stdio draft lazy-started per spawn. Acceptable for the developer audience this path targets.

**Upgrade flow.** Releases bump the pinned `image:` tag in `docker-compose.yml` on `main`. Users upgrade with:

```bash
git pull
docker compose pull
docker compose up -d
```

Pinned semver keeps upgrades explicit and aligned with release notes. `:latest` is intentionally avoided — it can silently deliver breaking changes (schema migrations, Neo4j major-version bumps, tool-schema changes, env-var renames, embedding-model swaps that invalidate existing vectors).

The `docker-compose.yml` is **not used for cloud deployment** — it exists solely for local power users.

### Cloud Deployment

**Platform: GCP** — Cloud Run for Memento, Neo4j Aura Free for storage.

- Cloud Run fits within the [GCP always-free quota](https://cloud.google.com/run/pricing) (2M requests/month).
- [Neo4j Aura Free](https://neo4j.com/cloud/platform/aura-graph-database/faq/) is sufficient for the target scale (personal, friends, and family).
- **Total cost: $0/month** at this scale. Clear upgrade path to self-hosted Neo4j on GCE if needed.

No docker-compose in cloud. Cloud Run pulls the **same pinned Memento image tag** used locally — either directly from `ghcr.io`, or mirrored to Artifact Registry for lower intra-GCP latency. The multi-registry publish pipeline (ghcr + AR via Workload Identity Federation) is deferred to the Cloud Run spec — see `Documentation/misc/planning.md`. Neo4j Aura is an external managed service — no sidecar needed.

### Dockerfile Strategy

A single multi-stage `Dockerfile`:

- **Builder stage**: Installs `uv`, resolves and installs dependencies into a venv.
- **Runtime stage**: Copies only the venv and source into a slim Python image. No build tools in the final image.

The image's `ENTRYPOINT` is `fastmcp run src/mcp/server.py` with an empty `CMD`. The same image serves both environments by pinned semver tag — power users pull `ghcr.io/rigrergl/memento:<version>` via `docker compose pull`; Cloud Run pulls the same tag (directly from ghcr, or mirrored to Artifact Registry). Each environment supplies its own CLI flags: compose sets `command: ["--transport", "http", "--host", "0.0.0.0", "--port", "8000"]`; Cloud Run sets `args = ["--transport", "http", "--host", "0.0.0.0", "--port", "8080"]`. The only per-environment differences are Neo4j connection config (env vars) and the port.

> **Interim decision**: the sentence-transformers model is baked into the image (see spec 002-container-setup, FR-003). The longer-term choice between baked image, named-volume cache, and hosted embedding API remains open and is tracked in `Documentation/known-tech-debt.md` TD-004.

### Infrastructure-as-Code

Cloud infrastructure is managed with Terraform (Google provider):

- `google_artifact_registry_repository`
- `google_cloud_run_v2_service`
- `google_secret_manager_secret`
- `google_service_account` + IAM bindings (least-privilege for Cloud Run)
- `google_secret_manager_secret_iam_member` — grants the Cloud Run service account `roles/secretmanager.secretAccessor` on `MEMENTO_NEO4J_PASSWORD`, without which the secret mount fails at deploy time

Neo4j Aura is provisioned manually — the Neo4j Labs Aura Terraform provider requires Aura API credentials that Free-tier accounts don't receive. Its connection string is stored in Secret Manager. Terraform state is stored in a GCS bucket.

## Consequences

- Power users install with no Python or Neo4j prerequisites: `git clone`, `docker compose up -d`, and a one-time MCP client config entry. Modern clients (Claude Code) connect directly via `"type": "http"`; stdio-only clients (Claude Desktop) need a thin bridge (`mcp-remote` or `mcp-proxy`). Memento runs as an HTTP daemon on `127.0.0.1:8000`.
- Transport is unified across local and Cloud Run (HTTP everywhere except the dev loop, which stays on stdio because Memento runs natively via `uv run fastmcp run --reload`). The same pinned image tag is pulled in both environments.
- Upgrades are explicit user actions via `git pull && docker compose pull && docker compose up -d`; pinned semver tags prevent silent breaking changes.
- **Power-user distribution ships with the embedding model baked into the image** as an interim resolution (per spec 002-container-setup, FR-003). This avoids per-spawn re-download for power users and per-cold-start re-download on Cloud Run. The longer-term distribution strategy (named-volume cache, hosted embedding API, or hybrid) intersects with a separate requirement to let users configure their own embedding provider, and remains tracked by TD-004. The container plumbing here does not pre-commit to any of those options — they layer on additively.
- Dev (and power users) copy `.env.example` to `.env` and set `MEMENTO_NEO4J_PASSWORD` before starting the stack. MCP servers are pre-configured via `.mcp.json`.
- Single entrypoint across all environments: `fastmcp run src/mcp/server.py` with per-environment CLI flags. The `if __name__ == "__main__":` block in `server.py` is deleted. Global resources (Config, Repository, Service) and `ensure_vector_index()` move into a FastMCP lifespan hook, so they are only initialized when the server starts serving and do not fire on bare imports. `MEMENTO_TRANSPORT`, `MEMENTO_MCP_HOST`, and `MEMENTO_MCP_PORT` env vars and their `Config` fields are removed — these are now CLI flags, not runtime env lookups. TD-003 (`mcp_host` default) is resolved by this deletion.
- Cloud deployment is zero-cost at personal scale.
- Claude self-validates by calling Memento tools then inspecting the DB via Neo4j MCP.
- Secrets are never plaintext in cloud. Locally, the compose file ships with no fallback default for the Neo4j password — users supply their own via `.env` — so we never commit a credential that could leak into screenshots, copy-pasted snippets, or cargo-culted into actually-exposed deployments.
- One Dockerfile; no per-environment divergence.
- Cloud infrastructure is reproducible via Terraform.
