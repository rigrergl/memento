# ADR-007: Container Setup for Local and Cloud Deployment

## Status
Decided

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
fastmcp run src/mcp/server.py --reload  # auto-restarts on file change, maintains connection
```

The key reason to avoid the power-user container approach here is **hot reload without client reconnection**. `fastmcp --reload` restarts the server code internally while fastmcp itself keeps the stdio pipe alive — so Claude's MCP session never breaks between code changes. Running Memento as an ephemeral container (power-user style) would tear down the stdio connection on every restart, forcing Claude to reconnect and breaking the agentic dev loop. A volume-mount + `compose watch` approach could achieve the same hot-reload behaviour inside a container, but it's additional setup for an identical outcome.

### MCP configuration as repo files

The MCP server config for dev is committed to the repo as `.mcp.json` at the project root. Claude Code treats this as the project-level MCP configuration, shared with anyone who clones the repo — no manual `~/.claude` setup required:

```json
{
  "mcpServers": {
    "memento": {
      "command": "fastmcp",
      "args": ["run", "src/mcp/server.py", "--reload"]
    },
    "neo4j-cypher": {
      "command": "uvx",
      "args": ["mcp-neo4j-cypher"],
      "env": {
        "NEO4J_URI": "${NEO4J_URI}",
        "NEO4J_USERNAME": "${NEO4J_USERNAME}",
        "NEO4J_PASSWORD": "${NEO4J_PASSWORD}"
      }
    }
  }
}
```

The Neo4j MCP server picks up its credentials from the developer's `.env` file (see below).

### Transport configuration

Transport is currently hardcoded to HTTP. Supporting stdio for local use requires making it configurable via an environment variable (e.g. `TRANSPORT`, defaulting to `stdio`). This is a necessary implementation change that follows from the decisions in this ADR.

| Environment | Transport | Why |
|---|---|---|
| Dev (VM) | `stdio` | Default; required by `fastmcp --reload` |
| Power user (local) | `stdio` | Industry standard for local MCP servers |
| Cloud Run | `http` | Client (phone, n8n, etc.) is on a different machine — stdio requires spawning a local subprocess, which is impossible over a network |

Cloud Run sets `TRANSPORT=http` as an environment variable. Local environments default to `stdio` with no configuration needed.

### Credentials and environment variables

**Power users (docker-compose)**

The compose file uses a default value rather than a hardcoded literal:

```yaml
NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-memento}
```

If no `NEO4J_PASSWORD` env var is set, it falls back to `memento`. Security-conscious users can create a `.env` to override it without touching the compose file. Power users who don't care run `docker compose up` with zero configuration.

Neo4j's host ports are bound to `127.0.0.1` (e.g. `127.0.0.1:7687:7687`), making them reachable only from the host machine. Docker's default is `0.0.0.0`, which would expose the database to the local network — a real attack surface on shared networks (café, office, etc.). Container-to-container traffic between Memento and Neo4j uses the Docker internal network and is unaffected by this binding.

**Development (VM)**

A `.env` file is used and gitignored. `.env.example` is committed with values pre-filled to match the compose defaults:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=memento
TRANSPORT=stdio
```

Dev copies `.env.example` to `.env` — no values need changing.

This follows the [12-factor app](https://12factor.net/config) convention and maps naturally to pydantic-settings: env vars are the source of truth, `.env` provides local defaults, and Cloud Run overrides them directly without any profile-switching logic. This is the Python idiomatic equivalent of Spring's `application-{profile}.yml` — simpler because there is no profile concept, just individual vars set per environment.

**Cloud Run**

Credentials reach the container through:
- `NEO4J_URI`, `NEO4J_USERNAME`, `TRANSPORT=http` — plain Cloud Run environment variables
- `NEO4J_PASSWORD` — stored in GCP Secret Manager, mounted via [Cloud Run's native secret integration](https://docs.cloud.google.com/run/docs/configuring/services/secrets)

### Local Setup (power users)

The standard for distributing containerized MCP servers is `docker run --rm -i`, which preserves stdio transport — the same transport used by all official Anthropic reference servers and Docker's MCP Toolkit. No HTTP transport is needed.

Memento needs a Neo4j sidecar. The solution is `docker compose run`, which handles network attachment automatically and ensures Neo4j is healthy before Memento starts:

```yaml
# docker-compose.yml
services:
  memento:
    image: your-registry/memento
    depends_on:
      neo4j:
        condition: service_healthy

  neo4j:
    image: neo4j:5
    healthcheck: ...
    volumes:
      - neo4j_data:/data
```

The MCP client spawns Memento as a stdio subprocess via compose:

```json
{
  "mcpServers": {
    "memento": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "memento"]
    }
  }
}
```

On first invocation, compose starts Neo4j and waits for it to be healthy (~15s). Subsequent spawns are near-instant since Neo4j stays running. Neo4j data persists via a named volume. No wrapper script or manual network management required.

The `docker-compose.yml` is **not used for cloud deployment** — it exists solely for local power users.

### Cloud Deployment

**Platform: GCP** — Cloud Run for Memento, Neo4j Aura Free for storage.

- Cloud Run fits within the [GCP always-free quota](https://cloud.google.com/run/pricing) (2M requests/month).
- [Neo4j Aura Free](https://neo4j.com/cloud/platform/aura-graph-database/faq/) (200k nodes / 400k relationships) is sufficient for personal/family-scale workloads.
- **Total cost: $0/month** at this scale. Clear upgrade path to self-hosted Neo4j on GCE if needed.

No docker-compose in cloud. The Memento image is pushed to Artifact Registry and deployed directly to Cloud Run. Neo4j Aura is an external managed service — no sidecar needed.

### Dockerfile Strategy

A single multi-stage `Dockerfile`:

- **Builder stage**: Installs `uv`, resolves and installs dependencies into a venv.
- **Runtime stage**: Copies only the venv and source into a slim Python image. No build tools in the final image.

The same image serves both environments — power users build locally via `docker compose up --build`, Cloud Run pulls from Artifact Registry. The only difference is Neo4j connection config and transport passed via environment variables.

### Infrastructure-as-Code

Cloud infrastructure is managed with Terraform (Google provider):

- `google_artifact_registry_repository`
- `google_cloud_run_v2_service`
- `google_secret_manager_secret`
- `google_service_account` + IAM bindings (least-privilege for Cloud Run)

Neo4j Aura is provisioned manually (no Terraform provider for Aura Free); its connection string is stored in Secret Manager. Terraform state is stored in a GCS bucket.

## Consequences

- Power users get a one-command local setup with no Python or Neo4j prerequisites.
- Dev copies `.env.example` to `.env` once — no values to edit. MCP servers are pre-configured via `.mcp.json`.
- Transport is config-driven; `TRANSPORT=http` activates the cloud path, `stdio` is the local default.
- Cloud deployment is zero-cost at personal scale.
- Claude self-validates by calling Memento tools then inspecting the DB via Neo4j MCP.
- Secrets are never plaintext in cloud; local defaults pose no meaningful security risk.
- One Dockerfile; no per-environment divergence.
- Cloud infrastructure is reproducible via Terraform.
