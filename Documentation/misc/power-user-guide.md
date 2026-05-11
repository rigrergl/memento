# Power-User Snooping Guide

Quick reference for interacting with a running Memento stack — no code changes needed.

**Prerequisites**: `docker compose up -d` is running and both containers are healthy (`docker compose ps`).

---

## Accessing from another machine

All ports are bound to `127.0.0.1` — they are not exposed on the network by default. If you're connecting from a different machine, forward the ports over SSH first:

```bash
ssh -L 8000:localhost:8000 -L 7474:localhost:7474 user@remote-host
```

Then use `localhost` in all commands below as if you were local.

---

## MCP Inspector

The MCP Inspector lets you interactively call Memento's tools from a browser UI.

### Interactive (browser UI)

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

Opens a local web UI. Select a tool (`remember` or `recall`), fill in the arguments, and hit **Run**.

### CLI — store a memory

```bash
npx @modelcontextprotocol/inspector --cli --method tools/call \
  --tool-name remember \
  --tool-arg content="your memory here" \
  --tool-arg confidence=0.9 \
  http://localhost:8000/mcp
```

### CLI — recall memories

```bash
npx @modelcontextprotocol/inspector --cli --method tools/call \
  --tool-name recall \
  --tool-arg query="your search query" \
  http://localhost:8000/mcp
```

Pipe either command through `| jq` for readable output.

### CLI — list available tools

```bash
npx @modelcontextprotocol/inspector --cli --method tools/list \
  http://localhost:8000/mcp
```

---

## Neo4j Browser

The Neo4j browser UI is available at:

```
http://localhost:7474
```

**Login**:
- Username: `neo4j`
- Password: the value of `MEMENTO_NEO4J_PASSWORD` from your `.env`

### Useful Cypher queries

Get all memory nodes:
```cypher
MATCH (m:Memory) RETURN m LIMIT 25
```

Get all nodes and relationships (full graph):
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
```

Search memory content by keyword:
```cypher
MATCH (m:Memory)
WHERE m.content CONTAINS 'your keyword'
RETURN m.content, m.confidence, m.created_at
```

Count total memories:
```cypher
MATCH (m:Memory) RETURN count(m)
```

Delete all memories (destructive — useful for resetting state):
```cypher
MATCH (n) DETACH DELETE n
```
