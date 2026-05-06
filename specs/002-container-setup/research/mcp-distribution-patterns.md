# Research: Power-User Distribution Patterns for MCP Servers with Sidecar Dependencies

**Status**: Open exploration — input for the 002-container-setup spec
**Date**: 2026-04-20
**Question**: Can the Memento power-user setup be a single `mcp.json` paste, or is the two-step `curl yml + edit config` flow inherent to the Neo4j sidecar requirement?

## Problem framing

Memento is a GraphRAG MCP server. Every session needs:

1. A running Neo4j instance with vector-index support
2. A persistent volume so memories survive restarts
3. Network wiring between Memento and Neo4j
4. Memento to start *after* Neo4j is healthy

ADR-007 and the current spec resolve this with `docker compose run --rm -T memento` against a committed `docker-compose.yml`. The user curls the compose file to disk, then points their MCP client at it via an entry like:

```json
"memento": {
  "command": "docker",
  "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "-T", "memento"]
}
```

The open question: is there a single-paste mcp.json entry that avoids the separate "download the compose file" step without regressing on robustness or data persistence?

## What peers do

### Graphiti (Neo4j sidecar — structurally identical to Memento)

- Power-user install: `git clone https://github.com/getzep/graphiti.git && cd graphiti/mcp_server && docker compose up`
- mcp.json bridges stdio → HTTP via `mcp-remote`:
  ```json
  {
    "mcpServers": {
      "graphiti-memory": {
        "command": "npx",
        "args": ["mcp-remote", "http://localhost:8000/mcp/"]
      }
    }
  }
  ```
- **More friction than Memento's current spec** — clone + `cd` + `compose up` (and keep it running) versus a single `curl` and a compose-run entry.

### Qdrant MCP (vector DB with sidecar-shaped problem)

- Sidesteps sidecars entirely with an embedded mode: `QDRANT_LOCAL_PATH` makes Qdrant an in-process library rather than a service.
- mcp.json is one paste because there is no separate database process to orchestrate.
- Not applicable to Memento unless we swap Neo4j for an embeddable graph DB (e.g. Kuzu) — a much larger architectural change, out of scope here.

### Official Memory MCP (Anthropic reference)

- One-paste install via `claude mcp add memory -e MEMORY_FILE_PATH=~/.claude/memory.json -- npx -y @modelcontextprotocol/server-memory`.
- One-paste works because persistence is a single JSON file on disk. No database, no container, no network.

### Docker MCP Toolkit

- Positions a *gateway* as the entry point. Users install Docker Desktop, add Memento via a catalog UI, and mcp.json reduces to:
  ```json
  "MCP_DOCKER": {
    "command": "docker",
    "args": ["mcp", "gateway", "run", "--profile", "my_profile"],
    "type": "stdio"
  }
  ```
- Dependencies between containers are declared in catalog metadata, managed by the gateway.
- Not one-paste from scratch — it trades "edit mcp.json" for "install Docker Desktop and add via UI" — but it is the closest thing to a canonical "install MCP with sidecars" UX emerging in the ecosystem.

### mcp-remote / mcp-proxy

- Sidecar pattern's *glue*: long-lived server runs HTTP; stdio-only clients connect via `npx mcp-remote http://...` or `uvx mcp-proxy`.
- Used by Graphiti and Tavily to present a clean one-line mcp.json while the server runs out-of-band.

## The design space for Memento

