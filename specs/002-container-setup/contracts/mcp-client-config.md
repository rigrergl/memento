# Contract: Power-User MCP Client Config Documentation

**Location**: documented in `README.md` (Power-User Setup section)
**Driven by**: FR-012, FR-013; ADR-007 §"Local Setup (power users)"; research §R15
**Consumers**: Power users adding Memento to their MCP client config.

This is **not** a file the project ships. It is the *config blocks the README must publish* for power users to copy into their own client config (`~/.claude.json`, `claude_desktop_config.json`, etc.).

## Required content (README must include all three blocks)

### Block 1 — Native HTTP (preferred; for Claude Code and other modern clients)

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

### Block 2 — Bridge via `mcp-remote` (for stdio-only clients with Node/npm)

```json
{
  "mcpServers": {
    "memento": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/mcp/"]
    }
  }
}
```

### Block 3 — Bridge via `mcp-proxy` (for stdio-only clients with Python/uv)

```json
{
  "mcpServers": {
    "memento": {
      "command": "uvx",
      "args": ["mcp-proxy", "http://localhost:8000/mcp/"]
    }
  }
}
```

## Required behaviour / framing in README

- The native-HTTP block MUST be presented first as the recommended path (FR-012).
- README MUST mark `npx mcp-remote …` and `uvx mcp-proxy …` as third-party bridges not authored or maintained by this project (FR-012).
- README MUST identify which clients fall into which group at the time of writing — e.g. "Claude Code: native HTTP. Claude Desktop: bridge required."

## Forbidden

- README MUST NOT bundle `mcp-remote` or `mcp-proxy` as project dependencies.
- README MUST NOT recommend `:latest` image tags or any path other than `git pull && docker compose pull && docker compose up -d` for upgrades (FR-011).

## Test plan

- A reviewer following the README's Power-User Setup end-to-end on a clean machine reaches a working `remember`/`recall` round-trip.
- The native-HTTP block works in Claude Code; the bridge blocks work in Claude Desktop. Both verified manually as part of US1 acceptance.
