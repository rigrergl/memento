# Contract: `.mcp.json` (developer dev-loop)

**Location**: repo root (`/.mcp.json`)
**Driven by**: FR-009; ADR-007 §"MCP configuration as repo files"; research §R7
**Consumers**: Claude Code, Gemini CLI (clients that read project-level `.mcp.json` and perform `${VAR}` substitution from their launching shell).

## Required content

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

## Required behaviour

- The `memento` entry MUST launch the dev server via `uv run fastmcp run src/mcp/server.py --reload` so file edits trigger a worker restart.
- The `neo4j-cypher` entry MUST use the upstream `mcp-neo4j-cypher` package via `uvx` (no vendoring).
- The Neo4j MCP entry MUST read credentials via `${VAR}` references that resolve to `MEMENTO_NEO4J_*` from the launching shell — single source of truth across Memento app and Neo4j MCP (ADR-007 §"Single source of truth for credentials").

## Forbidden

- MUST NOT contain literal credentials.
- MUST NOT reference any HTTP transport (the dev loop is stdio).
- MUST NOT reference an env var named `MEMENTO_TRANSPORT`, `MEMENTO_MCP_HOST`, or `MEMENTO_MCP_PORT` (FR-007).
- MUST NOT be the file power users edit — power users edit their own client config (`~/.claude.json`, `claude_desktop_config.json`, etc.) per FR-012.

## Test plan

- File parses as valid JSON.
- A developer who has exported `MEMENTO_NEO4J_*` from `.env` and launches Claude Code in the repo sees both `memento` and `neo4j-cypher` MCP servers connected.
- After editing a tool in `src/mcp/server.py`, the next tool call in the client reflects the change with at most one observable failed call between the edit and the retry (per FR's US2 acceptance scenario 2).