| # | Option | mcp.json paste | Prior steps needed | Main tradeoff |
|---|---|---|---|---|
| A | `curl \| docker compose -f - run` | One line | None | **Data-loss hazard** (see below). Rule out. |
| B | `curl` yml to disk + `docker compose -f <path> run` (current spec) | One entry, path-bound | One `curl` | Robust. Two user actions total. |
| C | Fat image (Neo4j + Memento in one container) | `docker run` one-liner, but user still needs `-v memento_data:/data` | None | ~1.2GB image, violates one-process-per-container, can't tune Neo4j JVM independently, harder to upgrade either piece. |
| D | Split: one-time `docker compose up -d` + `docker exec -i` in mcp.json | One entry | `docker compose up -d` once per reboot | Cleanest mcp.json among stdio-only options. DB lifecycle decoupled from client spawns. Still needs yml on disk. |
| E | HTTP + `mcp-remote` (Graphiti's pattern) | `npx mcp-remote http://localhost:8000/mcp/` | `docker compose up -d` once per reboot | Client-portable, decoupled lifecycle. Requires exposing HTTP from Memento — ADR-007 currently reserves HTTP for Cloud Run. |
| F | Installer CLI (`brew install memento`, shell-pipe) | `"command": "memento", "args": ["run"]` | Install the CLI | Cleanest paste. New artifact to maintain and distribute; shell installers carry a trust cost. |

### Why option A (curl-piped compose) is a trap

`docker compose -f - run` reads the compose file from stdin, which has no on-disk path. Compose derives its **project name** from the current working directory when `-f -` is used. Named volumes (`neo4j_data`) are namespaced by project, so two spawns from different CWDs get **different Neo4j volumes** — the second spawn sees an empty database.

Workarounds exist (`-p memento` forces a stable project name; `COMPOSE_PROJECT_NAME=memento` via env) but they undo the "one-paste" ergonomics and make the entry longer and more fragile than option B. Not worth the risk of silent data loss for personal memory data.

## Initial read

Two directions are worth serious consideration:

1. **Keep the two-step (B), reframe it as one command.** The friction is mostly perceptual — `curl -o ~/.memento/docker-compose.yml https://…` is a single command, not a multi-step procedure. Most production MCPs with sidecars accept this shape; Graphiti is worse. Document the install as a single copy-paste block, not a numbered list.

2. **Split architecture (D).** User runs `docker compose up -d` once per reboot; mcp.json becomes `docker exec -i memento-memento-1 fastmcp run src/mcp/server.py`. No network fetch per spawn, no compose parsing per spawn, no first-spawn cold start, and the entry is tighter than option B's. Trade: the user has to start the daemon manually (or set up autostart) rather than letting compose lazy-start on first client invocation.

Option A is a silent-data-loss hazard and should be ruled out. Option C (fat image) is a fallback only if repeated user feedback indicates the two-step path is actually blocking adoption; the operational-hygiene cost is real but not catastrophic at personal scale. Option E is the cloud-forward answer but is gated on exposing HTTP locally, which ADR-007 deferred. Option F is the cleanest UX but introduces a new distribution surface.

## Open questions for the spec

- Is the perceived friction of option B actually a problem, or are we over-optimizing for the paste? No user signal yet.
- If option D is picked: does the user starting/stopping the daemon manually feel worse or better than lazy-start via `compose run`?
- Should the `docker-compose.yml` be `curl`-installable to a predictable path (e.g. `~/.memento/`) to make the mcp.json entry parametrizable?
- Does enabling HTTP transport locally (option E) introduce meaningful attack surface if bound to `127.0.0.1`? If not, E becomes more attractive — same transport as Cloud Run, same `mcp-remote` bridge pattern already widespread.

## Sources

- [Graphiti MCP Server README](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md)
- [Official Qdrant MCP Server](https://github.com/qdrant/mcp-server-qdrant)
- [Neo4j MCP (neo4j-contrib)](https://github.com/neo4j-contrib/mcp-neo4j)
- [Knowledge Graph Memory MCP Server (Anthropic reference)](https://github.com/modelcontextprotocol/servers/tree/main/src/memory)
- [mcp-remote (geelen/mcp-remote)](https://github.com/geelen/mcp-remote)
- [mcp-proxy (sparfenyuk)](https://github.com/sparfenyuk/mcp-proxy)
- [Docker MCP Toolkit — Get Started](https://docs.docker.com/ai/mcp-catalog-and-toolkit/get-started/)
- [Docker MCP Catalog](https://docs.docker.com/ai/mcp-catalog-and-toolkit/catalog/)
- [Top 5 MCP Server Best Practices (Docker blog)](https://www.docker.com/blog/mcp-server-best-practices/)
